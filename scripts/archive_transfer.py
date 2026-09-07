"""Verified portable backups and explicit archive adoption; sources are never deleted."""
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
import tempfile
import zipfile

from workspace_config import CONFIG_PATH, SKILL_ROOT, resolve_workspace
from practice_store import build_state, writer, write_json, rebuild, validate_payload

MAX_BYTES=256*1024*1024
MAX_FILES=20000
FORMAT='english-speaking-coach-backup'
VERSION=1

def digest(data):return hashlib.sha256(data).hexdigest()

def assert_idle(root):
    from practice_runtime import recent_reviews
    from live_companion import TERMINAL
    root=Path(root)
    dbpath=root/'Live/companion.sqlite3'
    if dbpath.exists():
        with sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro',uri=True) as db:
            for desired,raw in db.execute('SELECT desired,state FROM runs'):
                row=json.loads(raw)
                if desired!='stopped' and row.get('status') not in TERMINAL and not row.get('close_epoch'):
                    raise ValueError('该目录有正在进行的英语练习，请结束后再切换。')
    if any(j.get('auto_review') and j['status'] in {'queued','reading','generating','checking','saving'} for j in recent_reviews(root)):
        raise ValueError('该目录还有未完成复盘，请完成或处理错误后再切换。')

def tree_fingerprint(root):
    return {rel:digest(file.read_bytes()) for rel,file in source_files(Path(root))}

def check_root(root):
    root=Path(root).expanduser().resolve()
    if root in {Path(root.anchor),Path.home().resolve()} or root==SKILL_ROOT or SKILL_ROOT in root.parents:
        raise ValueError('请选择 Skill 外的专用学习目录，不能使用系统、主目录或 Skill 目录。')
    return root

def counts(root):
    root=Path(root)
    if not (root/'profile.json').is_file() or not (root/'Archive/legacy-v1.md').is_file() or not (root/'Sessions').is_dir():
        raise ValueError('目录不是完整学习档案：需要 profile.json、Sessions 和 Archive。')
    state=build_state(root)
    for file in (root/'Pending').glob('*.json'):
        validate_payload(json.loads(file.read_text()),allow_in_progress=True)
    return {'sessions':len(state['sessions']),'expressions':len(state['expressions']),
            'concepts':len(state.get('concepts',[]))}

def source_files(root, include_live=False):
    for file in sorted(Path(root).rglob('*')):
        rel=file.relative_to(root)
        if file.is_symlink():
            raise ValueError('学习目录含符号链接，未跨出目录复制：'+str(rel))
        if not file.is_file():continue
        if file.name in {'.write.lock','.review-worker.lock'}:continue
        if rel.parts[0]=='Live':continue
        yield rel.as_posix(),file

def backup_bytes(root, project_page=None, include_live=False):
    root=Path(root).resolve(); payload={}; total=0
    with writer(root):
        summary=counts(root)
        for rel,file in source_files(root):
            data=file.read_bytes();total+=len(data)
            if total>MAX_BYTES or len(payload)>=MAX_FILES:raise ValueError('档案超过网页备份上限；请让 Agent 使用文件复制并逐项校验。')
            payload['data/'+rel]=data
        if project_page:
            page=Path(project_page)
            if not page.is_file():raise ValueError('关联项目页不可读，未生成缺少该上下文的完整备份。')
            payload['context/project.md']=page.read_bytes()
        if include_live and (root/'Live/companion.sqlite3').exists():
            with tempfile.TemporaryDirectory() as temp:
                target=Path(temp)/'companion.sqlite3'
                with sqlite3.connect('file:'+str(root/'Live/companion.sqlite3')+'?mode=ro',uri=True) as src, sqlite3.connect(target) as dst:
                    src.backup(dst)
                payload['data/Live/companion.sqlite3']=target.read_bytes()
    if sum(len(v) for v in payload.values())>MAX_BYTES:raise ValueError('备份内容超过网页上限。')
    manifest={'format':FORMAT,'version':VERSION,'created_at':datetime.now(timezone.utc).isoformat(),
              'counts':summary,'includes_live':bool(include_live and any(k.startswith('data/Live/') for k in payload)),
              'includes_project_page':'context/project.md' in payload,
              'files':{name:{'sha256':digest(data),'size':len(data)} for name,data in payload.items()}}
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in payload.items():z.writestr(name,data)
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    result=output.getvalue()
    inspect_backup(result)
    return result,manifest

def inspect_backup(blob):
    if not isinstance(blob,bytes) or len(blob)>MAX_BYTES:raise ValueError('备份过大或格式不正确。')
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            entries=z.infolist()
            if len(entries)>MAX_FILES+2 or len({i.filename for i in entries})!=len(entries):
                raise ValueError('备份有重复文件或文件过多。')
            total=0
            for info in entries:
                path=PurePosixPath(info.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in info.filename or ':' in info.filename or path.as_posix()!=info.filename or info.is_dir():
                    raise ValueError('备份包含不安全路径。')
                if stat.S_ISLNK(info.external_attr>>16):raise ValueError('备份包含符号链接。')
                total+=info.file_size
                if total>MAX_BYTES:raise ValueError('备份解压后过大。')
            manifest=json.loads(z.read('manifest.json'))
            if manifest.get('format')!=FORMAT or manifest.get('version')!=VERSION:raise ValueError('不是受支持的完整学习备份。')
            wanted=manifest['files']
            if set(wanted)|{'manifest.json'} != {i.filename for i in entries}:raise ValueError('备份文件清单不一致。')
            if not {'data/profile.json','data/Archive/legacy-v1.md'}<=set(wanted):raise ValueError('备份缺少主要学习文件。')
            for name,meta in wanted.items():
                if not (name.startswith('data/') or name=='context/project.md'):raise ValueError('未知备份内容。')
                data=z.read(name)
                if len(data)!=meta['size'] or digest(data)!=meta['sha256']:raise ValueError('备份校验失败：'+name)
            return manifest
    except (zipfile.BadZipFile,KeyError,TypeError,json.JSONDecodeError,RuntimeError) as exc:
        raise ValueError('备份损坏或缺少校验清单。') from exc

def extract_verified(blob,target):
    manifest=inspect_backup(blob)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in manifest['files']:
            if not name.startswith('data/'):continue
            dest=target/name[5:];dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(z.read(name))
        if manifest['includes_project_page']:
            data=z.read('context/project.md')
            page=target/'Context'/('project-'+digest(data)[:12]+'.md')
            page.parent.mkdir(parents=True,exist_ok=True)
            if page.exists() and page.read_bytes()!=data:raise ValueError('项目页目标冲突。')
            page.write_bytes(data)
        else:page=None
    for folder in ('Sessions','Evidence','Pending'):
        (target/folder).mkdir(exist_ok=True)
    actual=counts(target)
    if actual!=manifest['counts']:raise ValueError('恢复后的课次或学习点数量与备份不一致。')
    return manifest, page

def detach_runtime(target):
    # Moved logs are not authority to resume another machine's model requests.
    for file in (target/'Runtime/Reviews').glob('*.json'):
        row=json.loads(file.read_text())
        row['auto_review']=False
        for key in ('source','worker_pid'):row.pop(key,None)
        if row.get('status') not in {'saved','error'}:
            row.update(status='error',error='这是迁移前的未完成复盘；请让 Agent 找回该场来源后继续。')
        write_json(file,row)
    shutil.rmtree(target/'Runtime/ReviewWatches',ignore_errors=True)
    dbpath=target/'Live/companion.sqlite3'
    if dbpath.exists():
        with sqlite3.connect(dbpath) as db:
            for rid,state in db.execute('SELECT id,state FROM runs').fetchall():
                row=json.loads(state)
                row.update(ready=False,status='stopped',source='',imported=True)
                db.execute('UPDATE runs SET desired=?, state=? WHERE id=?',('stopped',json.dumps(row),rid))

def save_configuration(target, page, config_path=None):
    config=Path(config_path or CONFIG_PATH)
    previous=json.loads(config.read_text()) if config.exists() else None
    cfg={'schema_version':1,'data_root':str(target),'project_page':str(page) if page else None}
    # Keep a machine-side undo receipt without putting an old machine path in the portable archive.
    if previous:
        write_json(config.parent/'location-history'/ (datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json'),previous)
    write_json(config,cfg)
    return cfg

def restore_backup(blob, destination, config_path=None, activate=True):
    if activate:assert_idle(resolve_workspace(config_path=config_path)['data_root'])
    target=check_root(destination)
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError('目标目录不是空目录；未覆盖、合并或删除任何现有档案。')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.english-restore-',dir=target.parent) as tmp:
        staging=Path(tmp)/'archive';staging.mkdir()
        manifest,page=extract_verified(blob,staging)
        page_rel=page.relative_to(staging) if page else None
        detach_runtime(staging)
        rebuild(staging)
        if counts(staging)!=manifest['counts']:raise ValueError('恢复校验失败，原配置未改变。')
        if target.exists():target.rmdir()
        os.replace(staging,target)
    cfg=save_configuration(target,target/page_rel if page_rel else None,config_path) if activate else None
    return {'status':'restored','data_root':str(target),'counts':manifest['counts'],
            'configuration':cfg,'source_retained':True}

def adopt_existing(destination, config_path=None):
    target=check_root(destination)
    summary=counts(target)
    assert_idle(target)
    assert_idle(resolve_workspace(config_path=config_path)['data_root'])
    # Validate the whole archive before accepting it, even when old configured storage is missing.
    for rel,file in source_files(target):pass
    pages=list((target/'Context').glob('project-*.md'))
    current=resolve_workspace(config_path=config_path)
    page=current.get('project_page') if Path(current['data_root']).resolve()==target else (pages[0] if len(pages)==1 else None)
    with writer(target):
        detach_runtime(target)
        cfg=save_configuration(target,page,config_path)
    return {'status':'adopted','data_root':str(target),'counts':summary,'configuration':cfg,'source_retained':True}

def move_archive(source,destination,project_page=None,config_path=None):
    source=Path(source).resolve();target=check_root(destination)
    assert_idle(source)
    if source==target or source in target.parents or target in source.parents:
        raise ValueError('新旧目录不能相同或相互包含。')
    blob,_=backup_bytes(source,project_page,include_live=True)
    result=restore_backup(blob,target,config_path)
    result.update(status='copied_and_switched',source_retained=str(source))
    return result

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['backup','inspect','restore','adopt','move'])
    p.add_argument('--file',type=Path);p.add_argument('--destination',type=Path)
    p.add_argument('--include-live',action='store_true')
    args=p.parse_args();workspace=resolve_workspace()
    if args.action=='backup':
        if not args.file:p.error('--file is required')
        if args.file.exists():raise ValueError('备份文件已存在，未覆盖。')
        blob,meta=backup_bytes(workspace['data_root'],workspace.get('project_page'),args.include_live)
        args.file.parent.mkdir(parents=True,exist_ok=True);args.file.write_bytes(blob);result=meta
    elif args.action=='inspect':
        if not args.file:p.error('--file is required')
        result=inspect_backup(args.file.read_bytes())
    elif args.action=='restore':
        if not args.file or not args.destination:p.error('--file and --destination are required')
        result=restore_backup(args.file.read_bytes(),args.destination)
    elif args.action=='adopt':
        if not args.destination:p.error('--destination is required')
        result=adopt_existing(args.destination)
    else:
        if not args.destination:p.error('--destination is required')
        result=move_archive(workspace['data_root'],args.destination,workspace.get('project_page'))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as exc:raise SystemExit(str(exc))

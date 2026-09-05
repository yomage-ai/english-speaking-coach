"""Resolve one durable learning root; keep machine settings out of distributable assets."""
from pathlib import Path
import argparse
import json
import os
import shutil
import sys

SKILL_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'english-speaking-coach' / 'workspace.json'

def resolve_workspace(root=None, vault=None, config_path=None, skill_root=None, legacy_root=None):
    config_path = Path(config_path or CONFIG_PATH)
    skill_root = Path(skill_root or SKILL_ROOT)
    if root is not None:
        return {'data_root':str(Path(root).expanduser().resolve()), 'project_page':None, 'mode':'explicit', 'config_path':str(config_path)}
    if vault is not None:
        directory = Path(vault).expanduser().resolve() / 'vault/Work/Projects'
        return {'data_root':str(directory / 'English-Speaking'), 'project_page':str(directory / 'PRJ-ENGLISH-SPEAKING.md'), 'mode':'vault', 'config_path':str(config_path)}
    if config_path.exists():
        cfg = json.loads(config_path.read_text(encoding='utf-8'))
        if cfg.get('schema_version') != 1 or not Path(cfg.get('data_root','')).is_absolute():
            raise ValueError('Invalid workspace configuration; do not silently create a second archive.')
        return {**cfg, 'mode':'configured', 'config_path':str(config_path)}
    # Old layouts are opt-in migration inputs, never another person's default.
    legacy = Path(legacy_root) if legacy_root is not None else None
    if legacy is not None and (legacy / 'state.json').is_file() and (legacy / 'Sessions').is_dir():
        return {'data_root':str(legacy.resolve()), 'project_page':str(legacy.parent / 'PRJ-ENGLISH-SPEAKING.md'), 'mode':'existing-vault', 'config_path':str(config_path)}
    return {'data_root':str((skill_root / 'data').resolve()), 'project_page':None, 'mode':'skill-data', 'config_path':str(config_path)}

def configure(destination, project_page=None, copy_existing=False, config_path=None):
    from practice_store import build_state, initialize, rebuild, write_json
    config_path = Path(config_path or CONFIG_PATH)
    current = resolve_workspace(config_path=config_path)
    source = Path(current['data_root'])
    target = Path(destination).expanduser().resolve()
    if current['mode']=='configured' and not source.is_dir():
        raise ValueError('Configured archive is unavailable; restore it or reconnect its drive before switching. No empty replacement was created.')
    if target in {Path(target.anchor), Path.home().resolve(), SKILL_ROOT.resolve()}:
        raise ValueError('Choose a dedicated learning folder, not the home, filesystem or skill root.')
    if source.resolve() != target and source.exists() and any(source.iterdir()):
        if not copy_existing:
            raise ValueError('Existing learning data found. Use --copy-existing after reviewing the destination; the source will be retained.')
        if target.exists() and any(target.iterdir()):
            raise ValueError('Destination is not empty; no files were overwritten.')
        if source.resolve() in target.parents or target in source.resolve().parents:
            raise ValueError('Source and destination cannot contain each other.')
        before = build_state(source)
        shutil.copytree(source, target, dirs_exist_ok=True)
        if build_state(target) != before:
            raise ValueError('Copy verification failed; original configuration and source preserved.')
        import hashlib
        for file in source.rglob('*'):
            if file.is_file() and hashlib.sha256(file.read_bytes()).digest() != hashlib.sha256((target / file.relative_to(source)).read_bytes()).digest():
                raise ValueError('Copy hash mismatch; original configuration preserved.')
    if not target.exists() or not any(target.iterdir()):
        initialize(target); rebuild(target)
    else:
        build_state(target)
    page = str(Path(project_page).expanduser().resolve()) if project_page else (current.get('project_page') if source.resolve() == target else None)
    cfg = {'schema_version':1, 'data_root':str(target), 'project_page':page}
    write_json(config_path, cfg)
    return {**cfg, 'config_path':str(config_path), 'source_retained':str(source) if copy_existing else None}

def backup_embedded_data(root):
    """One atomic recovery copy outside the skill, only for skill-internal data."""
    import tempfile
    import zipfile
    root=Path(root).resolve()
    if SKILL_ROOT.resolve() not in root.parents:return None
    destination=CONFIG_PATH.parent/'backups'/'latest.zip'
    destination.parent.mkdir(parents=True,exist_ok=True)
    handle,temp=tempfile.mkstemp(dir=destination.parent,prefix='.latest-',suffix='.zip');os.close(handle)
    try:
        with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for file in root.rglob('*'):
                if file.is_file() and file.name!='.write.lock':archive.write(file,file.relative_to(root))
        with zipfile.ZipFile(temp) as archive:
            if archive.testzip() is not None:raise ValueError('Recovery backup verification failed')
        os.replace(temp,destination)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return str(destination)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['show','configure'])
    p.add_argument('--data-root',type=Path)
    p.add_argument('--project-page',type=Path)
    p.add_argument('--copy-existing',action='store_true')
    args=p.parse_args()
    if args.command=='configure' and not args.data_root:p.error('--data-root is required')
    result=resolve_workspace() if args.command=='show' else configure(args.data_root,args.project_page,args.copy_existing)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as exc:print(str(exc),file=sys.stderr);sys.exit(1)

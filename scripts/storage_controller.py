"""Same-origin storage plans; switching requires an idle workspace-owned server."""
import base64
import json
from pathlib import Path
import secrets
import time
from archive_transfer import (backup_bytes, inspect_backup, extract_verified, counts,
                              check_root, restore_backup, adopt_existing, MAX_BYTES, tree_fingerprint, assert_idle)
from practice_runtime import recent_reviews
from workspace_config import CONFIG_PATH, resolve_workspace

class StorageController:
    def __init__(self, server, workspace=False, config_path=None):
        self.server=server;self.workspace=workspace
        self.config_path=Path(config_path or CONFIG_PATH);self.plans={}

    def info(self):
        cfg=resolve_workspace(config_path=self.config_path)
        root=self.server.archive.root
        page=cfg.get('project_page') if Path(cfg['data_root']).resolve()==root else None
        return {'can_switch':self.workspace,'project_page':page,
                'available':(root/'profile.json').is_file(),'transfer_limit_bytes':MAX_BYTES}

    def idle(self):
        from live_companion import TERMINAL
        root=self.server.archive.root
        # Read-only check: never initialize a missing old archive to allow recovery.
        dbpath=root/'Live/companion.sqlite3'
        if dbpath.exists():
            import sqlite3
            with sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro',uri=True) as db:
                for desired,raw in db.execute('SELECT desired,state FROM runs'):
                    state=json.loads(raw)
                    if desired!='stopped' and state.get('status') not in TERMINAL and not state.get('close_epoch'):
                        raise ValueError('英语练习还在进行，请结束语音后再切换目录。')
        worker=getattr(self.server,'review_worker',None)
        if worker and worker.busy:raise ValueError('复盘正在生成，请保存完成后再切换目录。')
        for j in recent_reviews(root):
            if j.get('auto_review') and j['status'] in {'queued','reading','generating','checking','saving'}:
                raise ValueError('本地还有未完成复盘，请先完成或处理错误后再切换目录。')

    def export(self, body):
        if set(body)-{'include_live'} or type(body.get('include_live',False)) is not bool:
            raise ValueError('无效的备份选项。')
        return backup_bytes(self.server.archive.root,self.info()['project_page'],body.get('include_live',False))[0]

    def preview(self, body):
        if not self.workspace:raise ValueError('这是绑定单个目录的预览服务；请让 Agent 用当前工作区模式启动后迁移。')
        if set(body)-{'action','destination','backup_base64'}:raise ValueError('未知迁移字段。')
        self.idle()
        action=body.get('action');target=check_root(body.get('destination',''))
        root=self.server.archive.root
        if not body.get('destination') or not Path(body['destination']).expanduser().is_absolute():
            raise ValueError('请填写新电脑或本机上的绝对目录路径。')
        if target==root or target in root.parents or root in target.parents:
            raise ValueError('请选择与当前学习目录分开的专用目录。')
        blob=None;manifest=None
        if action=='adopt':
            assert_idle(target)
            summary=counts(target)
        elif action in {'move','restore'}:
            if target.exists() and (not target.is_dir() or any(target.iterdir())):
                raise ValueError('目标目录不是空目录；不会覆盖或合并已有学习记录。')
            if action=='move':
                blob,manifest=backup_bytes(root,self.info()['project_page'],True)
            else:
                try:blob=base64.b64decode(body['backup_base64'],validate=True)
                except (ValueError,KeyError):raise ValueError('请选择完整备份 ZIP。')
                manifest=inspect_backup(blob)
                # Hash checks alone are insufficient: verify the canonical lesson schema as well.
                import tempfile
                with tempfile.TemporaryDirectory(prefix='english-backup-check-') as tmp:
                    extract_verified(blob,Path(tmp))
            summary=manifest['counts']
        else:raise ValueError('请选择搬动当前档案、恢复备份或使用已有档案。')
        self.plans={k:v for k,v in self.plans.items() if time.time()-v['created']<600}
        if len(self.plans)>=3:self.plans.pop(next(iter(self.plans)))
        token=secrets.token_urlsafe(24)
        self.plans[token]={'action':action,'target':str(target),'root':str(root),
            'target_fingerprint':tree_fingerprint(target) if action=='adopt' else None,
            'blob':blob,'manifest':manifest,'counts':summary,'created':time.time()}
        return {'plan':token,'action':action,'destination':str(target),'counts':summary,
                'source_retained':str(root),'includes_live':manifest.get('includes_live',False) if manifest else None,
                'message':'校验完成。确认后网页与下次练习使用这个目录；原目录保留，不覆盖、不合并。'}

    def apply(self, body):
        if set(body)!={'plan'}:raise ValueError('无效的迁移确认。')
        plan=self.plans.get(body['plan'])
        if not plan or time.time()-plan['created']>600:raise ValueError('预览已过期，请重新校验。')
        if not self.workspace or str(self.server.archive.root)!=plan['root']:raise ValueError('当前目录已改变，请重新校验。')
        self.idle()
        if plan['action']=='adopt':
            assert_idle(plan['target'])
            if counts(plan['target'])!=plan['counts'] or tree_fingerprint(plan['target'])!=plan['target_fingerprint']:raise ValueError('待使用的档案已改变，请重新校验。')
        if plan['action']=='move':
            _,fresh=backup_bytes(plan['root'],self.info()['project_page'],True)
            if fresh['files']!=plan['manifest']['files']:raise ValueError('源档案已改变，请重新校验，避免遗漏新记录。')
        self.server.stop_background()
        try:
            if plan['action']=='adopt':
                result=adopt_existing(plan['target'],self.config_path)
            else:result=restore_backup(plan['blob'],plan['target'],self.config_path)
            from library_server import Archive, SKILL_ROOT
            self.server.archive=Archive(plan['target'],SKILL_ROOT)
            self.plans.clear()
            result['message']='已切换到校验后的学习目录。原目录仍保留。'
            return result
        finally:self.server.start_background()

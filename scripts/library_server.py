"""Read-only local learning archive. Facts remain in the coach's Markdown files."""
from collections import Counter
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, unquote
import argparse
import hashlib
import json
import os
import re
import sys
import threading
import signal
import sqlite3
import secrets
import subprocess
import shutil

SKILL_ROOT = Path(__file__).resolve().parents[1]
APP = SKILL_ROOT / 'assets/library'
from practice_runtime import code_revision
LOADED_CODE_REVISION = code_revision(SKILL_ROOT)
from workspace_config import resolve_workspace, CONFIG_PATH, default_data_root
from progress_views import period_rows, progress_list, progress_detail
from practice_context import voice_sources
DEFAULT_ROOT = Path(resolve_workspace()['data_root'])
LABELS = {'not_tested': '尚未尝试', 'source_text': '看原句说出', 'keywords': '借关键词说出', 'independent': '曾独立说出', 'transfer': '曾换场景使用'}


def book_for(session):
    text = ' '.join([session['title'], *session.get('topics', []), *session.get('scenarios', [])])
    if re.search('旅行|机场|出租|打车|点餐', text):
        return '旅行出行'
    if re.search('宠物|兽医|领养', text):
        return '宠物咨询'
    if re.search('日常|音乐|计划|聊天', text):
        return '日常聊天'
    return (session.get('topics') or ['其他主题'])[0]


class Archive:
    def __init__(self, root, skill_root):
        self.root = Path(root).resolve()
        sys.path.insert(0, str(Path(skill_root).resolve() / 'scripts'))
        from practice_store import build_state
        from practice_view import read_record
        self.build_state, self.read_record = build_state, read_record
        self.lock = threading.Lock()
        self.signature = None
        self.data = None
        self.open_token = secrets.token_urlsafe(32)

    def fingerprint(self):
        files = [self.root / 'Archive/legacy-v1.md', self.root / 'profile.json', *sorted((self.root / 'Sessions').glob('*.md')), *sorted((self.root / 'Evidence').glob('*.md'))]
        return tuple((str(p.relative_to(self.root)), p.stat().st_mtime_ns, p.stat().st_size) for p in files)

    def load(self):
        with self.lock:
            signature = self.fingerprint()
            if signature == self.signature:
                return self.data
            # A save may change more than one source file; never publish a mixed read.
            for _ in range(3):
                signature = self.fingerprint()
                state = self.build_state(self.root)
                sessions, details = [], {}
                for raw in reversed(state['sessions']):
                    s = {**raw, 'book': book_for(raw), 'expression_count': len(raw.get('expression_ids', []))}
                    record, supplement = self.read_record(self.root, raw, state)
                    sessions.append(s)
                    details[s['id']] = {**s, 'evidence_note': record.get('evidence_note', ''), 'excerpts': record.get('expressions', []), 'supplement': supplement}
                by_id = {s['id']: s for s in sessions}
                terms = []
                for raw in reversed(state['expressions']):
                    source = by_id[raw['source_session']]
                    term = {**raw, 'book': source['book'], 'source_title': source['title'], 'date': source['date'], 'state_label': LABELS.get(raw['mastery'], '未记录')}
                    term['sources'] = [{'id': sid, 'title': by_id[sid]['title'], 'date': by_id[sid]['date']} for sid in raw.get('seen_in_sessions', [source['id']]) if sid in by_id]
                    terms.append(term)
                # Concepts extracted from a longer utterance get their own vocabulary card.
                # If the whole expression already is that concept, reuse its card.
                for concept in state.get('concepts',[]):
                    matching=next((t for t in terms if t['english'].casefold().strip(' .?!')==concept['term'].casefold().strip(' .?!') and t['id'] in {x for e in concept['events'] for x in e.get('expression_ids',[])}),None)
                    if matching:
                        matching['concept_id']=concept['id'];continue
                    events=concept['events'];source=by_id[events[0]['session']]
                    quoted=next((e for e in reversed(events) if e['quote_kind']=='utterance'),None)
                    related=[t for t in terms if t['id'] in {x for e in events for x in e.get('expression_ids',[])}]
                    terms.insert(0,{'id':concept['id'],'concept_id':concept['id'],'english':concept['term'],'chinese':concept['meaning'],'kind':'知识点','original':quoted['quote'] if quoted else None,'mastery':'independent' if concept['level'] in {'stable','independent'} else 'source_text' if concept['level']=='supported' else 'not_tested','state_label':concept['level_label'],'source_session':source['id'],'source_title':source['title'],'date':source['date'],'updated':concept['last_date'],'note':events[-1]['note'],'next_review':min([t['next_review'] for t in related] or [concept['last_date']]),'book':source['book'],'sources':[{'id':sid,'title':by_id[sid]['title'],'date':by_id[sid]['date']} for sid in sorted({e['session'] for e in events})],'seen_in_sessions':sorted({e['session'] for e in events})})
                for session in sessions:
                    session['card_count'] = sum(session['id'] in t.get('seen_in_sessions', [t['source_session']]) for t in terms)
                    details[session['id']]['card_count'] = session['card_count']
                books = [{'name': name, 'count': count, 'sessions': sum(s['book'] == name for s in sessions)} for name, count in Counter(t['book'] for t in terms).items()]
                if signature == self.fingerprint():
                    break
            else:
                raise ValueError('学习记录正在保存，请稍后刷新。')
            self.data = {'sessions': sessions, 'details': details, 'terms': terms, 'books': books, 'concepts':state.get('concepts',[]), 'profile': state['profile'], 'revision': hashlib.sha256(repr(signature).encode()).hexdigest()[:12], 'source_updated_at': datetime.fromtimestamp(max(x[1] for x in signature) / 1e9).astimezone().isoformat(timespec='seconds')}
            self.signature = signature
            return self.data

    def query(self, path, args):
        if path=='/api/identity':
            return {'application':'english-speaking-coach','pid':os.getpid(),'data_root':str(self.root),'skill_root':str(SKILL_ROOT),
                    'code_revision':LOADED_CODE_REVISION}
        if path == '/api/live':
            from live_companion import LiveStore
            return LiveStore(self.root).view(args)
        if path=='/api/storage':
            embedded = self.root.is_relative_to(SKILL_ROOT.resolve())
            return {'data_root':str(self.root),'skill_root':str(SKILL_ROOT),'viewer_root':str(APP),'config_path':str(CONFIG_PATH),'default_data_root':str(default_data_root()),'backup_path':str(CONFIG_PATH.parent/'backups/latest.zip'),'embedded':embedded,'location':'旧版 Skill 内数据目录' if embedded else '独立的本地学习目录','project_page':resolve_workspace().get('project_page'), 'open_token':self.open_token}
        data = self.load()
        meta = {'revision': data['revision'], 'source_updated_at': data['source_updated_at']}
        sessions, terms = data['sessions'], data['terms']
        if path == '/api/overview':
            return {**meta, 'today': date.today().isoformat(), 'counts': {'sessions': len(sessions), 'terms': len(terms), 'days': len({s['date'] for s in sessions}), 'books': len(data['books'])}, 'books': data['books'], 'profile': data['profile'], 'latest': data['details'][sessions[0]['id']] if sessions else None, 'recent': sessions[:4], 'review_terms': [t for t in terms if t.get('next_review', '9999') <= date.today().isoformat()][:3]}
        if path == '/api/review':
            sources = voice_sources(args.get('thread'), args.get('voice'))
            matches = [s for s in sessions if set(sources) <= set(s.get('source_ids', []))]
            if len(matches) > 1:
                raise ValueError('同一场 Voice 有多份复盘，请让 Agent 核对记录来源。')
            from practice_runtime import review_status
            job = review_status(self.root, args.get('thread'), args.get('voice'))
            if not matches and job['status'] == 'practicing' and job.get('run_id'):
                from live_companion import LiveStore
                with LiveStore(self.root).db() as db:
                    row = db.execute('SELECT state FROM runs WHERE id=?', (job['run_id'],)).fetchone()
                state = json.loads(row['state']) if row else {}
                if state.get('voice_id') == args.get('voice') and (state.get('voice_closed_at') or state.get('close_epoch')):
                    job['status'] = job['stage'] = 'waiting'
            saved = matches[0] if matches else {}
            public_job={k:v for k,v in job.items() if k not in {'source','worker_pid'}}
            return {**meta, **public_job, **({'status':'saved', 'stage':'saved', 'elapsed_seconds':None} if matches else {}),
                    'thread_id':args.get('thread'), 'voice_id':args.get('voice'),
                    'created_epoch': job.get('created_epoch', job.get('started_epoch', 0)),
                    'title': saved.get('title') or job.get('title', '本次英语练习'),
                    'practice_time': saved.get('practiced_at') or (datetime.fromtimestamp(job['created_epoch']).astimezone().isoformat() if job.get('created_epoch') else ''),
                    'session_id': saved.get('id')}
        if path == '/api/reviews':
            from practice_runtime import recent_reviews
            jobs = recent_reviews(self.root)
            # Keep delayed reviews discoverable even after newer practices finish.
            pending = [j for j in jobs if not any(set(voice_sources(j['thread_id'], j['voice_id'])) <= set(s.get('source_ids', [])) for s in sessions)]
            recent = jobs[:5]
            selected = recent + [j for j in pending if j not in recent]
            return {**meta, 'items':[self.query('/api/review', {'thread':j['thread_id'],'voice':j['voice_id']}) for j in selected]}
        if path.startswith('/api/sessions/'):
            sid = path.rsplit('/', 1)[1]
            if sid not in data['details']:
                raise KeyError('没有找到这次练习。')
            return {**meta, **data['details'][sid]}
        if path.startswith('/api/terms/'):
            term = next((t for t in terms if t['id'] == path.rsplit('/', 1)[1]), None)
            if term is None:
                raise KeyError('没有找到这条表达。')
            return {**meta, **term}
        if path in {'/api/sessions', '/api/terms'}:
            rows = self.filter(sessions if path.endswith('sessions') else terms, args, data)
            page = max(1, int(args.get('page', '1')))
            limit = max(1, min(60, int(args.get('limit', '12'))))
            pages = max(1, (len(rows) + limit - 1) // limit)
            page = min(page, pages)
            # Scope counts and the card grid use the same session. Theme chips must not
            # silently show global totals while the grid remains session-filtered.
            scoped = self.filter(terms, {'session':args['session']}, data) if args.get('session') else terms
            books = [{'name':name,'count':count} for name,count in Counter(t['book'] for t in scoped).items()]
            latest = sessions[0] if sessions else None
            return {**meta, 'items': rows[(page - 1) * limit:page * limit], 'total': len(rows), 'page': page, 'pages': pages, 'limit': limit,
                    'books': books if path.endswith('terms') else data['books'],
                    'scope': {'session_id':args.get('session'), 'session_title':data['details'].get(args.get('session'),{}).get('title'),
                              'count':len(scoped), 'all_count':len(terms)},
                    'latest_session': {'id':latest['id'], 'title':latest['title']} if latest else None}
        if path == '/api/progress':
            return {**meta, **progress_list(data['concepts'], args)}
        if path.startswith('/api/progress/'):
            return {**meta, **progress_detail(data['concepts'], path.rsplit('/',1)[1], args)}
        if path == '/api/stats':
            selected = self.filter(sessions, args, data)
            ids = {s['id'] for s in selected}
            included = [t for t in terms if t['source_session'] in ids]
            rows=period_rows(data['concepts'], args)
            priorities={'improved':0,'revisit':1,'first':2,'practiced':3}
            highlights=sorted(rows,key=lambda r:priorities[r['change_kind']])[:3]
            observations=[{'id':s['id'],'date':s['date'],'text':text} for s in selected for text in s.get('progress',[])][:3]
            return {**meta, 'counts':{'sessions':len(selected),'days':len({s['date'] for s in selected}),'terms':len(included)},
                    'activity':dict(sorted(Counter(s['date'] for s in selected).items())),
                    'highlights':highlights,'progress_total':len(rows),'observations':observations,
                    'review':sorted(rows,key=lambda r:(not r['needs_revisit'],r['level']=='stable'))[:2]}
        raise KeyError('页面不存在。')

    @staticmethod
    def filter(rows, args, data):
        query = args.get('q', '').strip().casefold()
        start, end = args.get('from', ''), args.get('to', '')
        for value in (start, end):
            if value:
                date.fromisoformat(value)
        if start and end and start > end:
            raise ValueError('开始日期不能晚于结束日期。')
        result = []
        for row in rows:
            if args.get('session') and row['id'] not in data['details'].get(args['session'], {}).get('expression_ids', []) and args['session'] not in row.get('seen_in_sessions',[]):
                continue
            if start and row['date'] < start or end and row['date'] > end:
                continue
            if args.get('book') and row['book'] != args['book']:
                continue
            if args.get('state') and row.get('mastery') != args['state']:
                continue
            if args.get('due') == '1' and row.get('next_review', '9999') > date.today().isoformat():
                continue
            searchable = data['details'].get(row['id'], row)
            if query and query not in json.dumps(searchable, ensure_ascii=False).casefold():
                continue
            result.append(row)
        return result


def open_learning_directory(root):
    """Ask the desktop to open only this server's configured data directory."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('学习目录暂不可用，请先让 Agent 检查存储位置。')
    if sys.platform == 'win32':
        os.startfile(str(root))
    else:
        command = '/usr/bin/open' if sys.platform == 'darwin' else shutil.which('xdg-open')
        if not command:
            raise ValueError('当前环境没有可用的文件管理器；可复制下方目录路径。')
        result = subprocess.run([command, str(root)], capture_output=True, timeout=8)
        if result.returncode:
            raise ValueError('文件管理器未能打开目录；可复制下方路径，或让 Agent 检查。')
    return {'status':'requested', 'message':'已请求在文件管理器中打开学习目录。', 'data_root':str(root)}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        paths={'/api/storage/open','/api/storage/backup','/api/storage/preview','/api/storage/apply','/api/review/retry'}
        if self.path not in paths:return self.send_payload(404, {'error':'操作不存在。'})
        host=self.headers.get('Host','');origin=self.headers.get('Origin')
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        token=self.headers.get('X-Coach-Token','')
        if host not in allowed or (origin is not None and origin!='http://'+host) or not secrets.compare_digest(token,self.server.archive.open_token):
            return self.send_payload(403,{'error':'请从本机学习网页执行此操作。'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            limit=360*1024*1024 if self.path=='/api/storage/preview' else 8192
            if not 0<length<=limit or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                raise ValueError('无效的本地操作请求。')
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):raise ValueError('无效的本地操作内容。')
            from contextlib import nullcontext
            with getattr(self.server,'gate',nullcontext()):
                if not secrets.compare_digest(token,self.server.archive.open_token):
                    return self.send_payload(403,{'error':'学习目录已切换，请刷新页面后重试。'})
                if self.path=='/api/storage/open':
                    if body!={}:raise ValueError('只能打开当前学习目录。')
                    return self.send_payload(200,open_learning_directory(self.server.archive.root))
                if self.path=='/api/review/retry':
                    if set(body)!={'thread','voice'}:raise ValueError('需要指定本场 Voice。')
                    from practice_runtime import review_file
                    from review_worker import enqueue
                    path=review_file(self.server.archive.root,body['thread'],body['voice'])
                    if not path.exists():raise ValueError('未找到这场复盘登记。')
                    job=json.loads(path.read_text())
                    from live_companion import find_source
                    source=job.get('source') or find_source(body['thread'])
                    result=enqueue(self.server.archive.root,body['thread'],body['voice'],source,retry=True)
                    return self.send_payload(200,{k:v for k,v in result.items() if k!='source'})
                controller=self.server.storage
                if self.path=='/api/storage/backup':
                    return self.send_bytes(200,controller.export(body),'application/zip')
                result=controller.preview(body) if self.path.endswith('/preview') else controller.apply(body)
                self.send_payload(200,result)
        except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired) as exc:
            self.send_payload(400,{'error':'无法打开学习目录；可复制目录路径。' if self.path=='/api/storage/open' else str(exc)})

    def do_GET(self):
        from contextlib import nullcontext
        with getattr(self.server,'gate',nullcontext()):
            return self.read_get()

    def read_get(self):
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        if self.headers.get('Host', '').split(':')[0] not in {'127.0.0.1', 'localhost'}:
            return self.send_payload(403, {'error': '仅可从本机访问。'})
        try:
            if path.startswith('/api/'):
                args = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
                data=self.server.archive.query(path,args)
                if path=='/api/storage' and hasattr(self.server,'storage'):data.update(self.server.storage.info())
                if path=='/api/identity':data['workspace_managed']=getattr(self.server,'workspace_managed',False)
                return self.send_payload(200,data)
            assets = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'), '/app.css': ('app.css', 'text/css'), '/app.js': ('app.js', 'text/javascript'), '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
            if path in assets:
                filename, mime = assets[path]
                return self.send_bytes(200, (APP / filename).read_bytes(), mime)
            if path in {'/live.js', '/live.css', '/storage.js'}:
                return self.send_bytes(200, (APP / path[1:]).read_bytes(), 'text/javascript' if path.endswith('.js') else 'text/css')
            if re.fullmatch(r'/records/SES-\d{8}-\d{3}\.md', path):
                sid = Path(path).stem
                if sid in self.server.archive.load()['details']:
                    return self.send_bytes(200, (self.server.archive.root / 'Sessions' / (sid + '.md')).read_bytes(), 'text/plain')
            raise KeyError('页面不存在。')
        except KeyError as exc:
            self.send_payload(404, {'error': str(exc).strip("'")})
        except (ValueError, TypeError) as exc:
            self.send_payload(400, {'error': str(exc)})
        except Exception as exc:
            self.log_error('Archive read failed: %s', exc)
            self.send_payload(503, {'error': '双语缓存暂不可读，请让 Agent 检查；正式学习记录仍可查看。' if path == '/api/live' else '暂时无法读取本机学习记录，请稍后刷新；若仍失败，请让 Agent 检查数据源。'})

    def do_HEAD(self):
        self.do_GET()

    def send_payload(self, status, data):
        self.send_bytes(status, json.dumps(data, ensure_ascii=False).encode(), 'application/json')

    def send_bytes(self, status, payload, mime):
        self.send_response(status)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)


class LibraryServer(ThreadingHTTPServer):
    def __init__(self, address, root, skill_root=SKILL_ROOT, workspace=False, config_path=None, background=True):
        super().__init__(address,Handler)
        self.archive=Archive(root,skill_root)
        self.gate=threading.RLock();self.workspace_managed=workspace
        self.background=background;self.companion=self.review_worker=None
        from storage_controller import StorageController
        self.storage=StorageController(self,workspace,config_path)

    def start_background(self):
        if not self.background or not (self.archive.root/'profile.json').is_file():return
        from live_companion import LiveSupervisor
        from review_worker import ReviewWorker
        try:
            self.companion=LiveSupervisor(self.archive.root);self.companion.start()
        except (sqlite3.Error,OSError):
            self.companion=None
        self.review_worker=ReviewWorker(self.archive.root);self.review_worker.start()

    def stop_background(self):
        for worker in (self.companion,self.review_worker):
            if worker:worker.close()
        self.companion=self.review_worker=None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8897)
    loc=parser.add_mutually_exclusive_group()
    loc.add_argument('--root',type=Path)
    loc.add_argument('--workspace',action='store_true',help='Use the machine configuration at startup and support verified directory changes')
    parser.add_argument('--skill-root',type=Path,default=SKILL_ROOT)
    args=parser.parse_args()
    root=args.root or Path(resolve_workspace()['data_root'])
    server=LibraryServer(('127.0.0.1',args.port),root,args.skill_root,workspace=args.workspace or args.root is None)
    server.start_background()
    def stop(signum,frame):raise SystemExit(0)
    signal.signal(signal.SIGTERM,stop)
    print(f'English learning archive: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    finally:
        server.stop_background();server.server_close()

if __name__=='__main__':main()

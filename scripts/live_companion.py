"""Explicitly bound Voice tailer and local companion cache, separate from learning facts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid
from codex_translation import CodexTranslator, MODEL
from workspace_config import resolve_workspace

MAX_LINE = 8 * 1024 * 1024
TERMINAL = {'ended', 'error', 'expired'}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def source_identity(path):
    with Path(path).open('rb') as f:
        line = f.readline(MAX_LINE + 1)
    if not line.endswith(b'\n') or len(line) > MAX_LINE:
        raise ValueError('Voice 日志头不完整。')
    row = json.loads(line)
    if not isinstance(row, dict) or row.get('type') != 'session_meta' or not isinstance(row.get('payload'), dict) or not row['payload'].get('id'):
        raise ValueError('这不是可识别的 Codex 任务日志。')
    return row['payload']['id']


def scan_lifecycle(path):
    """Find the active Voice and last COMPLETE byte; never return transcript content."""
    active, complete = None, 0
    with Path(path).open('rb') as f:
        while True:
            line = f.readline(MAX_LINE + 1)
            if len(line) > MAX_LINE:
                raise ValueError('Voice 日志行过大，绑定已停止。')
            if not line or not line.endswith(b'\n'):
                break
            complete = f.tell()
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            p = row.get('payload', {})
            if not isinstance(p, dict):
                continue
            if row.get('type') == 'realtime_item':
                if p.get('type') == 'realtime_session_started':
                    active = p.get('realtime_session_id')
                elif p.get('type') == 'realtime_session_closed' and p.get('realtime_session_id') == active:
                    active = None
    return active, complete


def find_source(thread_id):
    if not re.fullmatch(r'[0-9a-f-]{36}', thread_id or ''):
        raise ValueError('需要明确的当前 Codex 任务 ID。')
    root = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'sessions'
    matches = list(root.glob('*/*/*/rollout-*-' + thread_id + '.jsonl'))
    if len(matches) != 1:
        raise ValueError('没有找到唯一的当前任务日志；请让 Agent 指定已核实的源文件。')
    return matches[0]


def companion_preferences(root):
    """Read-only discovery for resume; never initialize runtime data during learning recovery."""
    path = Path(root) / 'Live' / 'companion.sqlite3'
    if not path.exists():
        return {'enabled': False}
    try:
        db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
        try:
            return {'enabled': db.execute("SELECT 1 FROM meta WHERE key='enabled' AND value='true'").fetchone() is not None}
        finally:
            db.close()
    except (sqlite3.Error, OSError):
        return {'enabled': False, 'error': '双语缓存暂不可读；可继续正常口语练习，请让 Agent 检查伴随缓存。'}


class LiveStore:
    def __init__(self, root):
        directory = Path(root) / 'Live'
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'companion.sqlite3'
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, desired TEXT NOT NULL, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS segments (
                  seq INTEGER PRIMARY KEY AUTOINCREMENT, run TEXT NOT NULL, id TEXT NOT NULL,
                  role TEXT NOT NULL, text TEXT NOT NULL, timestamp TEXT, ordinal INTEGER,
                  ingested_at TEXT NOT NULL, chinese TEXT, status TEXT NOT NULL DEFAULT 'pending',
                  attempts INTEGER NOT NULL DEFAULT 0, translated_at TEXT, latency REAL,
                  UNIQUE(run,id));
                CREATE INDEX IF NOT EXISTS segment_queue ON segments(run,status,seq);
            ''')
        try:
            directory.chmod(0o700); self.path.chmod(0o600)
        except OSError:
            pass

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def active(self):
        with self.db() as db:
            row = db.execute("SELECT runs.* FROM runs JOIN meta ON meta.value=runs.id WHERE meta.key='active'").fetchone()
        if row:
            return {**json.loads(row['state']), 'desired': row['desired']}

    def save(self, state, db=None):
        clean = {k: v for k, v in state.items() if k != 'desired'}
        if db is not None:
            db.execute('UPDATE runs SET state=? WHERE id=?', (json.dumps(clean, ensure_ascii=False), state['id']))
        else:
            with self.db() as conn:
                self.save(state, conn)

    def bind(self, thread_id, source, model=MODEL, demo=False):
        source = Path(source).expanduser().resolve()
        if source_identity(source) != thread_id:
            raise ValueError('源文件身份与指定任务不一致；未绑定。')
        voice_id, complete = scan_lifecycle(source)
        state = {'id': str(uuid.uuid4()), 'thread_id': thread_id, 'source': str(source),
            'voice_id': voice_id, 'cursor': 0 if voice_id else complete,
            'file_identity': [source.stat().st_dev, source.stat().st_ino], 'demo': demo,
            'created_at': now(), 'created_epoch': time.time(), 'model': model, 'effort': 'low',
            'status': 'starting', 'heartbeat': None, 'last_transcript_at': None, 'last_read_at': None,
            'last_activity_epoch': time.time(), 'close_epoch': None, 'error': None,
            'invalid_lines': 0, 'rewinds': 0, 'has_partial_line': False, 'ready': False}
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT runs.* FROM runs JOIN meta ON meta.value=runs.id WHERE meta.key='active'").fetchone()
            existing = {**json.loads(row['state']), 'desired':row['desired']} if row else None
            if existing and existing['desired'] != 'stopped' and existing['status'] not in TERMINAL:
                if existing['source'] == str(source) and existing['voice_id'] in {None, voice_id} and existing['model'] == model:
                    return existing
                raise ValueError('另一场双语伴随尚未结束；保留当前绑定，不能为新练习停止其他任务。')
            db.execute('INSERT INTO runs VALUES (?,?,?)', (state['id'], 'running', json.dumps(state)))
            db.execute("INSERT OR REPLACE INTO meta VALUES ('active',?)", (state['id'],))
            if not demo:
                db.execute("INSERT OR REPLACE INTO meta VALUES ('enabled','true')")
            # Transient transcript cache expires after seven days; learning facts are untouched.
            for row in db.execute('SELECT id,state FROM runs').fetchall():
                old = json.loads(row['state'])
                if row['id'] != state['id'] and time.time() - old['created_epoch'] > 7 * 86400:
                    db.execute('DELETE FROM segments WHERE run=?', (row['id'],))
                    db.execute('DELETE FROM runs WHERE id=?', (row['id'],))
        return self.active()

    def enabled(self):
        with self.db() as db:
            return db.execute("SELECT 1 FROM meta WHERE key='enabled' AND value='true'").fetchone() is not None

    def stop(self, run_id, immediate=False):
        with self.db() as db:
            row = db.execute('SELECT state FROM runs WHERE id=?', (run_id,)).fetchone()
            if not row:
                raise ValueError('没有这个绑定；未停止其他练习。')
            desired = 'stopped' if immediate or json.loads(row['state'])['status'] in TERMINAL else 'drain'
            db.execute('UPDATE runs SET desired=? WHERE id=?', (desired, run_id))
            return desired

    def finish(self, state):
        if state['status'] not in TERMINAL:
            raise ValueError('Only a terminal binding can be finished')
        state['ready'] = False
        clean = {k:v for k,v in state.items() if k != 'desired'}
        with self.db() as db:
            result = db.execute("UPDATE runs SET desired='stopped',state=? WHERE id=?",
                                (json.dumps(clean, ensure_ascii=False), state['id']))
            if result.rowcount != 1:
                raise ValueError('Unknown binding; nothing was stopped')

    def resume(self, run_id):
        active = self.active()
        if not active or active['id'] != run_id:
            raise ValueError('只能恢复当前明确绑定；没有切换到其他任务。')
        if source_identity(active['source']) != active['thread_id']:
            raise ValueError('源文件身份已改变，未恢复。')
        active['status'] = 'starting'; active['error'] = None; active['ready'] = False
        active['last_activity_epoch'] = time.time(); active['created_epoch'] = time.time()
        with self.db() as db:
            self.save(active, db)
            db.execute("UPDATE runs SET desired='running' WHERE id=?", (run_id,))
            db.execute("UPDATE segments SET status='pending',attempts=0 WHERE run=? AND status IN ('failed','translating')", (run_id,))

    def disable(self):
        active = self.active()
        if active:
            self.stop(active['id'])
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO meta VALUES ('enabled','false')")

    def read_tail(self, state):
        path = Path(state['source'])
        if source_identity(path) != state['thread_id']:
            raise ValueError('源日志身份变化，读取已停止。')
        stat = path.stat()
        identity = [stat.st_dev, stat.st_ino]
        if identity != state['file_identity'] or stat.st_size < state['cursor']:
            if source_identity(path) != state['thread_id']:
                raise ValueError('源日志被替换为其他任务，读取已停止。')
            # Same task rewritten/rotated: replay only this voice; UNIQUE(run,id) deduplicates.
            if state['voice_id'] is None:
                raise ValueError('等待期间源日志被重写，请让 Agent 重新绑定，避免误读旧 Voice。')
            state['cursor'] = 0; state['file_identity'] = identity; state['rewinds'] += 1
        rows, consumed = [], 0
        with path.open('rb') as f:
            f.seek(state['cursor'])
            while consumed < 2 * MAX_LINE:
                line = f.readline(MAX_LINE + 1)
                if len(line) > MAX_LINE:
                    raise ValueError('源日志出现过大行，读取已停止。')
                if not line:
                    state['has_partial_line'] = False; break
                if not line.endswith(b'\n'):
                    state['has_partial_line'] = True; break
                consumed += len(line); state['cursor'] = f.tell()
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeError):
                    state['invalid_lines'] += 1; continue
                if not isinstance(row, dict) or row.get('type') != 'realtime_item':
                    continue
                p = row.get('payload', {})
                if not isinstance(p, dict):
                    continue
                kind, voice = p.get('type'), p.get('realtime_session_id')
                if kind == 'realtime_session_started' and state['voice_id'] is None and isinstance(voice, str):
                    state['voice_id'] = voice; state['last_activity_epoch'] = time.time()
                if voice != state['voice_id'] or not voice:
                    continue
                if kind == 'realtime_session_closed' and state['close_epoch'] is None:
                    state['close_epoch'] = time.time()
                if kind != 'transcript_segment' or p.get('role') not in {'user', 'assistant'}:
                    continue
                if not isinstance(p.get('id'), str) or not p['id'] or not isinstance(p.get('text'), str) or not p['text'].strip():
                    continue
                if len(p['text']) > 12000:
                    raise ValueError('转写片段过长，已停止自动翻译；请让 Agent 检查来源。')
                rows.append((p, row))
        with self.db() as db:
            for p, row in rows:
                result = db.execute('''INSERT OR IGNORE INTO segments
                    (run,id,role,text,timestamp,ordinal,ingested_at) VALUES (?,?,?,?,?,?,?)''',
                    (state['id'], p['id'], p['role'], p['text'], row.get('timestamp'),
                     row.get('ordinal') if isinstance(row.get('ordinal'), int) else None, now()))
                if result.rowcount:
                    state['last_transcript_at'] = now(); state['last_activity_epoch'] = time.time()
            state['last_read_at'] = now()
            self.save(state, db)

    def recover_queue(self, run):
        with self.db() as db:
            # A committed translation is never redone. An interrupted in-flight call may be billed twice.
            db.execute("UPDATE segments SET status='pending' WHERE run=? AND status='translating'", (run,))

    def batch(self, run):
        with self.db() as db:
            rows = db.execute("SELECT * FROM segments WHERE run=? AND status='pending' ORDER BY seq LIMIT 3", (run,)).fetchall()
            selected, length = [], 0
            for row in rows:
                if selected and length + len(row['text']) > 4500:
                    break
                selected.append(dict(row)); length += len(row['text'])
            for row in selected:
                db.execute("UPDATE segments SET status='translating',attempts=attempts+1 WHERE seq=?", (row['seq'],))
        return selected

    def translated(self, run, result, latency):
        with self.db() as db:
            for item in result:
                db.execute("UPDATE segments SET chinese=?,status='translated',translated_at=?,latency=? WHERE run=? AND id=?",
                           (item['chinese'], now(), latency, run, item['id']))

    def fail_batch(self, run, batch):
        with self.db() as db:
            for row in batch:
                db.execute("UPDATE segments SET status=CASE WHEN attempts>=2 THEN 'failed' ELSE 'pending' END WHERE run=? AND id=?", (run, row['id']))
            return db.execute("SELECT COUNT(*) FROM segments WHERE run=? AND status='failed'", (run,)).fetchone()[0]

    def view(self, args=None):
        args = args or {}; active = self.active()
        with self.db() as db:
            run_id = args.get('run') or (active or {}).get('id')
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            history = [json.loads(r['state']) for r in db.execute('SELECT state FROM runs ORDER BY rowid DESC LIMIT 12')]
            state = {**json.loads(row['state']), 'desired': row['desired']} if row else None
            if run_id and not row:
                raise KeyError('没有找到这场双语缓存。')
            counts = dict(db.execute('SELECT status,COUNT(*) FROM segments WHERE run=? GROUP BY status', (run_id,)).fetchall())
            total = sum(counts.values()); pages = max(1, (total + 39) // 40)
            page = max(1, min(pages, int(args.get('page', pages))))
            rows = [dict(r) for r in db.execute('SELECT * FROM segments WHERE run=? ORDER BY seq LIMIT 40 OFFSET ?', (run_id, (page - 1) * 40))]
        if state:
            # Do not expose source filesystem paths to a subtitle reader.
            for key in ('source', 'file_identity', 'cursor'):
                state.pop(key, None)
            state['stale'] = bool(state['desired'] != 'stopped' and state['status'] not in TERMINAL and
                                  (not state.get('heartbeat_epoch') or time.time() - state['heartbeat_epoch'] > 8))
            if state['status'] == 'recovering':
                state['stale'] = time.time() - state.get('heartbeat_epoch', 0) > 90
        return {'state': state, 'items': rows, 'total': total, 'counts': counts, 'page': page, 'pages': pages,
                'enabled': self.enabled(), 'server_time': now(),
                'history': [{k: r.get(k) for k in ['id', 'created_at', 'demo', 'status', 'thread_id', 'recovery_mode', 'voice_started_at']} for r in history]}


class LiveSupervisor:
    """Ordinary background thread owned by the existing archive server, not an AI polling loop."""
    def __init__(self, root, factory=CodexTranslator):
        self.store = LiveStore(root); self.factory = factory
        self.shutdown = threading.Event(); self.client = None
        self.thread = threading.Thread(target=self.run, name='voice-companion', daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.shutdown.set()
        if self.client:
            self.client.close()
        if self.thread.is_alive():
            self.thread.join(timeout=4)

    def run(self):
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='translation-request')
        current, future, batch, connecting, drain_epoch = None, None, [], False, None
        try:
            while not self.shutdown.is_set():
                try:
                    active = self.store.active()
                    if current and (not active or active['id'] != current['id'] or active['desired'] == 'stopped'):
                        if self.client:
                            self.client.close()
                        if future:
                            # Connection close unblocks its finite wait before another binding can run.
                            try: future.result(timeout=4)
                            except Exception: pass
                        current = future = None; drain_epoch = None
                    if not current and active and active['desired'] != 'stopped' and active['status'] not in TERMINAL:
                        current = active; self.store.recover_queue(current['id'])
                        self.client = self.factory(current['model'])
                        current['status'] = 'starting'; current['ready'] = False
                        future = pool.submit(self.client.connect); connecting = True; batch = []
                    if current:
                        self.store.read_tail(current)
                        current['heartbeat'] = now(); current['heartbeat_epoch'] = time.time()
                        if active['desired'] == 'drain' and drain_epoch is None:
                            drain_epoch = time.time()
                        if future and future.done():
                            try:
                                result = future.result()
                                if connecting:
                                    current['connection'] = result; current['ready'] = True
                                else:
                                    self.store.translated(current['id'], *result)
                                    current['error'] = None
                            except Exception as exc:
                                message = str(exc) if isinstance(exc, ValueError) else '后台翻译失败，请让 Agent 检查连接。'
                                if connecting or self.store.fail_batch(current['id'], batch):
                                    raise ValueError(message)
                                current['error'] = message
                                self.client.close()
                            future = None; connecting = False
                        if not future:
                            batch = self.store.batch(current['id'])
                            if batch:
                                future = pool.submit(self.client.translate, batch)
                        current['status'] = ('starting' if connecting else 'translating' if future else
                            'draining' if current['close_epoch'] or drain_epoch else
                            'waiting_voice' if not current['voice_id'] else 'waiting_transcript')
                        end = current['close_epoch'] or drain_epoch
                        quiet = time.time() - current['last_activity_epoch']
                        if end and not future and time.time() - end >= 5 and quiet >= 5:
                            if current['has_partial_line']:
                                raise ValueError('结束时还有未写完整的转写行；请让 Agent 检查并恢复尾段。')
                            current['status'] = 'ended'
                        elif time.time() - current['created_epoch'] > 6 * 3600 or quiet > 30 * 60:
                            current['status'] = 'expired'; current['error'] = '长时间未收到新转写，已停止伴随。继续练习时由 Agent 重新绑定。'
                        if current['status'] in TERMINAL:
                            self.store.finish(current)
                        else:
                            self.store.save(current)
                    self.shutdown.wait(.35)
                except Exception as exc:
                    if current:
                        current['status'] = 'error'
                        current['ready'] = False
                        current['error'] = str(exc) if isinstance(exc, (ValueError, FileNotFoundError)) else '读取伴随数据失败；请让 Agent 检查源日志和本地缓存。'
                        self.store.finish(current)
                    if self.client:
                        self.client.close()
                    self.shutdown.wait(1)
        finally:
            if self.client:
                self.client.close()
            pool.shutdown(wait=False, cancel_futures=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    start = sub.add_parser('start')
    start.add_argument('--thread-id', default=os.environ.get('CODEX_THREAD_ID'))
    start.add_argument('--source', type=Path)
    start.add_argument('--model', default=MODEL)
    start.add_argument('--demo', action='store_true')
    stop = sub.add_parser('stop'); stop.add_argument('--run', required=True)
    resume = sub.add_parser('resume'); resume.add_argument('--run', required=True)
    sub.add_parser('disable')
    sub.add_parser('status'); sub.add_parser('probe')
    args = parser.parse_args()
    if args.command == 'probe':
        client = CodexTranslator()
        try: result = client.connect()
        finally: client.close()
    else:
        root = Path(resolve_workspace(root=args.root)['data_root'])
        if not (root / 'profile.json').is_file():
            raise ValueError('学习档案尚不可用，请让 Agent 恢复或初始化正式档案。')
        store = LiveStore(root)
        if args.command == 'start':
            if not args.thread_id:
                raise ValueError('请让 Agent 提供当前 Voice 所在任务的 ID。')
            result = store.bind(args.thread_id, args.source or find_source(args.thread_id), args.model, args.demo)
            result = {'status': 'bound', 'run_id': result['id'], 'thread_id': result['thread_id'],
                      'voice_id': result['voice_id'], 'next': 'Open the managed library at #live and verify ready=true.'}
        elif args.command == 'stop':
            desired = store.stop(args.run); result = {'status': 'stopped' if desired == 'stopped' else 'drain_requested', 'run_id': args.run}
        elif args.command == 'resume':
            store.resume(args.run); result = {'status': 'resume_requested', 'run_id': args.run}
        elif args.command == 'disable':
            store.disable(); result = {'status': 'disabled', 'active_tail': 'drain_requested'}
        else:
            result = store.view()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError) as exc: raise SystemExit(str(exc))

"""Finite after-Voice translation recovery for one explicit closed session; no active binding switch."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from codex_translation import CodexTranslator, MODEL
from live_companion import LiveStore, MAX_LINE, TERMINAL, find_source, now, source_identity
from workspace_config import resolve_workspace


def snapshot_voice(source, thread_id, voice_id):
    source = Path(source).expanduser().resolve()
    if source_identity(source) != thread_id:
        raise ValueError('源任务身份不一致，未恢复。')
    started = closed = None
    segments = {}; cursor = 0
    with source.open('rb') as f:
        while True:
            line = f.readline(MAX_LINE + 1)
            if len(line) > MAX_LINE:
                raise ValueError('源日志行过大，未恢复。')
            if not line or not line.endswith(b'\n'):
                break
            cursor = f.tell()
            row = json.loads(line)
            if not isinstance(row, dict) or row.get('type') != 'realtime_item':
                continue
            p = row.get('payload', {})
            if not isinstance(p, dict) or p.get('realtime_session_id') != voice_id:
                continue
            kind = p.get('type')
            if kind == 'realtime_session_started':
                started = row.get('timestamp')
            elif kind == 'realtime_session_closed':
                closed = row.get('timestamp')
            elif kind == 'transcript_segment' and p.get('role') in {'user', 'assistant'}:
                if not isinstance(p.get('id'), str) or not isinstance(p.get('text'), str) or not p['text'].strip():
                    raise ValueError('指定 Voice 有无效片段，未把恢复标记为完整。')
                if len(p['text']) > 12000:
                    raise ValueError('指定 Voice 片段过长，未自动恢复。')
                segment = {k: p[k] for k in ['id', 'role', 'text']}
                segment.update(timestamp=row.get('timestamp'), ordinal=row.get('ordinal'))
                if p['id'] in segments and any(segments[p['id']][k] != segment[k] for k in ['role','text']):
                    raise ValueError('同一片段 ID 的内容冲突，未覆盖原话。')
                segments.setdefault(p['id'], segment)
                if len(segments) > 2000:
                    raise ValueError('单次恢复超过 2000 个片段，请让 Agent 缩小已核实范围。')
    if not started or not closed or closed < started:
        raise ValueError('仅恢复有明确开始和结束的指定 Voice；未监听下一场。')
    return {'source': str(source), 'thread_id': thread_id, 'voice_id': voice_id,
            'voice_started_at': started, 'voice_closed_at': closed,
            'snapshot_at': now(), 'cursor': cursor, 'segments': list(segments.values())}


@contextmanager
def recovery_lock(store, thread_id, voice_id):
    key = hashlib.sha256((thread_id + '/' + voice_id).encode()).hexdigest()[:24]
    with (store.path.parent / ('.recover-' + key + '.lock')).open('a+b') as f:
        if f.tell() == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError('这场恢复正在运行，未启动重复翻译。') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def recover_voice(store, source, thread_id, voice_id, model=MODEL, refresh=False, factory=CodexTranslator):
    with recovery_lock(store, thread_id, voice_id):
        snapshot = snapshot_voice(source, thread_id, voice_id)
        with store.db() as db:
            matches = [json.loads(r['state']) for r in db.execute('SELECT state FROM runs')]
            matches = [r for r in matches if r['thread_id'] == thread_id and r['voice_id'] == voice_id]
            if len(matches) > 1:
                raise ValueError('同一 Voice 有多个缓存，需 Agent 核实后恢复。')
            if matches:
                state = matches[0]
                if state['status'] not in TERMINAL | {'recovering'}:
                    raise ValueError('这场实时绑定还未排空，未与它并行恢复。')
                if Path(state['source']).resolve() != Path(source).resolve():
                    raise ValueError('已有 Voice 来源路径不同，未改绑定。')
            else:
                state = {'id':str(uuid.uuid4()), 'thread_id':thread_id, 'voice_id':voice_id,
                         'source':snapshot['source'], 'created_at':now(), 'created_epoch':time.time(),
                         'demo':False, 'model':model, 'effort':'low', 'status':'recovering',
                         'ready':False, 'error':None, 'recovery_reason':'missing_binding'}
                db.execute('INSERT INTO runs VALUES (?,?,?)', (state['id'], 'stopped', json.dumps(state)))
            old = {r['id']: dict(r) for r in db.execute('SELECT * FROM segments WHERE run=?', (state['id'],))}
            wanted = {s['id']:s for s in snapshot['segments']}
            if set(old) - set(wanted):
                raise ValueError('缓存有不在本次源快照中的片段，未改原缓存。')
            for sid, row in old.items():
                if any(row[k] != wanted[sid][k] for k in ['role','text']):
                    raise ValueError('源文字与已有缓存不一致，未覆盖原话。')
            if not refresh and state.get('status') == 'ended' and set(old) == set(wanted) and all(r['status']=='translated' for r in old.values()):
                return {'status':'already_complete','run_id':state['id'],'segments':len(old),'model_batches':0}
            state.update(recovery_mode='after_voice', status='recovering', ready=False, error=None,
                         model=model, heartbeat=now(), heartbeat_epoch=time.time(),
                         **{k:snapshot[k] for k in ['voice_started_at','voice_closed_at','snapshot_at','cursor']})
            state['last_transcript_at'] = snapshot['segments'][-1]['timestamp'] if snapshot['segments'] else None
            if 'recovery_reason' not in state:
                state['recovery_reason'] = 'refresh_translation' if refresh else 'late_tail'
            store.save(state, db)
            db.execute("UPDATE runs SET desired='stopped' WHERE id=?", (state['id'],))
            for row in snapshot['segments']:
                db.execute('INSERT OR IGNORE INTO segments(run,id,role,text,timestamp,ordinal,ingested_at) VALUES (?,?,?,?,?,?,?)',
                    (state['id'],row['id'],row['role'],row['text'],row['timestamp'],row['ordinal'],now()))
            db.execute("UPDATE segments SET status='pending',attempts=0 WHERE run=? AND (status!='translated' OR ?)", (state['id'],refresh))
        client = factory(model); batches = 0
        try:
            while True:
                batch = store.batch(state['id'])
                if not batch:
                    break
                state.update(heartbeat=now(), heartbeat_epoch=time.time()); store.save(state)
                try:
                    result, latency = client.translate(batch)
                    store.translated(state['id'],result,latency)
                    batches += int(latency > 0)
                except Exception:
                    client.close()
                    if store.fail_batch(state['id'],batch):
                        raise
            state.update(status='ended', ready=False, error=None, recovery_finished_at=now())
            store.save(state)
        except Exception as exc:
            state.update(status='error',ready=False,error=str(exc) if isinstance(exc,ValueError) else '结束后恢复失败，原话已保留。')
            store.save(state)
            raise
        finally:
            client.close()
        return {'status':'recovered_after_voice','run_id':state['id'],'segments':len(snapshot['segments']),
                'model_batches':batches,'prior_binding_existed':bool(matches)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path);p.add_argument('--thread-id',required=True)
    p.add_argument('--voice-id',required=True);p.add_argument('--source',type=Path)
    p.add_argument('--model',default=MODEL);p.add_argument('--refresh-translations',action='store_true')
    args=p.parse_args();root=Path(resolve_workspace(root=args.root)['data_root'])
    if not (root/'profile.json').is_file():raise ValueError('学习档案不可用，未创建空替代。')
    result=recover_voice(LiveStore(root),args.source or find_source(args.thread_id),args.thread_id,
                         args.voice_id,args.model,args.refresh_translations)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as exc:raise SystemExit(str(exc))

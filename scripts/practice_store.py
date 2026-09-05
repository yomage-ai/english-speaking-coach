#!/usr/bin/env python3
"""Local speaking journal: canonical records, recoverable writes, derived views."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

PROJECT_ID = 'PRJ-ENGLISH-SPEAKING'
MASTERY_ZH = {'not_tested':'尚未尝试', 'source_text':'看原句说出', 'keywords':'借关键词说出', 'independent':'曾独立说出', 'transfer':'曾换场景使用'}
VALID_RESULT = {'failed', 'partial', 'success', 'transfer_success'}
VALID_PROMPT = {'source_text', 'keywords', 'none', 'changed_context'}
ID = re.compile(r'^SES-\d{8}-\d{3}$')
EXP_ID = re.compile(r'^EXP-\d{8}-\d{3}$')
MARKER = 'speaking-record-v2'
LEGACY = 'speaking-legacy-v1'

def project_dir(vault):
    return Path(vault) / 'vault' / 'Work' / 'Projects' / 'English-Speaking'

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'

def write_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def write_json(path, data):
    write_text(path, encoded(data))

@contextmanager
def writer(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.write.lock').open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)

def block(marker, value):
    # Escape markup delimiters while retaining valid JSON.
    return '<!-- ' + marker + '\n' + encoded(value).replace('<', '\\u003c').replace('>', '\\u003e') + '-->\n'

def extract(path, marker):
    text = Path(path).read_text(encoding='utf-8')
    match = re.search(r'<!-- ' + re.escape(marker) + r'\n(.*?)-->', text, re.S)
    return json.loads(match.group(1)) if match else None

def baseline():
    return {'schema_version':1, 'project_id':PROJECT_ID, 'updated':'', 'learner':{}, 'sessions':[], 'expressions':[], 'weekly_reviews':[]}

def default_profile():
    return {'schema_version':1, 'goal':'清楚、自然地表达自己的想法 / Express ideas clearly and naturally',
            'practice_language':'english_first', 'help_language':'zh-CN',
            'mode':'conversation', 'correction':'light', 'drills':'on_request',
            'review_limit':2, 'source_ids':[], 'updated':str(date.today())}

def initialize(root):
    for folder in ('Sessions', 'Weeks', 'Archive', 'Pending', 'Evidence'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    archive = root / 'Archive' / 'legacy-v1.md'
    if not archive.exists():
        old = read_json(root / 'state.json') if (root / 'state.json').exists() else baseline()
        if old.get('schema_version') != 1:
            raise ValueError('Legacy archive missing; restore it from backup before rebuilding.')
        hashes = {}
        for session in old.get('sessions', []):
            if not ID.fullmatch(session['id']):
                raise ValueError('Unsafe legacy session id')
            source = root / 'Sessions' / (session['id'] + '.md')
            if not source.is_file():
                raise ValueError('Legacy session missing: ' + session['id'])
            hashes[session['id']] = hashlib.sha256(source.read_bytes()).hexdigest()
        write_text(archive, '# 旧版学习状态原样归档\n\n保留迁移前课次、表达和尝试记录；重建旧数据时读取本档案。旧课次 Markdown 保持原样，未补造旧版缺失的尝试证据。\n\n' + block(LEGACY, {'state':old, 'session_hashes':hashes}))
    if not (root / 'profile.json').exists():
        write_json(root / 'profile.json', default_profile())

def check_date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError('Dates must use YYYY-MM-DD')

def strings(value, key):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(key + ' must be a list of nonempty strings')

def validate_payload(data, allow_in_progress=False):
    if not isinstance(data, dict):
        raise ValueError('Session must be an object')
    for key in ('id', 'date', 'title', 'summary', 'source_ids', 'expressions'):
        if key not in data:
            raise ValueError('Missing session field: ' + key)
    if not isinstance(data['id'], str) or not ID.fullmatch(data['id']):
        raise ValueError('Session id must be SES-YYYYMMDD-NNN')
    check_date(data['date'])
    record_frontmatter(data)
    if data['id'][4:12] != data['date'].replace('-', ''):
        raise ValueError('Session id date differs from practice date')
    for key in ('title', 'summary'):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(key + ' must be nonempty text')
    strings(data['source_ids'], 'source_ids')
    if not data['source_ids']:
        raise ValueError('Actual source_ids required')
    for key in ('topics', 'scenarios', 'progress', 'next_focus', 'unfinished'):
        strings(data.get(key, []), key)
    if len(data.get('next_focus', [])) > 2:
        raise ValueError('At most two next focuses')
    if data.get('end_status', 'ended') not in ({'ended', 'in_progress'} if allow_in_progress else {'ended'}):
        raise ValueError('Only ended sessions can be committed')
    if data.get('evidence_status', 'selected') not in {'selected', 'partial'}:
        raise ValueError('Invalid evidence_status')
    if data.get('recovered_on'):
        check_date(data['recovered_on'])
    if not isinstance(data['expressions'], list):
        raise ValueError('expressions must be a list; [] is allowed')
    from learning_progress import validate_observations
    validate_observations(data.get('concept_observations', []))
    seen = set()
    for item in data['expressions']:
        for key in ('id', 'english', 'chinese', 'mastery', 'next_review', 'note'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError('Expression missing text: ' + key)
        if not EXP_ID.fullmatch(item['id']) or item['id'] in seen:
            raise ValueError('Invalid or duplicate expression id')
        seen.add(item['id'])
        check_date(item['next_review'])
        if item['mastery'] not in MASTERY_ZH:
            raise ValueError('Invalid mastery')
        if item.get('original') is not None and not isinstance(item['original'], str):
            raise ValueError('original must be text')
        strings(item.get('issue_tags', []), 'issue_tags')
        result, prompt = item.get('review_result'), item.get('review_prompt')
        if result or prompt:
            if result not in VALID_RESULT or prompt not in VALID_PROMPT or not item.get('original'):
                raise ValueError('An attempt requires original wording, result, prompt and note')
        if item['mastery'] in {'independent', 'transfer'}:
            expected = ('success', 'none') if item['mastery'] == 'independent' else ('transfer_success', 'changed_context')
            if (result, prompt) != expected:
                raise ValueError('Independent/transfer state requires a matching observed attempt')
        if item['mastery'] == 'not_tested' and (result or prompt):
            raise ValueError('An untested collection cannot contain a scored attempt')

def record_frontmatter(data):
    """Knowledge-base metadata is explicit input, not a global governance scheme."""
    meta={'id':data['id'],'type':'english-practice','sensitivity':'private','created':data['date'],'source_ids':data['source_ids']}
    extra=data.get('record_metadata',{})
    if not isinstance(extra,dict) or set(extra)-{'type','status','primary_project','related_projects','domains','sensitivity'}:
        raise ValueError('Unsupported record_metadata fields')
    for value in extra.values():
        if not isinstance(value,str) and not (isinstance(value,list) and all(isinstance(v,str) for v in value)):
            raise ValueError('Metadata values must be text or lists of text')
    meta.update(extra)
    return '---\n'+''.join(k+': '+json.dumps(v,ensure_ascii=False)+'\n' for k,v in meta.items())+'---\n\n'

def session_markdown(data):
    def bullets(key):
        return '\n'.join('- ' + x for x in data.get(key, [])) or '未另行记录。'
    text = record_frontmatter(data)
    text += '# ' + data['title'] + '\n\n' + data['date'] + ' · ' + ' / '.join(data.get('scenarios', [])) + '\n\n' + data['summary'] + '\n\n'
    for item in data['expressions']:
        text += '## ' + item['english'] + '\n\n' + item['chinese'] + '\n\n'
        text += '**我当时说：** ' + (item.get('original') or '未保留原话；仅收集表达，尚未测试。') + '\n\n'
        text += '**这次观察：** ' + item['note'] + '\n\n**提示情况：** ' + MASTERY_ZH[item['mastery']] + '；建议复习 ' + item['next_review'] + '\n\n'
    if not data['expressions']:
        text += '本次未新增表达，仍保留练习经过与下次入口。\n\n'
    if data.get('concept_observations'):
        from learning_progress import DIMENSIONS, RESULTS, SUPPORTS
        text += '## 知识点的变化\n\n'
        for o in data['concept_observations']:
            text += '### ' + o['term'] + ' · ' + DIMENSIONS[o['dimension']] + '\n\n' + o['meaning'] + '\n\n'
            text += RESULTS[o['result']] + '；' + SUPPORTS[o['support']] + '。\n\n来源选段：' + o['quote'] + '\n\n' + o['note'] + '\n\n'
    text += '## 本次观察\n\n' + bullets('progress') + '\n\n## 下次接着聊\n\n' + bullets('next_focus') + '\n\n## 尚未聊完\n\n' + bullets('unfinished')
    text += '\n\n## 来源与证据边界\n\n' + '\n'.join('- ' + x for x in data['source_ids']) + '\n\n'
    text += data.get('evidence_note', '只保留学习所需的精选转写，不代表完整对话；文字不能证明发音准确。') + '\n\n'
    if data.get('recovered_on'):
        text += '补录日期：' + data['recovered_on'] + '；掌握状态仅按当时可见证据记录。\n\n'
    text += block(MARKER, data) + '\n## 我的补充\n\n可在这里自由补充学习笔记；Agent 重建页面时保留本文件。\n'
    return text

def build_state(root):
    archive = extract(root / 'Archive' / 'legacy-v1.md', LEGACY)
    if not archive or not isinstance(archive.get('state'), dict):
        raise ValueError('Legacy archive invalid')
    state = deepcopy(archive['state'])
    state['schema_version'] = 2
    state.setdefault('sessions', []); state.setdefault('expressions', []); state.setdefault('weekly_reviews', [])
    legacy_ids = {s['id'] for s in state['sessions']}
    records = []
    for path in sorted((root / 'Sessions').glob('*.md')):
        if path.stem in legacy_ids:
            continue
        record = extract(path, MARKER)
        if record is None:
            raise ValueError('Unindexed session needs explicit migration: ' + path.name)
        validate_payload(record)
        if record['id'] != path.stem:
            raise ValueError('Session file/id mismatch')
        records.append(record)
    for sid in legacy_ids:
        if not (root / 'Sessions' / (sid + '.md')).is_file():
            raise ValueError('Legacy source missing: ' + sid)
    expressions = {e['id']:e for e in state['expressions']}
    for record in sorted(records, key=lambda r:(r['date'], r['id'])):
        summary = {k:deepcopy(v) for k,v in record.items() if k != 'expressions'}
        summary['expression_ids'] = [e['id'] for e in record['expressions']]
        state['sessions'].append(summary)
        for item in record['expressions']:
            prior = expressions.get(item['id'], {})
            attempts = deepcopy(prior.get('attempts', []))
            if item.get('review_result'):
                attempts.append({'date':record['date'], 'session':record['id'], 'result':item['review_result'], 'prompt':item['review_prompt'], 'original':item['original'], 'note':item['note']})
            # Older imports add evidence without regressing a newer observation.
            newer = prior.get('updated', '') > record['date']
            merged = deepcopy(prior if newer else item)
            merged['source_session'] = prior.get('source_session', record['id'])
            merged['seen_in_sessions'] = sorted(set(prior.get('seen_in_sessions', []) + [record['id']]))
            merged['attempts'] = sorted(attempts, key=lambda a:(a['date'], a['session']))
            merged['updated'] = max(prior.get('updated', ''), record['date'])
            expressions[item['id']] = merged
    state['sessions'].sort(key=lambda s:(s['date'], s['id']))
    state['expressions'] = sorted(expressions.values(), key=lambda e:e['id'])
    state['updated'] = max([s['date'] for s in state['sessions']] + [state.get('updated', '')])
    state['profile'] = read_json(root / 'profile.json')
    validate_profile(state['profile'])
    state['learner'] = {**state.get('learner', {}), 'goal':state['profile']['goal'], 'current_focus':state['sessions'][-1].get('next_focus', []) if state['sessions'] else [], 'practice_style':[state['profile']['mode'], state['profile']['correction'], state['profile']['drills']]}
    state['review_strategy'] = {'name':'contextual-retrieval-v2', 'max_due_per_session':state['profile']['review_limit'], 'default_intervals_days':{'not_tested':1, 'source_text':1, 'keywords':3, 'independent':7, 'transfer':14}}
    from learning_progress import collect_progress
    state['concepts'] = collect_progress(root, state)
    return state

def rebuild(root):
    from practice_view import render
    state = build_state(root)
    write_json(root / 'state.json', state)
    write_text(root / 'dashboard.html', render(state, root))
    lines = ['# 英语学习手记', '', '精选表达、练习经过与下次入口。', '', '[本地阅读页](dashboard.html)', '']
    for session in reversed(state['sessions']):
        lines += ['- [' + session['date'] + ' · ' + session['title'] + '](Sessions/' + session['id'] + '.md)']
    write_text(root / 'INDEX.md', '\n'.join(lines) + '\n')
    return state

def commit(root, data):
    validate_payload(data)
    destination = root / 'Sessions' / (data['id'] + '.md')
    pending = root / 'Pending' / (data['id'] + '.json')
    if destination.exists():
        if extract(destination, MARKER) != data:
            raise ValueError('Conflicting session id; existing record preserved: ' + data['id'])
        status = 'already_saved'
    else:
        if data.get('concept_observations'):
            from learning_progress import collect_progress
            prospective = build_state(root)
            prospective['sessions'].append({k:deepcopy(v) for k,v in data.items() if k!='expressions'})
            known = {e['id'] for e in prospective['expressions']}
            prospective['expressions'] += [deepcopy(e) for e in data['expressions'] if e['id'] not in known]
            collect_progress(root, prospective)
        if pending.exists():
            staged = read_json(pending)
            if staged.get('end_status', 'ended') == 'ended' and staged != data:
                raise ValueError('Conflicting ended checkpoint; recover or inspect it first')
        write_json(pending, data)
        write_text(destination, session_markdown(data))
        status = 'saved'
    rebuild(root)
    if pending.exists() and read_json(pending) == data:
        pending.unlink()
    return {'status':status, 'session':data['id']}

def validate_profile(profile):
    if not isinstance(profile.get('goal'), str) or not profile['goal'].strip():
        raise ValueError('goal must be nonempty')
    allowed = {'practice_language':{'english_first', 'bilingual'}, 'help_language':{'zh-CN', 'en'}, 'mode':{'conversation', 'roleplay', 'focused'}, 'correction':{'light', 'detailed'}, 'drills':{'on_request', 'guided'}}
    for key, choices in allowed.items():
        if profile.get(key) not in choices:
            raise ValueError('Invalid preference: ' + key)
    if type(profile.get('review_limit')) is not int or not 0 <= profile['review_limit'] <= 5:
        raise ValueError('review_limit must be 0–5')
    strings(profile.get('source_ids'), 'source_ids')
    check_date(profile['updated'])

def resume(root, today):
    from live_companion import companion_preferences
    companion = companion_preferences(root)
    state = build_state(root)
    latest = state['sessions'][-1] if state['sessions'] else None
    due = sorted([e for e in state['expressions'] if e['next_review'] <= today], key=lambda e:(e['next_review'], e['id']))
    profile = state['profile']
    if companion['enabled'] and profile['practice_language'] == 'english_first':
        brief = 'Speak simple English in Voice. Put Chinese help on the companion page; do not read it aloud unless the learner explicitly asks for spoken Chinese. '
    else:
        brief = ('Use simple English first. ' if profile['practice_language'] == 'english_first' else 'Use bilingual scaffolding at the learner’s pace. ')
        brief += 'Help language: ' + profile['help_language'] + '. '
    brief += 'Respond to meaning and continue with a natural follow-up. '
    brief += ('Give at most one short recast per turn. ' if profile['correction'] == 'light' else 'Give the requested detailed feedback without losing the conversation. ')
    brief += ('No compulsory repetition. ' if profile['drills'] == 'on_request' else 'Use guided practice where useful. ')
    brief += 'Do not repeatedly ask whether to continue. '
    brief += 'Goal: ' + profile['goal'] + '. Mode: ' + profile['mode'] + '; corrections: ' + profile['correction'] + '; drills: ' + profile['drills'] + '. '
    brief += 'Continue from: ' + (' / '.join(latest.get('next_focus', [])) if latest else 'a simple daily-life question') + '. Save selected evidence when an actual end signal is observed; never invent a host hook.'
    concepts = [{'id':c['id'],'term':c['term'],'meaning':c['meaning'],'level':c['level_label'],'next_step':c['next_step'],'last_observation':c['events'][-1]} for c in state.get('concepts',[]) if c['level']!='stable' or c['needs_revisit']][:profile['review_limit']]
    brief += ' Preserve stable concept IDs. If later speech shows changed understanding, reading or unprompted use, record the actual evidence separately; reading aloud is not proof of independent use.'
    if companion['enabled']:
        brief += ' Bilingual companion is enabled: the tool-enabled Agent must bind EACH new Voice in this task and verify its local #live page. An ended binding does not follow the next Voice. Do not forward each sentence through tools. Do not claim the voice host received this brief or live subtitles without observation.'
    return {'profile':profile, 'latest_session':latest, 'due_candidates':due[:profile['review_limit']], 'concept_review_candidates':concepts, 'pending':[p.name for p in sorted((root / 'Pending').glob('*.json'))], 'voice_brief':brief, 'companion':companion}

def validate(root):
    rebuilt = build_state(root)
    problems = []
    if not (root / 'state.json').exists() or read_json(root / 'state.json') != rebuilt:
        problems.append('state.json missing or stale; run rebuild')
    if not (root / 'dashboard.html').is_file():
        problems.append('dashboard.html missing; run rebuild')
    legacy = extract(root / 'Archive' / 'legacy-v1.md', LEGACY)
    changed = [sid for sid,digest in legacy['session_hashes'].items() if hashlib.sha256((root / 'Sessions' / (sid+'.md')).read_bytes()).hexdigest() != digest]
    return {'ok':not problems, 'problems':problems, 'sessions':len(rebuilt['sessions']), 'expressions':len(rebuilt['expressions']), 'legacy_notes_changed':changed, 'pending':[p.name for p in sorted((root / 'Pending').glob('*.json'))]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    locations=parser.add_mutually_exclusive_group()
    locations.add_argument('--vault', type=Path)
    locations.add_argument('--root', type=Path)
    parser.add_argument('command', choices=['init', 'migrate', 'add-session', 'add-evidence', 'paths', 'checkpoint', 'recover', 'rebuild', 'render', 'resume', 'validate', 'set-preferences', 'export'])
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--today', default=str(date.today()))
    args = parser.parse_args()
    from workspace_config import resolve_workspace, CONFIG_PATH
    workspace=resolve_workspace(root=args.root, vault=args.vault)
    root = Path(workspace['data_root'])
    if args.command=='paths':
        print(encoded(workspace),end='');return 0
    check_date(args.today)
    if args.command in {'resume', 'validate'}:
        result = resume(root, args.today) if args.command == 'resume' else validate(root)
        print(encoded({**result,'workspace':workspace}), end='')
        return 1 if result.get('ok') is False else 0
    with writer(root):
        initialize(root)
        if args.command in {'init', 'migrate', 'rebuild', 'render'}:
            rebuild(root); result = validate(root)
            if args.command=='init' and args.root is None and args.vault is None:
                write_json(CONFIG_PATH,{'schema_version':1,'data_root':str(root),'project_page':workspace.get('project_page')})
        elif args.command == 'add-session':
            if args.input is None: raise ValueError('--input required')
            result = commit(root, read_json(args.input))
            result['archive_route']='#sessions/'+result['session']
        elif args.command == 'add-evidence':
            if args.input is None:raise ValueError('--input required')
            from learning_progress import save_evidence
            result=save_evidence(root,read_json(args.input));rebuild(root)
        elif args.command == 'checkpoint':
            if args.input is None: raise ValueError('--input required')
            data = read_json(args.input); validate_payload(data, allow_in_progress=True)
            if (root / 'Sessions' / (data['id'] + '.md')).exists():
                raise ValueError('Session already committed')
            pending = root / 'Pending' / (data['id'] + '.json')
            if pending.exists() and read_json(pending).get('end_status', 'ended') == 'ended':
                raise ValueError('Ended checkpoint cannot be replaced; recover it')
            write_json(pending, data); result = {'status':'checkpointed', 'session':data['id']}
        elif args.command == 'recover':
            results = []
            for pending in sorted((root / 'Pending').glob('*.json')):
                data = read_json(pending); validate_payload(data, allow_in_progress=True)
                if pending.stem != data['id']: raise ValueError('Pending filename/id mismatch')
                results.append(commit(root, data) if data.get('end_status', 'ended') == 'ended' else {'status':'needs_session_context', 'session':data['id']})
            rebuild(root); result = {'recovered':results}
        elif args.command == 'set-preferences':
            if args.input is None: raise ValueError('--input required')
            changes = read_json(args.input)
            if not changes.get('source_ids'): raise ValueError('Preference change requires user decision source_ids')
            prior = read_json(root / 'profile.json')
            if set(changes) - set(prior): raise ValueError('Unknown preference fields')
            profile = {**prior, **changes}; validate_profile(profile)
            write_json(root / 'profile.json', profile); rebuild(root); result = {'status':'preferences_saved'}
        else:
            if args.output is None: raise ValueError('--output required')
            state = build_state(root)
            from practice_view import render
            output = args.output.resolve()
            if output == root.resolve() or root.resolve() in output.parents:
                raise ValueError('Export destination must be outside the canonical learning directory')
            write_text(output / 'dashboard.html', render(state, root, snapshot=True))
            for s in state['sessions']:
                write_text(output / 'Sessions' / (s['id']+'.md'), (root / 'Sessions' / (s['id']+'.md')).read_text(encoding='utf-8'))
            result = {'status':'exported', 'path':str(output / 'dashboard.html')}
        from workspace_config import backup_embedded_data
        backup=backup_embedded_data(root)
        if backup:result['recovery_backup']=backup
        print(encoded(result), end='')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, TypeError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(1)

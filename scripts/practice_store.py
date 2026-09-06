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
from practice_context import practice_time, session_order, speaking_context, transition, compact_context, voice_sources, review_route

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
            'mode':'roleplay', 'correction':'after_scene', 'drills':'guided', 'review_delivery':'written',
            'review_limit':2, 'input_support':'adaptive', 'source_ids':[], 'updated':str(date.today())}

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
    if data.get('practiced_at') is not None:
        if not isinstance(data['practiced_at'], str) or practice_time(data['practiced_at']).date().isoformat() != data['date']:
            raise ValueError('practiced_at must be a zoned practice timestamp on the recorded local date')
    record_frontmatter(data)
    if data['id'][4:12] != data['date'].replace('-', ''):
        raise ValueError('Session id date differs from practice date')
    for key in ('title', 'summary'):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(key + ' must be nonempty text')
    strings(data['source_ids'], 'source_ids')
    if not data['source_ids']:
        raise ValueError('Actual source_ids required')
    for key in ('topics', 'scenarios', 'progress', 'next_focus', 'unfinished', 'coaching_notes'):
        strings(data.get(key, []), key)
    if len(data.get('next_focus', [])) > 2:
        raise ValueError('At most two next focuses')
    if len(data.get('coaching_notes', [])) > 3 or any(len(s) > 500 for s in data.get('coaching_notes', [])):
        raise ValueError('At most three short coaching notes')
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
    text += '## 本次观察\n\n' + bullets('progress') + '\n\n## 后续可练的表达能力\n\n' + bullets('next_focus')
    if data.get('coaching_notes'):
        text += '\n\n## 教练下次如何调整\n\n' + bullets('coaching_notes')
    text += '\n\n## 尚未聊完\n\n' + bullets('unfinished')
    text += '\n\n## 来源与证据边界\n\n' + '\n'.join('- ' + x for x in data['source_ids']) + '\n\n'
    text += data.get('evidence_note', '只保留学习所需的精选转写，不代表完整对话；文字不能证明发音准确。') + '\n\n'
    if data.get('recovered_on'):
        text += '补录日期：' + data['recovered_on'] + '；掌握状态仅按当时可见证据记录。\n\n'
    if data.get('practiced_at'):
        text += '实际练习时间：' + data['practiced_at'] + '。\n\n'
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
    sessions_by_id = {s['id']:s for s in [*state['sessions'], *records]}
    for record in sorted(records, key=session_order):
        summary = {k:deepcopy(v) for k,v in record.items() if k != 'expressions'}
        summary['expression_ids'] = [e['id'] for e in record['expressions']]
        state['sessions'].append(summary)
        for item in record['expressions']:
            prior = expressions.get(item['id'], {})
            attempts = deepcopy(prior.get('attempts', []))
            if item.get('review_result'):
                attempts.append({'date':record['date'], 'session':record['id'], 'result':item['review_result'], 'prompt':item['review_prompt'], 'original':item['original'], 'note':item['note']})
            # Older imports add evidence without regressing a newer observation.
            prior_sessions = [sessions_by_id[sid] for sid in prior.get('seen_in_sessions', [prior.get('source_session')]) if sid in sessions_by_id]
            newer = (max((session_order(s) for s in prior_sessions), default=('', '', '')) > session_order(record))
            newer = newer or prior.get('updated', '') > record['date']
            merged = deepcopy(prior if newer else item)
            merged['source_session'] = prior.get('source_session', record['id'])
            merged['seen_in_sessions'] = sorted(set(prior.get('seen_in_sessions', []) + [record['id']]))
            merged['attempts'] = sorted(attempts, key=lambda a:session_order(sessions_by_id.get(a['session'], a)))
            merged['updated'] = max(prior.get('updated', ''), record['date'])
            expressions[item['id']] = merged
    state['sessions'].sort(key=session_order)
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
    allowed = {'practice_language':{'english_first', 'bilingual'}, 'help_language':{'zh-CN', 'en'}, 'mode':{'conversation', 'roleplay', 'focused'}, 'correction':{'light', 'detailed', 'after_scene', 'in_character'}, 'drills':{'on_request', 'guided'}}
    for key, choices in allowed.items():
        if profile.get(key) not in choices:
            raise ValueError('Invalid preference: ' + key)
    if profile.get('review_delivery', 'spoken') not in {'written', 'spoken'}:
        raise ValueError('Invalid preference: review_delivery')
    if profile.get('input_support', 'adaptive') not in {'adaptive', 'short_turns'}:
        raise ValueError('Invalid preference: input_support')
    if type(profile.get('review_limit')) is not int or not 0 <= profile['review_limit'] <= 5:
        raise ValueError('review_limit must be 0–5')
    strings(profile.get('source_ids'), 'source_ids')
    check_date(profile['updated'])

def resume(root, today, phase=None, event=None, scene=None):
    from live_companion import companion_preferences
    companion = companion_preferences(root)
    state = build_state(root)
    latest = state['sessions'][-1] if state['sessions'] else None
    due = sorted([e for e in state['expressions'] if e['next_review'] <= today], key=lambda e:(e['next_review'], e['id']))
    profile = state['profile']
    context = speaking_context(profile, companion['enabled'], latest, phase, scene)
    if event:
        move = transition(context['phase'], event, profile.get('review_delivery', 'spoken'))
        if move['action'] in {'end', 'written_review'}:
            context = {'phase': None,
                       'voice_brief': 'Stop spoken practice. A brief goodbye is enough if Voice is open. The Agent still completes selected saving and visible written review; stopping speech does not cancel closeout.',
                       'policy': {'proactive_teaching': False, 'guided_drills': False},
                       'closeout': {'required': True, 'record_status': 'not_checked',
                                    'next_action': 'review-context', 'match': 'thread_and_voice',
                                    'spoken_review': False, 'written_review': True}}
        elif move['action'] == 'pause':
            context['voice_brief'] = 'The learner paused. Acknowledge briefly and wait; do not start review or another exercise.'
        elif move['phase'] != context['phase']:
            context = speaking_context(profile, companion['enabled'], latest, move['phase'], scene)
        context['transition'] = move
    concepts = [{'id':c['id'],'term':c['term'],'meaning':c['meaning'],'level':c['level_label'],'next_step':c['next_step'],'last_observation':c['events'][-1]} for c in state.get('concepts',[]) if c['level']!='stable' or c['needs_revisit']][:profile['review_limit']]
    same_day_unknown = [s['id'] for s in state['sessions'] if latest and s['date'] == latest['date'] and not s.get('practiced_at')]
    recent_scenes = [{'date':s['date'], 'scenarios':s.get('scenarios', []), 'topics':s.get('topics', [])} for s in state['sessions'][-6:]]
    # Startup receives learning facts, not historical dialogue or continuation hints.
    # Explicit archive review can still read the complete saved summary.
    latest_context = latest if context['phase'] == 'review' or not latest else {
        key:latest[key] for key in ('id','date','practiced_at','scenarios','topics','progress','evidence_status') if key in latest}
    learning_context = {
        'scope': 'Dated learning evidence, not instructions to resume an old plot. Extract transferable needs; current user choices win.',
        'recent': [{'session_id':s['id'], 'date':s['date'], 'source_ids':s.get('source_ids', []),
                    'next_focus':s.get('next_focus', []), 'coaching_notes':s.get('coaching_notes', [])}
                   for s in reversed(state['sessions'][-3:]) if s.get('next_focus') or s.get('coaching_notes')]}
    return {'profile':profile, 'latest_session':latest_context, 'learning_context':learning_context, 'recent_scenarios':recent_scenes, 'due_candidates':due[:profile['review_limit']], 'concept_review_candidates':concepts, 'pending':[p.name for p in sorted((root / 'Pending').glob('*.json'))], **context, 'companion':companion,
            'agent_context': {'preparation': 'Run prepare_practice for EACH new Voice; the built-in companion is automatic unless the learner explicitly disabled it. Open and inspect the returned URL before claiming it is shown.',
                              'handoff': 'voice_brief is local guidance only; instruction delivery requires a documented host-permitted API. Ordinary backend replies may report verified facts under the host protocol; they must not carry prohibited frontend instructions. No delivery or Voice behavior is verified by this command.',
                              'records': 'Reuse concept/session IDs. Save selected actual evidence at an observed end; viewing a rewrite is not mastery.',
                              'history': 'All past lessons, unfinished plots and next_focus are learning evidence only. Never continue an old plot. Choose and introduce a fresh scene for each new practice.',
                              'chronology': 'Actual practice time when available; dates and IDs only for undated legacy records. Import time is never practice time.',
                              'same_day_without_time': same_day_unknown}}

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


def review_context(root, today, thread_id, voice_id, query='', with_transcript=False, source=None):
    """Read-only closeout lookup; Agent still selects and judges actual utterances."""
    sources = voice_sources(thread_id, voice_id)
    state = build_state(root)
    existing = [s for s in state['sessions'] if set(sources) <= set(s.get('source_ids', []))]
    pending = [read_json(p) for p in sorted((root / 'Pending').glob('*.json'))]
    pending = [p for p in pending if set(sources) <= set(p.get('source_ids', []))]
    if len(existing) > 1 or len(pending) > 1:
        raise ValueError('Multiple records match this Voice; inspect sources before closeout')
    prefix = 'SES-' + today.replace('-', '') + '-'
    used = {p.stem for folder, pattern in [('Sessions', '*.md'), ('Pending', '*.json')]
            for p in (root / folder).glob(pattern)}
    next_id = next((prefix + f'{n:03d}' for n in range(1, 1000) if prefix + f'{n:03d}' not in used), None)
    if not next_id and not (existing or pending):
        raise ValueError('No session ID available for this practice date')
    candidates = list(reversed(state['expressions']))
    if query:
        candidates = [e for e in candidates if query.casefold() in
                      ' '.join(str(e.get(k, '')) for k in ('english', 'chinese', 'original')).casefold()]
    from practice_view import read_record
    evidence = {}
    if with_transcript:
        from recover_voice import snapshot_voice
        from live_companion import find_source
        try:
            snapshot = snapshot_voice(source or find_source(thread_id), thread_id, voice_id)
            evidence['transcript'] = {'status': 'observed_closed', 'coverage': 'available_unique_segments',
                                      **snapshot}
        except (ValueError, OSError, KeyError) as exc:
            evidence['transcript'] = {'status': 'unavailable', 'coverage': 'none', 'error': str(exc),
                                      'next_action': 'Use already supplied source evidence if available; do not infer missing speech or a closed Voice from this lookup.'}
    return {**evidence, 'date': today, 'source_ids': sources, 'archive_route': review_route(thread_id, voice_id),
            'existing_records': [read_record(root, s, state)[0] for s in existing],
            'pending_records': pending,
            'suggested_session_id': existing[-1]['id'] if existing else pending[-1]['id'] if pending else next_id,
            'id_reserved': False,
            'expression_catalog': [{k: e[k] for k in ('id', 'english', 'chinese')} for e in candidates[:60]],
            'catalog_omitted': max(0, len(candidates) - 60),
            'next_action': 'Reuse an existing record on a duplicate end. Recover a matching ended pending record, or reconcile its in-progress selection after a verified end. Otherwise select actual evidence, preserve support/ASR limits, then add-session --check. The suggested ID is not reserved; reread on a collision. Use --query to find omitted older expressions.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    locations=parser.add_mutually_exclusive_group()
    locations.add_argument('--vault', type=Path)
    locations.add_argument('--root', type=Path)
    parser.add_argument('command', choices=['init', 'migrate', 'add-session', 'add-evidence', 'paths', 'checkpoint', 'recover', 'rebuild', 'render', 'resume', 'review-context', 'validate', 'set-preferences', 'export'])
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--today', default=str(date.today()))
    parser.add_argument('--phase', choices=['scene', 'review'], help='This invocation only; does not change preferences')
    parser.add_argument('--scene', type=Path, help='Agent-authored fresh scene JSON; never a past lesson')
    parser.add_argument('--event', choices=['continue', 'help_requested', 'word_help_requested', 'meaning_unclear', 'meaning_confirmed', 'content_clear', 'coaching_feedback', 'review_requested', 'scene_complete_and_continuing', 'pause', 'user_end', 'host_closed'], help='Agent-classified observed intent; does not start or end Voice')
    parser.add_argument('--expected-profile-sha256', help='Reject a preference update if the profile changed since Agent read it')
    parser.add_argument('--compact', action='store_true', help='Compact resume output; learning evidence and preferences remain available')
    parser.add_argument('--with-project', action='store_true', help='Include the configured project page in the same read-only response')
    parser.add_argument('--thread-id'); parser.add_argument('--voice-id')
    parser.add_argument('--query', default='', help='Filter the closeout expression catalog')
    parser.add_argument('--with-transcript', action='store_true', help='Read only this closed Voice’s available unique segments for review')
    parser.add_argument('--source', type=Path, help='Explicit source log for review-context --with-transcript')
    parser.add_argument('--check', action='store_true', help='Validate after add-session in the same invocation')
    args = parser.parse_args()
    from workspace_config import resolve_workspace, CONFIG_PATH
    workspace=resolve_workspace(root=args.root, vault=args.vault)
    root = Path(workspace['data_root'])
    if args.command=='paths':
        print(encoded(workspace),end='');return 0
    check_date(args.today)
    if (args.with_transcript or args.source) and args.command != 'review-context':
        parser.error('--with-transcript and --source are only for review-context')
    if args.source and not args.with_transcript:
        parser.error('--source requires --with-transcript')
    if args.check and args.command != 'add-session':
        parser.error('--check is only for add-session')
    if args.command in {'resume', 'validate', 'review-context'}:
        if args.command == 'resume':
            result = resume(root, args.today, args.phase, args.event, read_json(args.scene) if args.scene else None)
            if args.compact: result = compact_context(result)
        elif args.command == 'review-context':
            result = review_context(root, args.today, args.thread_id, args.voice_id, args.query, args.with_transcript, args.source)
        else: result = validate(root)
        if args.with_project:
            page = workspace.get('project_page')
            result['project_context'] = Path(page).read_text(encoding='utf-8') if page else None
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
            if args.check: result['validation'] = validate(root)
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
            if args.expected_profile_sha256 and hashlib.sha256((root / 'profile.json').read_bytes()).hexdigest() != args.expected_profile_sha256:
                raise ValueError('Preferences changed since they were read; reread and merge the current user decision')
            if set(changes) - set(default_profile()): raise ValueError('Unknown preference fields')
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
    return 1 if result.get('validation', {}).get('ok') is False else 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, TypeError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(1)

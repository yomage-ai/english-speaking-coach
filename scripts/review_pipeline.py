"""Exact-Voice closeout: Agent selects language evidence; code owns bookkeeping."""
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib

CONTRACT = {
    'command': 'finish-review --thread-id <actual> --voice-id <actual> --input <draft.json>',
    'required': ['title', 'summary', 'expressions', 'omitted_turns'],
    'expression': {'source_turn_ids': ['learner segment ID'], 'original': 'exact selected learner wording',
                   'english': 'usable English', 'chinese': 'meaning', 'note': 'help actually given, or a review-only suggestion'},
    'reading_guide_optional': {
        'when': 'For explicit reading help or a difficult priority phrase; omit for familiar short replies. Include in the normal draft with no extra per-phrase model call.',
        'expression_field': 'reading_guide',
        'shape': {'kind':'suggestion',
                  'groups':[{'text':'meaning group; all original words in order','stress':['up to three words in this group']}],
                  'tone':'rise | fall | level | fall-rise | context',
                  'tone_note':'one possible contextual reading, in the review language',
                  'memory':[{'text':'reusable starter or phrase','meaning':'what this part expresses'}]},
        'limits': 'Only the five shape fields go in reading_guide. 1–6 groups, 1–4 memory parts. Group by meaning, not word count; memory parts are not mandatory pauses. Short phrases need no internal break. This is advice, not measured audio or mastery.'},
    'existing_expression': 'Use expression_ref from the catalog and omit english/chinese; keep original, note and source_turn_ids.',
    'concept_observation': {'source_turn_ids': ['learner segment ID'], 'concept_id': 'existing catalog ID; omit term/meaning',
                            'dimension': 'meaning | use', 'result': 'needs_help | explained | supported | success',
                            'support': 'none | keywords | model', 'quote': 'exact selected wording', 'note': 'actual help and limits'},
    'new_concept': 'Omit concept_id and give term + meaning. Code assigns the ID. Optional expression_indices link to this draft’s zero-based expressions.',
    'optional': ['topics', 'scenarios', 'progress', 'next_focus (up to 2)', 'coaching_notes (up to 3)', 'priority_indices (up to 3)'],
    'coverage': 'Review EVERY available learner turn. Link valuable, deduplicated needs via source_turn_ids; for each remaining turn add omitted_turns: {segment_id: short reason}. Include useful English structure errors as well as explicit/Chinese help. Greetings, correct replies, self-repairs and coaching feedback need not become cards. Do not save the full transcript.',
    'support': 'Defaults are untested, without a scored attempt. Only set mastery/review_result/review_prompt when supported by actual evidence. New advice in this review was not taught during Voice.',
    'expression_evidence': {'mastery': ['not_tested','source_text','keywords','independent','transfer'],
                            'review_result': ['failed','partial','success','transfer_success'],
                            'review_prompt': ['source_text','keywords','none','changed_context'],
                            'rules': 'An attempt supplies both result and prompt. Independent requires success/none; transfer requires transfer_success/changed_context. not_tested has neither. source_text and keywords describe actual supplied help, not the new advice in this review.'},
    'automatic': 'Exact source identity, practice date, session/expression/observation IDs, canonical concept text, default review date, validation and duplicate recovery. No source-code or schema search is needed for normal closeout.',
}


def canonical_key(english, chinese):
    return english.strip().casefold(), chinese.strip()


def coalesce_expressions(draft):
    """One canonical phrase can include an initial need and a later supported attempt."""
    result=deepcopy(draft);items=[];keys={};remap={}
    for index,raw in enumerate(result['expressions']):
        if raw.get('expression_ref'):
            key=('ref',raw['expression_ref'])
        elif all(isinstance(raw.get(k),str) and raw[k].strip() for k in ('english','chinese')):
            key=canonical_key(raw['english'],raw['chinese'])
        else:
            # Partial/malformed drafts still belong to the normal validator.
            key=('unresolved',index)
        if key not in keys:
            keys[key]=len(items);remap[index]=len(items);items.append(raw);continue
        target=keys[key];remap[index]=target;old=items[target]
        quotes=[]
        for item in (old,raw):
            quotes.extend(item.get('source_quotes') or [{'quote':item['original'],'source_turn_ids':item['source_turn_ids']}])
        # Preserve an actual scored attempt verbatim; never manufacture a stronger score.
        chosen=deepcopy(raw if raw.get('review_result') and not old.get('review_result') else old)
        chosen['source_turn_ids']=list(dict.fromkeys(old['source_turn_ids']+raw['source_turn_ids']))
        chosen['source_quotes']=list({(q['quote'],tuple(q['source_turn_ids'])):q for q in quotes}.values())
        if not chosen.get('reading_guide'):
            guide=old.get('reading_guide') or raw.get('reading_guide')
            if guide:chosen['reading_guide']=guide
        items[target]=chosen
    result['expressions']=items
    if 'priority_indices' in result:
        result['priority_indices']=list(dict.fromkeys(remap.get(i,i) for i in result['priority_indices']))
    result['reading_omissions']={str(remap.get(int(i),int(i))):v for i,v in result.get('reading_omissions',{}).items()}
    for item in result.get('concept_observations',[]):
        if 'expression_indices' in item:item['expression_indices']=list(dict.fromkeys(remap.get(i,i) for i in item['expression_indices']))
    return result


def next_id(prefix, used):
    value = next((prefix + f'{i:03d}' for i in range(1, 1000) if prefix + f'{i:03d}' not in used), None)
    if value is None:
        raise ValueError('No available ID for ' + prefix)
    used.add(value)
    return value


def normalize_review(root, draft, thread_id, voice_id, snapshot, state):
    """Call under the canonical writer lock. Never infer linguistic correctness."""
    from practice_store import validate_payload
    from practice_context import voice_sources
    if (snapshot['thread_id'], snapshot['voice_id']) != (thread_id, voice_id):
        raise ValueError('Review snapshot belongs to a different Voice')
    for key in CONTRACT['required']:
        if key not in draft:
            raise ValueError('Review draft missing ' + key)
    if not isinstance(draft['expressions'], list) or not isinstance(draft.get('concept_observations', []), list):
        raise ValueError('expressions and concept_observations must be lists')
    stamp = datetime.fromisoformat(snapshot['voice_started_at'].replace('Z', '+00:00')).astimezone()
    day = stamp.date().isoformat()
    used = {p.stem for folder, glob in [('Sessions', '*.md'), ('Pending', '*.json')]
            for p in (root / folder).glob(glob)}
    sid = next_id('SES-' + day.replace('-', '') + '-', used)
    fields = ('title', 'summary', 'topics', 'scenarios', 'progress', 'next_focus', 'coaching_notes', 'unfinished')
    result = {k: deepcopy(draft[k]) for k in fields if k in draft}
    result.update(id=sid, date=day, practiced_at=stamp.isoformat(), source_ids=voice_sources(thread_id, voice_id),
                  end_status='ended', evidence_status='selected',
                  evidence_note='核对本场可用的去重转写后精选；转写不是发音证据。课后新增说法不代表会中已教学或已掌握。',
                  expressions=[], concept_observations=[])
    turns = {s['id']: s for s in snapshot['segments'] if s['role'] == 'user'}
    covered = set()

    def source_turns(item, quote):
        ids = item.get('source_turn_ids')
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in turns for i in ids):
            raise ValueError('Each selected item needs actual learner source_turn_ids from this Voice')
        # A short exact excerpt is allowed; paraphrases belong in english/note.
        if not isinstance(quote, str) or not quote.strip() or not any(quote in turns[i]['text'] for i in ids):
            raise ValueError('Selected original/quote must be an exact excerpt of a linked learner turn')
        covered.update(ids)

    expressions = {e['id']: e for e in state['expressions']}
    used = set(expressions)
    for p in (root / 'Pending').glob('*.json'):
        from practice_store import read_json
        used.update(e['id'] for e in read_json(p).get('expressions', []))
    by_text = {canonical_key(e['english'], e['chinese']): e for e in expressions.values()}
    for raw in draft['expressions']:
        item = deepcopy(raw)
        source_turns(item, item.get('original'))
        for quote in item.get('source_quotes',[]):
            source_turns(quote,quote.get('quote'))
        ref = item.pop('expression_ref', None)
        if ref:
            if ref not in expressions:
                raise ValueError('Unknown expression_ref: ' + str(ref))
            for key in ('english', 'chinese'):
                if key in item and item[key] != expressions[ref][key]:
                    raise ValueError('Conflicting expression_ref text; omit canonical fields')
                item[key] = expressions[ref][key]
        else:
            for key in ('english', 'chinese'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError('New expression needs ' + key)
            ref = by_text.get(canonical_key(item['english'], item['chinese']), {}).get('id')
        item['id'] = ref or next_id('EXP-' + day.replace('-', '') + '-', used)
        item.setdefault('mastery', 'not_tested')
        item.setdefault('next_review', (stamp.date() + timedelta(days=1)).isoformat())
        result['expressions'].append(item)
        by_text[canonical_key(item['english'], item['chinese'])] = item
    concepts = {c['id']: c for c in state.get('concepts', [])}
    for index, raw in enumerate(draft.get('concept_observations', [])):
        item = deepcopy(raw)
        source_turns(item, item.get('quote'))
        cid = item.get('concept_id')
        if cid:
            if cid not in concepts:
                raise ValueError('Unknown concept_id; new senses need term and meaning without an ID')
            for key in ('term', 'meaning'):
                if key in item and item[key] != concepts[cid][key]:
                    raise ValueError('Conflicting concept text; reference the existing ID without term/meaning, or create a separate sense')
                item[key] = concepts[cid][key]
        else:
            for key in ('term', 'meaning'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError('New concept needs ' + key)
            same = next((c for c in concepts.values() if canonical_key(c['term'], c['meaning']) == canonical_key(item['term'], item['meaning'])), None)
            item['concept_id'] = same['id'] if same else 'CON-' + hashlib.sha256((item['term'].strip().casefold() + '\n' + item['meaning'].strip()).encode()).hexdigest()[:16]
            if same:
                item.update(term=same['term'], meaning=same['meaning'])
        item['id'] = 'OBS-' + sid[4:] + '-' + str(index + 1)
        if item.get('modality', 'transcript') != 'transcript' or item.get('quote_kind', 'utterance') != 'utterance':
            raise ValueError('finish-review uses transcript utterances; other evidence needs its verified recovery path')
        item['modality'] = 'transcript'; item['quote_kind'] = 'utterance'
        item.setdefault('context', result['title'])
        indices = item.pop('expression_indices', [])
        if any(type(i) is not int or i < 0 or i >= len(result['expressions']) for i in indices):
            raise ValueError('Invalid expression_indices')
        item['expression_ids'] = [result['expressions'][i]['id'] for i in indices]
        result['concept_observations'].append(item)
    omitted = draft['omitted_turns']
    if not isinstance(omitted, dict) or any(k not in turns or not isinstance(v, str) or not v.strip() for k, v in omitted.items()):
        raise ValueError('omitted_turns must map actual learner turn IDs to concrete reasons')
    missing = set(turns) - covered - set(omitted)
    if missing:
        raise ValueError('Review has not accounted for learner turns: ' + ', '.join(sorted(missing)))
    if covered & set(omitted):
        raise ValueError('A recorded turn must not also be omitted')
    priorities = draft.get('priority_indices', list(range(min(3, len(result['expressions'])))))
    if not isinstance(priorities, list) or len(priorities) > 3 or any(type(i) is not int or i < 0 or i >= len(result['expressions']) for i in priorities) or len(set(priorities)) != len(priorities):
        raise ValueError('priority_indices needs up to three unique expression positions')
    result['review_priority_ids'] = [result['expressions'][i]['id'] for i in priorities]
    result['review_coverage'] = {'available_learner_turns': len(turns), 'selected_learner_turns': len(covered),
                                 'omitted_turns': omitted, 'scope': 'available_unique_segments',
                                 'judgment': 'Agent selection; coverage does not prove teaching quality'}
    if 'word_checks' in draft:
        result['review_coverage'].update(word_assessed_turns=len(draft['word_checks']),
            word_help_turns=sum(x['needs_word_help'] for x in draft['word_checks']),
            concept_observations=len(result['concept_observations']),
            reading_guided_expressions=sum(bool(e.get('reading_guide')) for e in result['expressions']))
    validate_payload(result)
    return result


def finish_review(root, draft, thread_id, voice_id, source=None):
    """Caller owns writer lock. Duplicate tails return the canonical saved lesson."""
    from practice_store import review_context, build_state, commit, validate
    from practice_runtime import set_review_stage
    from recover_voice import snapshot_voice
    from live_companion import find_source
    context = review_context(root, datetime.now().date().isoformat(), thread_id, voice_id)
    if context['existing_records']:
        return {'status': 'already_saved', 'session': context['existing_records'][0]['id'], 'validation': validate(root)}
    set_review_stage(root, thread_id, voice_id, 'saving', locked=True)
    try:
        pending = context['pending_records']
        if pending:
            if pending[0].get('end_status', 'ended') != 'ended':
                raise ValueError('An in-progress checkpoint needs explicit reconciliation before finish-review')
            result = commit(root, pending[0])
        else:
            snapshot = snapshot_voice(source or find_source(thread_id), thread_id, voice_id)
            payload = normalize_review(root, draft, thread_id, voice_id, snapshot, build_state(root))
            result = commit(root, payload)
        result['validation'] = validate(root)
        if not result['validation']['ok']:
            raise ValueError('Record saved but derived validation failed; preserve it and run recovery')
        set_review_stage(root, thread_id, voice_id, 'saved', locked=True, session_id=result['session'])
        return result
    except (ValueError, OSError, KeyError, TypeError) as exc:
        set_review_stage(root, thread_id, voice_id, 'error', locked=True, error=str(exc))
        raise

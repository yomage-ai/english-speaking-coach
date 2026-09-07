"""Stage-specific speaking context; storage and service work stay with the tool Agent."""
from datetime import datetime, timezone
from uuid import UUID
from urllib.parse import urlencode

PHASES = {'scene', 'review'}


def voice_sources(thread_id, voice_id):
    """Identify one actual Voice, including consecutive Voices in the same task."""
    try:
        thread_id, voice_id = str(UUID(thread_id)), str(UUID(voice_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Both actual thread and Voice UUIDs are required') from exc
    return ['codex-thread:' + thread_id, 'codex-voice:' + voice_id]


def review_route(thread_id, voice_id):
    sources = voice_sources(thread_id, voice_id)
    return '#review?' + urlencode({'thread': sources[0].split(':', 1)[1],
                                  'voice': sources[1].split(':', 1)[1]})


def compact_context(context, prepared=False):
    """Reduce repeated metadata, preserving preferences, evidence and live guidance."""
    keys = ('profile', 'phase', 'scene', 'startup', 'policy', 'voice_brief', 'companion', 'transition', 'closeout', 'learning_context')
    if not prepared:
        keys += ('latest_session', 'recent_scenarios', 'due_candidates', 'concept_review_candidates', 'pending')
    result = {key: context[key] for key in keys if key in context}
    result['profile'] = {k: v for k, v in context['profile'].items()
                         if k not in {'source_ids', 'schema_version'}}
    result['policy'] = {k:v for k,v in result.get('policy',{}).items() if k!='proactive_teaching'}
    if not prepared:
        result['due_candidates'] = [{k: v for k, v in item.items()
            if k not in {'attempts', 'seen_in_sessions'}} for item in context.get('due_candidates', [])]
        result['chronology'] = context.get('agent_context', {}).get('same_day_without_time', [])
    return result


def practice_time(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('practiced_at needs an explicit timezone')
    return stamp


def session_order(record):
    """Unknown same-day times sort before known times; importing never invents a time."""
    value = record.get('practiced_at')
    stamp = practice_time(value).astimezone(timezone.utc).isoformat() if value else ''
    return record['date'], stamp, record.get('id', record.get('session', ''))


def resolve_phase(profile, phase=None):
    phase = phase or ('review' if profile['mode'] == 'focused' else 'scene')
    if phase not in PHASES:
        raise ValueError('Phase must be scene or review')
    return phase


def transition(phase, event, review_delivery='spoken'):
    """Agent classifies the observed intent; a word such as Nothing is not an end signal."""
    if phase not in PHASES:
        raise ValueError('Unknown practice phase')
    if event in {'user_end', 'host_closed'}:
        return {'phase': None, 'action': 'end', 'spoken_review': False,
                'save_selected': True, 'continue_voice': False}
    if event == 'pause':
        return {'phase': phase, 'action': 'pause', 'spoken_review': False,
                'save_selected': False, 'continue_voice': False}
    if event == 'scene_complete_and_continuing':
        return {'phase': phase, 'action': 'offer_next_scene_or_finish', 'spoken_review': False,
                'save_selected': False, 'continue_voice': True}
    if event == 'review_requested':
        return {'phase': 'review', 'action': 'review', 'spoken_review': True,
                'save_selected': False, 'continue_voice': True}
    actions = {'continue': 'respond', 'help_requested': 'brief_help',
               'word_help_requested': 'supply_word', 'missing_expression': 'supply_phrase', 'meaning_unclear': 'clarify',
               'english_structure_help': 'model_usable_phrase', 'next_action_unclear': 'give_next_action',
               'meaning_confirmed': 'respond', 'content_clear': 'respond',
               'coaching_feedback': 'address_feedback'}
    if event in actions:
        return {'phase': phase, 'action': actions[event],
                'spoken_review': phase == 'review', 'save_selected': False, 'continue_voice': True}
    raise ValueError('Unknown observed practice event')


SCENE_FIELDS = ('setting', 'learner_role', 'partner_role', 'goal', 'introduction', 'opening_line')


def validate_scene(scene):
    if not isinstance(scene, dict) or not set(SCENE_FIELDS) <= set(scene) or set(scene) - set(SCENE_FIELDS) - {'key_terms'}:
        raise ValueError('Scene requires: ' + ', '.join(SCENE_FIELDS) + '; optional key_terms')
    for key in SCENE_FIELDS:
        if not isinstance(scene[key], str) or not scene[key].strip() or len(scene[key]) > 1000:
            raise ValueError('Scene ' + key + ' must be nonempty text of at most 1000 characters')
    result = {key: scene[key].strip() for key in SCENE_FIELDS}
    if 'key_terms' in scene:
        terms = scene['key_terms']
        if not isinstance(terms, list) or len(terms) > 3:
            raise ValueError('key_terms must be a list of at most three preparation candidates')
        result['key_terms'] = []
        seen = set()
        for term in terms:
            if not isinstance(term, dict) or set(term) != {'term', 'meaning', 'example'}:
                raise ValueError('Each key term needs term, meaning and example')
            if any(not isinstance(v, str) or not v.strip() or len(v) > 160 for v in term.values()):
                raise ValueError('Key term fields must be short nonempty text')
            clean = {k: v.strip() for k, v in term.items()}
            if clean['term'].casefold() in seen:
                raise ValueError('Duplicate preparation term')
            seen.add(clean['term'].casefold()); result['key_terms'].append(clean)
    return result


def speaking_context(profile, companion, latest, phase=None, scene=None):
    phase = resolve_phase(profile, phase)
    scene = validate_scene(scene) if scene is not None else None
    roleplay = phase == 'scene' and profile['mode'] == 'roleplay'
    deferred = profile['correction'] == 'after_scene'
    in_character = profile['correction'] == 'in_character'
    if profile['practice_language'] == 'english_first':
        language = ('Use English for all speech-facing messages, including setup updates, word help, '
                    'topic changes, scene introductions and coaching feedback. The written scene card uses '
                    + profile['help_language'] + '; spoken Chinese explanation requires an explicit request. '
                    'Chinese learner words do not switch the conversation language. ')
        if companion:
            language += 'Chinese help is on the companion page; its display language does not set the spoken language. '
    else:
        language = 'Use short English with brief ' + profile['help_language'] + ' support at the learner’s pace. '
    if phase == 'scene':
        role = ('Be ' + scene['partner_role'] + '. ' if scene else '') if roleplay else 'Be a natural conversation partner. '
        shared = ('Read learning_context before choosing difficulty. For a learner needing support, start with '
                  'one or two short sentences, about 10–20 words total, one useful point and at most one likely-new term. '
                  'These are adjustable starting targets, not a language level or an audio limiter. '
                  'Do not shorten by dropping a useful repair: if model plus role content overloads this learner, give the model first and retain the pending role answer for the next turn. After overload feedback keep later turns lighter too. Two requested details do not invite a third unrelated fact or step; an ordinary completed answer still needs a tiny cue for the same pending decision. Natural short answers remain valid. '
                  'Check meaning, usable English form, and the situation’s next action separately. Chinese/mixed content or missing English needs one usable phrase before role fulfillment; explicit help or ongoing formulation gets space to respond. '
                  'Coaching feedback: address it and change that behavior, without turning it into practice. '
                  'For overload, acknowledge in one short sentence and stop; do not append a simplified lesson or a new question. '
                  'A complaint about not knowing how to continue needs a brief acknowledgement plus a relevant situation cue now. '
                  'Accept resolved checks, self-repair and normal hesitations. After help and the learner’s reply, return to role action; praise alone is not a next step. '
                  'Keep the learner’s successfully used formulation; do not replace it with synonyms after acceptance. Keep confirmed facts, pending needs and who acts next. Do not change agreed dates or collapse alternatives without a choice. A recap retains agreed items unless changed. That is all ends adding items, not necessarily collection or payment. '
                  'After an ordinary role answer, give one explicit relevant next question or action; do not assume a price or acknowledgement tells a beginner what to do. Help/formulation space, pause and end are exceptions. A still-unanswered prior question may be restated briefly. Do not mechanically repeat Anything else. '
                  'One useful learning point and at most one main question. A brief model can accompany a short role answer if digestible. No running grades or compulsory retakes. ')
        if in_character:
            correction = ('English fragments with a useful unresolved structure error need one usable model even when their intent is obvious; do not silently answer only the meaning. '
                          'Known meaning gets You can say/ask; only uncertain meaning gets a check. Explicit help gets space; a completed English turn may receive a compact model plus role answer. ')
        elif deferred:
            correction = 'Save optional wording repairs for review; immediate missing-expression help still takes priority. Clarify genuine ambiguity. '
        else:
            correction = ('Briefly model useful unresolved English structure errors even when intent is understandable. ' if profile['correction'] == 'light' else
                          'Give the detailed correction the learner selected, without forcing repetition. ')
        if profile.get('input_support') == 'short_turns':
            shared = ('The learner chose short turns with gradual vocabulary support; retain meaningful adult topics. '
                      'At a new scene, briefly offer one or two useful phrases before the role opening unless declined or unnecessary from evidence. ') + shared
        behavior = shared + correction + ('Follow requested topic changes. When the scene is complete and the learner has not ended practice, '
                    'offer one choice to try a new scene or finish, then wait. Do not silently stop at the scene ending or force another scene. ')
    else:
        role = 'Be a supportive coach for a requested review. '
        behavior = ('Use selected actual utterances; distinguish misunderstandings, useful improvements and optional alternatives. '
                    'Keep support evidence; seeing or repeating a model is not independent use. ')
        behavior += ('Guide a targeted attempt when useful, without a fixed recitation sequence. '
                     if profile['drills'] == 'guided' else 'Offer focused practice only when requested. ')
    behavior += ('Keep meaning groups coherent, with light boundaries and a few informative stressed words; short phrases need no internal pause. On explicit reading help, model one or two groups, give one useful cue and leave space. Memory chunks are not mandatory spoken pauses. Do not read annotation marks aloud or infer pronunciation from transcripts. ')
    ending = ('An explicit end stops speech immediately; the Agent still saves and verifies the written record. '
              'A pause waits and does not create an ended lesson. ')
    brief = 'Local reminder for the responding Agent, not a policy update for another model.\n' + language + role + behavior + ending
    if roleplay and scene:
        import re
        intro = ('We are at ' + scene['setting'] + '. You are ' + scene['learner_role'] + '. I am ' + scene['partner_role'] + '. Your goal: ' + scene['goal'] + '.') if profile['practice_language']=='english_first' and re.search(r'[\u3400-\u9fff]',scene['introduction']) else scene['introduction']
        brief += ('\nIntroduce this fresh scene once in ' + ('English' if profile['practice_language']=='english_first' else profile['help_language']) + ': ' + intro
                  + '\nThen mark the English conversation boundary and open: ' + scene['opening_line'] + '\n')
        if scene.get('key_terms'):
            brief += ('Use scene.key_terms as preparation candidates: briefly preview only one or two useful items '
                      'before the role opening, then let the learner respond. Do not read the whole plan or assume the terms are unknown.\n')
    if roleplay and scene is None:
        brief = None
    return {'phase': phase, 'voice_brief': brief,
            'scene': scene if roleplay else None,
            'startup': {'scene_required': roleplay, 'scene_selected': bool(roleplay and scene),
                        'history_use': 'learning_only',
                        'next_action': 'Agent selects a fresh scene and reruns with --scene; do not hand off a generic readiness summary.' if roleplay and not scene else 'Open the prepared page once, allow at most one display recovery, then introduce this scene. Translation can continue connecting in the background.'},
            'policy': {'role': 'coach' if phase == 'review' else 'character' if profile['mode'] == 'roleplay' else 'partner',
                       'correction_timing': profile['correction'],
                       'review_delivery': profile.get('review_delivery', 'spoken'),
                       'input_support': profile.get('input_support', 'adaptive'),
                       'history_continuation': False,
                       'proactive_teaching': phase == 'review' or not (deferred or in_character),
                       'missing_expression_help': 'immediate_before_content',
                       'english_structure_help': 'after_scene' if deferred else 'model_when_useful_even_if_understandable',
                       'scene_completion': 'offer_next_scene_or_finish',
                       'next_action': 'make_relevant_next_step_visible',
                       'unsolicited_drills': False,
                       'embedded_recasts': phase == 'scene' and in_character,
                       'learner_expansion': phase == 'scene' and in_character,
                       'guided_drills': phase == 'review' and profile['drills'] == 'guided'}}

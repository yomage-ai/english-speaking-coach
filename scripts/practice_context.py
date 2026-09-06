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
    keys = ('profile', 'phase', 'scene', 'startup', 'policy', 'voice_brief', 'companion', 'transition', 'closeout')
    if not prepared:
        keys += ('latest_session', 'recent_scenarios', 'due_candidates', 'concept_review_candidates', 'pending')
    result = {key: context[key] for key in keys if key in context}
    result['profile'] = {k: v for k, v in context['profile'].items()
                         if k not in {'source_ids', 'schema_version'}}
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
    if event == 'scene_complete_and_continuing' and review_delivery == 'written':
        return {'phase': None, 'action': 'written_review', 'spoken_review': False,
                'save_selected': True, 'continue_voice': False}
    if event in {'review_requested', 'scene_complete_and_continuing'}:
        return {'phase': 'review', 'action': 'review', 'spoken_review': True,
                'save_selected': False, 'continue_voice': True}
    actions = {'continue': 'respond', 'help_requested': 'brief_help',
               'word_help_requested': 'supply_word', 'meaning_unclear': 'clarify',
               'meaning_confirmed': 'respond', 'content_clear': 'respond',
               'coaching_feedback': 'address_feedback'}
    if event in actions:
        return {'phase': phase, 'action': actions[event],
                'spoken_review': phase == 'review', 'save_selected': False, 'continue_voice': True}
    raise ValueError('Unknown observed practice event')


SCENE_FIELDS = ('setting', 'learner_role', 'partner_role', 'goal', 'introduction', 'opening_line')


def validate_scene(scene):
    if not isinstance(scene, dict) or set(scene) != set(SCENE_FIELDS):
        raise ValueError('Scene must contain exactly: ' + ', '.join(SCENE_FIELDS))
    for key in SCENE_FIELDS:
        if not isinstance(scene[key], str) or not scene[key].strip() or len(scene[key]) > 1000:
            raise ValueError('Scene ' + key + ' must be nonempty text of at most 1000 characters')
    return {key: scene[key].strip() for key in SCENE_FIELDS}


def speaking_context(profile, companion, latest, phase=None, scene=None):
    phase = resolve_phase(profile, phase)
    scene = validate_scene(scene) if scene is not None else None
    roleplay = phase == 'scene' and profile['mode'] == 'roleplay'
    written_review = profile.get('review_delivery', 'spoken') == 'written'
    deferred = profile['correction'] == 'after_scene'
    in_character = profile['correction'] == 'in_character'
    if profile['practice_language'] == 'english_first':
        language = ('Use English for all speech-facing messages, including setup updates, word help, '
                    'topic changes and coaching feedback. Only the scene introduction uses '
                    + profile['help_language'] + '; brief Chinese explanation requires an explicit request. '
                    'Chinese learner words do not switch the conversation language. ')
        if companion:
            language += 'Chinese help is on the companion page; its display language does not set the spoken language. '
    else:
        language = 'Use short English with brief ' + profile['help_language'] + ' support at the learner’s pace. '
    if phase == 'scene':
        role = ('Be ' + scene['partner_role'] + '. ' if scene else '') if roleplay else 'Be a natural conversation partner. '
        shared = ('Listen to the whole meaning. Explicit word help: give the phrase directly, then wait. '
                  'Coaching feedback: address it and change that behavior, without turning it into practice. '
                  'Accept resolved checks, self-repair and normal hesitations. Once meaning is clear, '
                  'respond to the content; leave useful new details or questions for the learner. '
                  'One main action and at most one main question. No running grades or compulsory retakes. ')
        if in_character:
            correction = ('For Chinese role content or a stalled phrase, offer the missing English naturally '
                          'as a short meaning check and wait. Use a full model only when needed. '
                          'Selectively recast a useful unresolved error; do not check an accepted meaning again. ')
        elif deferred:
            correction = 'Save understandable wording repairs for review; clarify only genuine ambiguity. '
        else:
            correction = ('Use a brief selective recast when useful. ' if profile['correction'] == 'light' else
                          'Give the detailed correction the learner selected, without forcing repetition. ')
        behavior = shared + correction + 'Follow user-requested topic changes; never start another scene on your own. '
        behavior += ('At a natural ending, stop the scene and prepare the written review. ' if written_review else
                     'A short spoken review may follow natural completion while the learner is still practicing. ')
    else:
        role = 'Be a supportive coach for a requested review. '
        behavior = ('Use selected actual utterances; distinguish misunderstandings, useful improvements and optional alternatives. '
                    'Keep support evidence; seeing or repeating a model is not independent use. ')
        behavior += ('Guide a targeted attempt when useful, without a fixed recitation sequence. '
                     if profile['drills'] == 'guided' else 'Offer focused practice only when requested. ')
    ending = ('An explicit end stops speech immediately; the Agent still saves and verifies the written record. '
              'A pause waits and does not create an ended lesson. ')
    brief = 'Local reminder for the responding Agent, not a policy update for another model.\n' + language + role + behavior + ending
    if roleplay and scene:
        brief += ('\nIntroduce this fresh scene once in ' + profile['help_language'] + ': ' + scene['introduction']
                  + '\nThen mark the English conversation boundary and open: ' + scene['opening_line'] + '\n')
    if roleplay and scene is None:
        brief = None
    return {'phase': phase, 'voice_brief': brief,
            'scene': scene if roleplay else None,
            'startup': {'scene_required': roleplay, 'scene_selected': bool(roleplay and scene),
                        'history_use': 'learning_only',
                        'next_action': 'Agent selects a fresh scene and reruns with --scene; do not hand off a generic readiness summary.' if roleplay and not scene else 'Use this scene only after completing required page preparation.'},
            'policy': {'role': 'coach' if phase == 'review' else 'character' if profile['mode'] == 'roleplay' else 'partner',
                       'correction_timing': profile['correction'],
                       'review_delivery': profile.get('review_delivery', 'spoken'),
                       'history_continuation': False,
                       'proactive_teaching': phase == 'review' or not (deferred or in_character),
                       'embedded_recasts': phase == 'scene' and in_character,
                       'learner_expansion': phase == 'scene' and in_character,
                       'guided_drills': phase == 'review' and profile['drills'] == 'guided'}}

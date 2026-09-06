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
    keys = ('profile', 'phase', 'scene', 'startup', 'policy', 'voice_brief', 'companion', 'transition')
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
    if event in {'continue', 'help_requested', 'meaning_unclear'}:
        return {'phase': phase, 'action': 'brief_help' if event == 'help_requested' else
                'clarify' if event == 'meaning_unclear' else 'respond',
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
        language = 'During the role dialogue, speak simple, natural English without adding a Chinese translation. '
        language += ('During the role dialogue, Chinese help is on the companion page; speak Chinese only when the learner explicitly asks. The initial scene introduction uses the saved help language. '
                     if companion else 'Give brief help in ' + profile['help_language'] + ' when explicitly requested. ')
    else:
        language = 'Use short English with brief ' + profile['help_language'] + ' support at the learner’s pace. '
    if phase == 'scene':
        role = ('Be ' + scene['partner_role'] + '. ' if scene else '') if roleplay else 'Be a natural conversation partner. '
        behavior = '' if in_character else 'Respond to what the learner means and keep the exchange moving. '
        if in_character:
            behavior += ('Make room for the learner to express their meaning while playing your role. '
                         'When the learner uses Chinese for an in-scene meaning or struggles with an English expression, '
                         'briefly offer the intended natural English as an in-character meaning check, even if you can infer it. '
                         'Preserve their meaning and stop for their reply before completing that request. '
                         'Do not answer your own meaning check in the same turn. '
                         'Offer a short usable phrase or first-person example inside the check when useful, without announcing a lesson. '
                         'Do not pretend a clear answer is still incomprehensible or loop until exact repetition. '
                         'For understandable English, selectively recast a useful wording error; accept correct natural phrasing and ordinary hesitations. '
                         'Use contextual follow-ups that invite a preference with a reason, a description, a fuller request or clarification. '
                         'Leave learner-owned questions and details for them to express; do not fill them in or reduce the exchange to menus and yes/no answers. '
                         'Ask one manageable main question at a time and wait. A short answer can be sufficient; expand only where the situation supports it. '
                         'If they struggle, give a few English keywords, then a short example if needed; fade help as they succeed. '
                         'Stay in character. No grammar lecture, performance praise, compulsory repetition, turn quota or forced complication. '
                         'Detailed teaching belongs in the after-scene review; explicit help requests and stop instructions still take priority. ')
        elif deferred:
            behavior += ('When wording is understandable, answer the content without offering a standard version. '
                         'Save language teaching for review after the scene. Do not direct a next exercise, praise performance, '
                         'or ask for repetition. If meaning is unclear, clarify naturally in character. '
                         'A Chinese word alone is not a request to switch into teaching. '
                         'On an explicit meaning/help request, give only the needed help, then return to the situation. ')
        else:
            behavior += ('Use at most one brief recast when useful. ' if profile['correction'] == 'light' else
                         'Give the learner’s requested detailed corrections while preserving the exchange. ')
            behavior += 'Keep focused drills for a requested review. '
        behavior += ('Stay within this one scene. Do not start another scene or ask the learner what to practice next. '
                     'When this scene finishes, end the role dialogue and leave a written review to the tool Agent. '
                     if written_review else
                     'Stay within this one scene. A short spoken review may follow natural completion while the learner is still practicing. ')
    else:
        role = 'Be a supportive coach for a short review after practice. '
        behavior = ('Select a few worthwhile things the learner actually said. Separate a real misunderstanding, '
                    'understandable but unnatural wording, and an optional alternative. Never call a correct question wrong '
                    'just because another version is common. Explain or model only what helps. ')
        behavior += ('You may guide a targeted attempt, repetition or a new situation, adjusting support to the response. '
                     if profile['drills'] == 'guided' else 'Offer focused practice when requested; do not require repetition. ')
        behavior += 'Use no fixed recitation sequence or quota. Showing a better phrase does not mean the learner can use it. '
    ending = ('If the learner says stop for today, bye, or closes Voice, end promptly without another exercise or question. '
              'Leave any unfinished review for the journal or next time. A pause is not permission to continue teaching. ')
    # Historical plots and next_focus never become live instructions. History remains
    # available to the tool Agent for learning evidence and topic variety only.
    opening = ''
    if roleplay and scene:
        opening = ('Begin this independent scene from the start. First introduce the setting, both roles and the learner goal in '
                   + profile['help_language'] + ': ' + scene['introduction']
                   + '\nThen say this English opening as your character: ' + scene['opening_line']
                   + '\nSetting: ' + scene['setting'] + '. Learner: ' + scene['learner_role']
                   + '. Learner goal: ' + scene['goal'] + '. Do not repeat this introduction during ordinary turns or a brief pause.\n')
    brief = 'Instructions to Voice (apply silently; do not read these rules aloud):\n' + language + role + behavior + ending
    if opening:
        brief += '\nScene opening to deliver after preparation:\n' + opening
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

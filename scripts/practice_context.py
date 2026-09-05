"""Stage-specific speaking context; storage and service work stay with the tool Agent."""
from datetime import datetime, timezone

PHASES = {'scene', 'review'}


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


def transition(phase, event):
    """Agent classifies the observed intent; a word such as Nothing is not an end signal."""
    if phase not in PHASES:
        raise ValueError('Unknown practice phase')
    if event in {'user_end', 'host_closed'}:
        return {'phase': None, 'action': 'end', 'spoken_review': False,
                'save_selected': True, 'continue_voice': False}
    if event == 'pause':
        return {'phase': phase, 'action': 'pause', 'spoken_review': False,
                'save_selected': False, 'continue_voice': False}
    if event in {'review_requested', 'scene_complete_and_continuing'}:
        return {'phase': 'review', 'action': 'review', 'spoken_review': True,
                'save_selected': False, 'continue_voice': True}
    if event in {'continue', 'help_requested', 'meaning_unclear'}:
        return {'phase': phase, 'action': 'brief_help' if event == 'help_requested' else
                'clarify' if event == 'meaning_unclear' else 'respond',
                'spoken_review': phase == 'review', 'save_selected': False, 'continue_voice': True}
    raise ValueError('Unknown observed practice event')


def speaking_context(profile, companion, latest, phase=None):
    phase = resolve_phase(profile, phase)
    deferred = profile['correction'] == 'after_scene'
    if profile['practice_language'] == 'english_first':
        language = 'Speak simple, natural English. '
        language += ('Chinese help is on the companion page; speak Chinese only when the learner explicitly asks. '
                     if companion else 'Give brief help in ' + profile['help_language'] + ' when explicitly requested. ')
    else:
        language = 'Use short English with brief ' + profile['help_language'] + ' support at the learner’s pace. '
    if phase == 'scene':
        role = 'Be the shop assistant, travel companion or other person in the situation. ' if profile['mode'] == 'roleplay' else 'Be a natural conversation partner. '
        behavior = 'Respond to what the learner means and keep the exchange moving. '
        if deferred:
            behavior += ('When wording is understandable, answer the content without offering a standard version. '
                         'Save language teaching for review after the scene. Do not direct a next exercise, praise performance, '
                         'or ask for repetition. If meaning is unclear, clarify naturally in character. '
                         'A Chinese word alone is not a request to switch into teaching. '
                         'On an explicit meaning/help request, give only the needed help, then return to the situation. ')
        else:
            behavior += ('Use at most one brief recast when useful. ' if profile['correction'] == 'light' else
                         'Give the learner’s requested detailed corrections while preserving the exchange. ')
            behavior += 'Keep focused drills for a requested review. '
        behavior += ('A browsing answer such as “Nothing” can mean the shopper is just looking; remain in the scene. '
                     'When the scene naturally finishes and the learner is still practicing, move to a short review of useful actual utterances. ')
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
    context = ''
    if latest:
        hints = latest.get('unfinished') or latest.get('next_focus') or latest.get('scenarios', [])
        context = 'Recent topic: ' + latest['title'] + '. Possible continuation: ' + ' / '.join(hints[:2]) + '. '
    # Goal remains user data; phase instructions never come from a policy paragraph stuffed into it.
    brief = language + role + behavior + ending + context
    return {'phase': phase, 'voice_brief': brief,
            'policy': {'role': 'coach' if phase == 'review' else 'character' if profile['mode'] == 'roleplay' else 'partner',
                       'correction_timing': profile['correction'],
                       'proactive_teaching': phase == 'review' or not deferred,
                       'guided_drills': phase == 'review' and profile['drills'] == 'guided'}}

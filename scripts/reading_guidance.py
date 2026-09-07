"""Validate optional teaching annotations, never observations of actual speech."""
import re

TONES = {'rise', 'fall', 'level', 'fall-rise', 'context'}


def words(text):
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.casefold(), re.UNICODE)


def short_text(value, label, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(label + ' must be short nonempty text')


def validate_guide(guide, english):
    if not isinstance(guide, dict) or set(guide) != {'kind', 'groups', 'tone', 'tone_note', 'memory'}:
        raise ValueError('reading_guide needs kind, groups, tone, tone_note and memory')
    if guide['kind'] != 'suggestion':
        raise ValueError('A reading guide is a suggestion, not measured audio evidence')
    groups = guide['groups']
    if not isinstance(groups, list) or not 1 <= len(groups) <= 6:
        raise ValueError('reading_guide needs one to six meaning groups')
    for group in groups:
        if not isinstance(group, dict) or set(group) != {'text', 'stress'}:
            raise ValueError('Each reading group needs text and stress')
        short_text(group['text'], 'Group text', 350)
        stress = group['stress']
        if not isinstance(stress, list) or len(stress) > 3 or any(not isinstance(w, str) for w in stress):
            raise ValueError('Group stress must list up to three words')
        if len(set(w.casefold() for w in stress)) != len(stress):
            raise ValueError('Duplicate stressed word')
        for word in stress:
            if words(word) != [word.casefold()] or word.casefold() not in words(group['text']):
                raise ValueError('Stress must identify a word in its reading group')
    if words(' '.join(g['text'] for g in groups)) != words(english):
        raise ValueError('Reading groups must preserve every original English word in order')
    if guide['tone'] not in TONES:
        raise ValueError('Unknown reading tone')
    short_text(guide['tone_note'], 'Tone explanation', 240)
    if not isinstance(guide['memory'], list) or not 1 <= len(guide['memory']) <= 4:
        raise ValueError('Memory needs one to four reusable parts')
    for part in guide['memory']:
        if not isinstance(part, dict) or set(part) != {'text', 'meaning'}:
            raise ValueError('Each memory part needs text and meaning')
        short_text(part['text'], 'Memory part', 160)
        short_text(part['meaning'], 'Memory meaning', 160)


def guide_markdown(guide):
    line = ' / '.join(g['text'] for g in guide['groups'])
    return ('\n怎么念（参考）：' + line + '\n\n' + guide['tone_note'] +
            '\n\n怎么记：' + '；'.join(p['text'] + ' — ' + p['meaning'] for p in guide['memory']) +
            '\n\n意群可轻停，记忆块不要求每块停顿；这是教学建议，不是实际语音评估。\n')


def stabilize_basic_guides(draft, help_language='zh-CN'):
    """Use a conservative neutral reading for short single-clause questions.

    This is a product teaching default, not a measured or mandatory intonation.
    Longer/compound phrases retain the model's contextual guidance.
    """
    from copy import deepcopy
    draft=deepcopy(draft)
    for item in draft.get('expressions',[]):
        english=item.get('english','').strip();guide=item.get('reading_guide')
        tokens=words(english)
        if not guide or not 2<=len(tokens)<=9 or not english.endswith('?'):
            continue
        if re.search(r'[,;:—]',english) or any(w in tokens for w in ('but','because','although','while')):
            continue
        if tokens[0] not in {'how','what','where','when','why','which','who','do','does','can','could','would','is','are','may','will'}:
            continue
        # A beginner can say the whole short question in one group. Memory parts
        # stay separate, but never create "How much is / each one?" breath marks.
        stress=list(dict.fromkeys(w for g in guide['groups'] for w in g['stress']))
        guide['groups']=[{'text':english,'stress':stress[:3]}]
        if 'or' not in tokens and tokens[0] in {'how','what','where','when','why','which','who'}:
            guide['tone']='fall'
            guide['tone_note']=('中性地询问信息时，句末可自然下降；确认或惊讶时可以换语调。'
                                if help_language=='zh-CN' else
                                'For a neutral information question, a fall is a useful option; checking or surprise can change the tune.')
    return draft

"""Small local preparation and closeout state; never evidence of learning success."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time


def code_revision(skill_root):
    digest = hashlib.sha256()
    for path in sorted((Path(skill_root) / 'scripts').glob('*.py')):
        digest.update(path.name.encode()); digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


# Defaults are a varied starting point. An Agent-authored scene always takes precedence.
# Each tuple has a family, setting, roles, communicative goal, opening and Chinese intro.
SCENES = [
    ('errand', 'A neighborhood bakery', 'A customer buying breakfast', 'The baker',
     'Ask for bread for two people and ask the price', 'Hello! What would you like today?',
     '今天在面包店。你是顾客，我是店员。你要买两个人的早餐，并问价钱。'),
    ('transport', 'A city bus stop', 'A visitor finding a bus', 'A local passenger',
     'Ask which bus goes to the museum and where to get off', 'Hi! Do you need help?',
     '今天在公交站。你是游客，我是当地乘客。你要问去博物馆坐哪路车、在哪里下车。'),
    ('social', 'A cafe with a friend', 'A friend making weekend plans', 'Your friend',
     'Suggest a weekend plan and agree on a meeting time', 'What would you like to do this weekend?',
     '今天和朋友约周末活动。你和我是朋友。你要提出一个安排，并约好见面时间。'),
    ('shopping', 'A clothing shop', 'A customer looking for a shirt', 'The shop assistant',
     'Describe the shirt you want and ask to try it on', 'Hi! What are you looking for?',
     '今天在服装店。你是顾客，我是店员。你要描述想买的衬衫，并询问能否试穿。'),
    ('lost_item', 'A station information desk', 'A traveler who lost a bag', 'The desk assistant',
     'Describe a missing bag and say where you last saw it', 'Hello. How can I help?',
     '今天在车站服务台。你是丢了包的旅客，我是工作人员。你要描述包，并说最后在哪里见过它。'),
    ('hotel', 'A hotel reception desk', 'A guest with a noisy room', 'The receptionist',
     'Explain the room problem and ask for a quieter room', 'Good evening. How can I help?',
     '今天在酒店前台。你是住客，我是前台。你的房间很吵，你要说明问题并询问能否换房。'),
    ('work', 'A short conversation with a coworker', 'A coworker planning a task', 'Your coworker',
     'Explain what you are working on and ask for one piece of help', 'What are you working on today?',
     '今天和同事聊工作。你和我是同事。你要介绍正在做的事，并提出一个需要帮助的地方。'),
    ('study', 'A class after the lesson', 'A student asking a question', 'Your classmate',
     'Explain which part was difficult and ask for an example', 'How was the lesson for you?',
     '今天在下课后。你和我是同学。你要说哪一部分比较难，并请我举一个例子。'),
    ('directions', 'A neighborhood street', 'A visitor looking for a park', 'A local resident',
     'Ask how to walk to a park and how long it takes', 'Hi there. Are you looking for somewhere?',
     '今天在街上问路。你是游客，我是当地居民。你要问怎么步行去公园、需要多久。'),
    ('restaurant', 'A small restaurant', 'A guest choosing lunch', 'The server',
     'Ask about one dish and explain what you would like', 'Hello! What would you like for lunch?',
     '今天在餐厅。你是客人，我是服务员。你要询问一道菜，并说明想点什么。'),
]
FAMILY_WORDS = {
    'water': ('swim', 'diving', 'boat', 'water sport', '游泳', '潜水', '船', '水上'),
    'transport': ('bus', 'train', 'ticket', '公交', '火车', '车票'),
    'restaurant': ('restaurant', 'order food', '点餐', '餐厅'),
    'errand': ('bakery', 'bread', '面包店'), 'shopping': ('shop', 'shirt', '购物', '服装'),
    'hotel': ('hotel', '酒店'), 'lost_item': ('lost', 'missing', '丢'),
    'social': ('weekend', 'friend', '朋友', '周末'),
    'work': ('coworker', 'project', '同事', '工作'),
    'study': ('classmate', 'lesson', '同学', '课程'),
    'directions': ('walk', 'direction', '问路', '步行'),
}


def families(text):
    text = text.casefold()
    return {key for key, words in FAMILY_WORDS.items() if any(word in text for word in words)}


def history(root):
    path = Path(root) / 'Runtime/scene-history.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []


def choose_scene(root, context):
    recent = history(root)[-8:]
    evidence = context.get('recent_scenarios', [])[-6:]
    avoided = set().union(*(families(json.dumps(x, ensure_ascii=False)) for x in [*evidence, *recent]))
    goal = context['profile']['goal'].casefold()
    preferred = 'work' if any(w in goal for w in ('work', 'job', '工作', '外企')) else 'study' if any(w in goal for w in ('study', 'campus', '留学', '校园')) else None
    counts = {s[0]: sum(s[0] in families(json.dumps(x, ensure_ascii=False)) for x in recent) for s in SCENES}
    chosen = min(SCENES, key=lambda s: (s[0] in avoided, s[0] != preferred if preferred else False, counts[s[0]], next((len(recent)-i for i,x in enumerate(reversed(recent)) if s[0] in families(json.dumps(x,ensure_ascii=False))), 0)))
    family, setting, learner, partner, goal, opening, zh = chosen
    introduction = zh if context['profile']['help_language'] == 'zh-CN' else f'We are at {setting.lower()}. You are {learner.lower()}, and I am {partner.lower()}. Your goal: {goal.lower()}.'
    return dict(setting=setting, learner_role=learner, partner_role=partner, goal=goal,
                introduction=introduction, opening_line=opening)


def remember_scene(root, binding_id, scene):
    from practice_store import writer, write_json
    with writer(Path(root)):
        rows = history(root)
        if any(x['binding_id'] == binding_id and x['scene'] == scene for x in rows):
            return
        rows.append({'binding_id': binding_id, 'scene': scene,
                     'selected_at': datetime.now(timezone.utc).isoformat()})
        write_json(Path(root) / 'Runtime/scene-history.json', rows[-24:])


def scene_for_binding(root, binding_id):
    return next((x['scene'] for x in reversed(history(root)) if x['binding_id'] == binding_id), None)


def review_file(root, thread_id, voice_id):
    from practice_context import voice_sources
    key = hashlib.sha256('\n'.join(voice_sources(thread_id, voice_id)).encode()).hexdigest()[:24]
    return Path(root) / 'Runtime/Reviews' / (key + '.json')


def set_review_stage(root, thread_id, voice_id, status, locked=False, **fields):
    from practice_store import writer, write_json
    if status not in {'practicing', 'queued', 'reading', 'generating', 'checking', 'preparing', 'saving', 'saved', 'error'}:
        raise ValueError('Unknown review stage')
    def save():
        path = review_file(root, thread_id, voice_id)
        prior = json.loads(path.read_text()) if path.exists() else {}
        # A setup retry must not hide an already-started or completed closeout.
        if status == 'practicing' and prior:
            return prior
        stamp = time.time()
        result = {**prior, 'status': status, 'thread_id': thread_id, 'voice_id': voice_id,
                  'created_epoch': prior.get('created_epoch', stamp), **fields}
        if status != 'practicing':
            result.setdefault('started_epoch', stamp)
        if prior.get('status') != status:
            result['stage_epoch'] = stamp
        if status != 'error':
            result.pop('error', None)
        write_json(path, result)
        return result
    if locked:
        return save()
    with writer(Path(root)):
        return save()


def begin_review(root, thread_id, voice_id):
    return set_review_stage(root, thread_id, voice_id, 'preparing')


def review_status(root, thread_id, voice_id):
    path = review_file(root, thread_id, voice_id)
    if not path.exists():
        return {'status': 'waiting', 'elapsed_seconds': 0}
    data = json.loads(path.read_text())
    elapsed = max(0, int(time.time() - data.get('started_epoch', time.time())))
    stage = data.get('status', 'preparing')
    return {**data, 'stage': stage, 'status': 'needs_attention' if stage in {'queued','reading','generating','checking','preparing','saving'} and elapsed >= 180 else stage,
            'elapsed_seconds': elapsed}


def recent_reviews(root):
    """Read registration metadata only; source records decide whether saving succeeded."""
    rows = [json.loads(p.read_text()) for p in (Path(root) / 'Runtime/Reviews').glob('*.json')]
    return sorted(rows, key=lambda row: row.get('created_epoch', row.get('started_epoch', 0)), reverse=True)

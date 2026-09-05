"""Render a portable, offline journal; session facts stay in Markdown."""
from datetime import date
from html import escape
from pathlib import Path
import json
import re

LABELS = {'not_tested':'尚未尝试', 'source_text':'看原句说出', 'keywords':'借关键词说出', 'independent':'曾独立说出', 'transfer':'曾换场景使用'}

def e(value):
    return escape(str(value), quote=True)

def tip(title, body):
    return '<span class="help"><button type="button" class="help-toggle" aria-label="' + e(title) + '说明" aria-expanded="false">?</button><span class="help-body" role="tooltip">' + e(body) + '</span></span>'

def paragraph_list(items):
    return ''.join('<p>' + e(x) + '</p>' for x in items)

def read_record(root, session, state):
    text = (root / 'Sessions' / (session['id'] + '.md')).read_text(encoding='utf-8')
    match = re.search(r'<!-- speaking-record-v2\n(.*?)-->', text, re.S)
    if match:
        record = json.loads(match.group(1))
        supplement = text.split('## 我的补充\n', 1)[1].strip() if '## 我的补充\n' in text else ''
        if supplement.startswith('可在这里自由补充学习笔记；'):
            supplement = supplement.split('\n', 1)[1].strip() if '\n' in supplement else ''
        return record, supplement
    # Read only the known legacy table, never today's index as old utterance evidence.
    rows = []
    table = text.split('## 精选表达与证据', 1)[1].split('\n## ', 1)[0] if '## 精选表达与证据' in text else ''
    for line in table.splitlines():
        cells = [c.strip().replace('\\|', '|') for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
        if len(cells) == 6 and cells[0] not in {'用户原话', '---'}:
            rows.append({'original':cells[0], 'english':cells[1], 'chinese':cells[2], 'note':'旧课次记载：' + cells[4] + '。这是当时保存的状态；未补造更详细的提示过程。'})
    return {**session, 'expressions':rows, 'evidence_note':'旧课次原话与状态直接读取原始 Markdown 表格；保留当时的判断，不用当前索引改写旧证据。文字不能证明发音准确。'}, ''

def render(state, root, snapshot=False):
    root = Path(root)
    today = date.today().isoformat()
    sessions = list(reversed(state['sessions']))
    latest = sessions[0] if sessions else None
    profile = state['profile']
    expressions = list(reversed(state['expressions']))
    latest_record = read_record(root, latest, state)[0] if latest else None
    feature = next(iter(latest_record.get('expressions', [])), None) if latest_record else None
    if feature is None and expressions:
        feature = expressions[0]
    due = [x for x in expressions if x['next_review'] <= today]
    dated = sorted(set(s['date'] for s in sessions))
    hero = '<span class="eyebrow">A phrase from your practice · 练习里的一句话</span><blockquote>' + e(feature['english'] if feature else 'What would you like to talk about today?') + '</blockquote><p>' + e(feature['chinese'] if feature else '从今天想说的一件小事开始。') + '</p>'
    if feature:
        hero += '<a class="text-link" href="#session-' + e(feature.get('source_session', latest['id'] if latest else '')) + '">回到这次练习 <span aria-hidden="true">↗</span></a>'
    journal = []
    for session in sessions:
        record, supplement = read_record(root, session, state)
        recovered = '<span class="badge">历史补录 · 精选转写</span>' if record.get('recovered_on') else ''
        facts = ''
        for item in record.get('expressions', []):
            facts += '<div class="utterance"><p class="small-label">我当时说</p><p class="original">' + e(item.get('original') or '未记录原话；仅收集表达，尚未测试。') + '</p><p class="small-label">可以这样表达</p><p class="model" lang="en">' + e(item['english']) + '</p><p>' + e(item['chinese']) + '</p><p class="evidence">' + e(item['note']) + '</p></div>'
        if not record.get('expressions'):
            facts = '<p class="muted">本页未列出逐句证据。' + ('旧记录的表达表格保留在原始 Markdown 中。' if not record.get('source_ids') else '本次未新增表达。') + '</p>'
        raw = '<details class="raw-source"><summary>查看原始 Markdown 文本</summary><pre>' + e((root / 'Sessions' / (session['id'] + '.md')).read_text(encoding='utf-8')) + '</pre></details>'
        journal.append('<article class="journal-row"><div class="date-stamp"><span>' + e(session['date'][:4]) + '</span><strong>' + e(session['date'][5:].replace('-', '.')) + '</strong></div><details class="session" id="session-' + e(session['id']) + '"><summary><span><span class="small-label">' + e(' / '.join(session.get('scenarios', [])) or '自由对话') + '</span><strong>' + e(session['title']) + '</strong></span><span class="expand" aria-hidden="true">＋</span></summary><div class="session-body">' + recovered + '<p class="summary">' + e(session.get('summary', '旧记录未单独保存摘要。')) + '</p>' + facts + '<div class="journal-bottom"><div><h4>这次留下的观察</h4>' + paragraph_list(session.get('progress', []) or ['没有额外评定进步。']) + '</div><div><h4>下次接着聊</h4>' + paragraph_list(session.get('next_focus', []) or ['从你当下想说的事开始。']) + '</div></div>' + ('<h4>我的补充</h4><p class="personal-note">' + e(supplement) + '</p>' if supplement else '') + '<p class="boundary">' + e(record.get('evidence_note', '精选转写用于表达反馈；不能据此判断发音，也不代表完整逐字稿。')) + '</p><div class="source-row"><a href="Sessions/' + e(session['id']) + '.md">打开 Markdown 原始记录 ↗</a><span>' + e(session['id']) + '</span></div>' + raw + '</div></details></article>')
    cards = []
    for item in expressions:
        links = ' · '.join('<a href="#session-' + e(sid) + '">' + e(sid[4:8] + '.' + sid[8:10] + '.' + sid[10:12]) + '</a>' for sid in item.get('seen_in_sessions', [item['source_session']]))
        observation = item.get('attempts', [])[-1] if item.get('attempts') else None
        history = '最近观察：' + item.get('updated', '') + ' · ' + LABELS[item['mastery']]
        cards.append('<article class="expression" data-search="' + e(item['english'] + ' ' + item['chinese'] + ' ' + ' '.join(item.get('issue_tags', []))) + '" data-due="' + ('yes' if item['next_review'] <= today else 'no') + '" data-state="' + e(item['mastery']) + '"><div class="expression-meta"><span class="badge">' + e(LABELS[item['mastery']]) + '</span><span>' + e(item.get('updated', '')) + '</span></div><h3>' + e(item['chinese']) + '</h3><details class="answer"><summary>想一想怎么说，再看表达 <span aria-hidden="true">↘</span></summary><div><p class="model" lang="en">' + e(item['english']) + '</p><p class="evidence">' + e(item['note']) + '</p></div></details><p class="observation">' + e(history) + '</p><div class="expression-footer"><span>记录：' + links + '</span><span>建议再聊 ' + e(item['next_review']) + '</span></div></article>')
    observations = []
    for session in sessions[:4]:
        observations.append('<li><span class="small-label">' + e(session['date']) + '</span><p>' + e((session.get('progress') or ['保存了这次练习，未评定能力变化。'])[0]) + '</p><a href="#session-' + e(session['id']) + '">查看依据 ↗</a></li>')
    focus = ' / '.join(latest.get('next_focus', [])) if latest else '聊聊今天的一个小计划。'
    mode = {'conversation':'自然对话', 'roleplay':'情景扮演', 'focused':'针对练习'}[profile['mode']]
    replacements = {
        'HERO':hero,
        'NEXT':e(focus or '继续你当下想说的话题。'),
        'SESSION_COUNT':str(len(sessions)), 'EXPRESSION_COUNT':str(len(expressions)),
        'DATE_COUNT':str(len(dated)), 'DUE_COUNT':str(len(due)),
        'JOURNAL':''.join(journal) or '<p class="empty">第一次练习结束后，这里会留下你的学习手记。</p>',
        'EXPRESSIONS':''.join(cards), 'OBSERVATIONS':''.join(observations),
        'GOAL':e(profile['goal']), 'MODE':e(mode),
        'LANGUAGE':e('英语为主，需要时中文帮助' if profile['practice_language'] == 'english_first' else '中英辅助，按理解情况调整'),
        'CORRECTION':e('少量纠正，接着聊' if profile['correction'] == 'light' else '详细反馈'),
        'DRILLS':e('需要时再专项练习' if profile['drills'] == 'on_request' else '引导式专项练习'),
        'REVIEW_TIP':tip('建议复习', '这些表达已到建议重访日期。Agent 每次自然带回少量内容；不是欠下的作业。点表达的记录日期可查看当时证据。'),
        'STATE_TIP':tip('表达状态', '记录最近一次有证据的提示情况，不代表永久掌握或英语等级。曾独立说出仍需隔一段时间再用；看学习手记核对原话和提示。'),
        'PROGRESS_TIP':tip('学习足迹', '课次和表达数量只表示留下了多少记录。能力变化要看延时、少提示或换场景的实际表现；下面每条观察都可追溯。'),
        'GENERATED':e(('导出快照 · ' if snapshot else '最近生成 · ') + today),
        'SNAPSHOT_NOTE':'这是交付时的阅读快照；日常练习会更新知识库中的学习手记。' if snapshot else '每次保存练习后刷新本页。Markdown 记录也可直接在 Obsidian 中阅读。',
    }
    template = (Path(__file__).parent.parent / 'assets' / 'journal.html').read_text(encoding='utf-8')
    return re.sub(r'@@([A-Z_]+)@@', lambda m:replacements[m.group(1)], template)

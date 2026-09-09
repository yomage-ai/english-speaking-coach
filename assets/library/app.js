'use strict';
const $ = (s, root = document) => root.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const main = $('#content');
const labels = {not_tested:'尚未尝试',source_text:'看原句说出',keywords:'借关键词说出',independent:'曾独立说出',transfer:'曾换场景使用'};
const bookEnglish = {'旅行出行':'Out & about','宠物咨询':'Care & ask','日常聊天':'Everyday life'};
let overview, overviewLoading, renderVersion = 0, toastTimer, reviewTimer, reviewPolling = false;
const trackedReviews = new Map(), reviewSeen = new Map();
const href = (path, args = {}) => '#' + path + (Object.keys(args).length ? '?' + new URLSearchParams(args) : '');
const route = () => { const [path, query = ''] = location.hash.slice(1).split('?'); return {path:path || 'overview', args:Object.fromEntries(new URLSearchParams(query))}; };
const shortDate = d => d ? d.slice(5).replace('-', '.') : '';
const fullDate = d => d ? `${d.slice(0,4)} 年 ${Number(d.slice(5,7))} 月 ${Number(d.slice(8,10))} 日` : '';
const tag = (text, type = '') => `<span class="tag ${type}">${esc(text)}</span>`;
const tip = (name, body) => `<span class="help"><button type="button" aria-label="${esc(name)}说明" aria-expanded="false">?</button><span class="help-body" role="tooltip">${esc(body)}</span></span>`;
// Browser speech was removed after real-host checks showed false completion
// and inconsistent audio. Keep rendering calls inert for older view helpers.
const speechButton = () => '';
const list = items => items.map(x => `<p>${esc(x)}</p>`).join('');
const empty = (title, body, path) => `<div class="empty"><strong>${esc(title)}</strong>${esc(body)}${path ? `<br><a class="button" href="${esc(href(path))}">查看全部记录</a>` : ''}</div>`;
const heading = (kicker, title, description, action = '') => `<div class="page-heading"><div><span class="eyebrow">${esc(kicker)}</span><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${action}</div>`;
const metric = (count, name, description) => `<div class="metric"><strong>${count}</strong><span>${name}${description ? tip(name, description) : ''}</span></div>`;
const sourceDate = s => `<div class="date-stamp">${esc(s.date.slice(0,4))}<strong>${shortDate(s.date)}</strong></div>`;

async function api(path, args = {}) {
  const response = await fetch(path + (Object.keys(args).length ? '?' + new URLSearchParams(args) : ''), {cache:'no-store', signal:AbortSignal.timeout(8000)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '读取失败，请刷新重试。');
  return result;
}
function toast(text) {
  $('#toast').textContent = text; $('#toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 2600);
}
function updateMeta(data) {
  if(!data.revision){$('#sync').textContent='本机存储配置';$('#revision').textContent='本地数据';return;}
  $('#sync').textContent = '记录更新于 ' + shortDate(data.source_updated_at.slice(0,10)) + ' ' + data.source_updated_at.slice(11,16);
  $('#revision').textContent = data.revision.slice(0,6);
}
function loadGoalInBackground() {
  if(overviewLoading)return;
  overviewLoading=api('/api/overview').then(data=>{
    overview=data;$('#goal').textContent=data.profile.goal;
  }).catch(()=>{}).finally(()=>{overviewLoading=null;});
}
function home(data) {
  const {latest, books} = data;
  const feature = latest?.excerpts?.find(e=>(latest.review_priority_ids||[]).includes(e.id)) || latest?.excerpts?.[0];
  return heading('START HERE', '学习首页', '现在想练什么？先回顾一句，或回到最近一次练习。', '<a class="button" href="#stats">查看一段时间的变化 ↗</a>') +
    `<section class="quick-review home-start"><div class="section-head"><div><h2>先花两分钟，试着说一句</h2><p>从到期表达中选几条；先看中文，再回想英文。</p></div><a class="button primary" href="${esc(href('terms',{mode:'speak',due:'1'}))}">开始回顾 ↗</a></div>${data.review_terms.map(t => `<a class="review-small" href="${esc(href('terms',{q:t.chinese,mode:'speak'}))}">${esc(t.chinese)}<span>${esc(t.book)} · ${esc(t.state_label)}</span></a>`).join('') || '<p class="fine">目前没有到期表达，可以到生词与表达里选一句回顾。</p>'}</section>` +
    (latest ? `<section class="hero" aria-label="最近一次练习"><div class="hero-quote"><span class="eyebrow">最近一次的表达 · ${esc(shortDate(latest.date))}</span><blockquote lang="en">${esc(feature?.english || latest.title)}</blockquote><p>${esc(feature?.chinese || '')}</p></div><div class="hero-summary">${tag('最近一次 · ' + latest.book)}<h2>${esc(latest.title)}</h2><p>${esc(latest.summary)}</p><a class="button primary" href="${esc(href('sessions/' + latest.id))}">查看这次总结 ↗</a></div></section>` : empty('第一段练习，还在等你','对 Agent 说「练英语」，保存后这里就会出现你的第一篇记录。')) +
    `<div class="home-grid"><section><div class="section-head"><h2>最近聊过什么</h2><a class="text-link" href="#sessions">全部记录 ↗</a></div><div class="panel">${data.recent.map(s => `<a class="session-link" href="${esc(href('sessions/' + s.id))}">${sourceDate(s)}<div><h3>${esc(s.title)}</h3><p>${esc(s.book)} · ${s.card_count ?? s.expression_count} 张词语与表达卡</p></div><span class="arrow">↗</span></a>`).join('') || '<p class="muted">还没有课次记录。</p>'}</div></section><section><div class="section-head"><h2>按生活主题找表达</h2><a class="text-link" href="#terms">全部表达 ↗</a></div><div class="books">${books.map(b => `<a class="book" href="${esc(href('terms',{book:b.name}))}"><span class="book-en" lang="en">${esc(bookEnglish[b.name] || b.name)}</span><h3>${esc(b.name)}</h3><p>${b.count} 条表达 · ${b.sessions} 次对话</p></a>`).join('')}</div><div class="practice-note"><strong>想开始下一场对话</strong><p>直接对 Agent 说「练英语」。AI 会参考学习记录选择新场景，介绍地点、角色和目标，再开始。</p>${latest?.next_focus?.length?`<p>上次建议继续练：${esc(latest.next_focus.join('；'))}</p>`:''}</div></section></div>`;
}
function filters(path, args, books) {
  const terms = path === 'terms';
  return `<form class="filters" data-filter="${path}"><label class="search-field">${terms ? '查找生词、句子或中文意思' : '查找主题、原话或总结'}<input name="q" type="search" value="${esc(args.q || '')}" placeholder="输入关键词，按回车搜索" autocomplete="off"></label><label>从哪天<input type="date" name="from" aria-label="开始日期" value="${esc(args.from || '')}"></label><label>到哪天<input type="date" name="to" aria-label="结束日期" value="${esc(args.to || '')}"></label>${terms ? `<label>表达状态<select name="state"><option value="">全部状态</option>${Object.entries(labels).map(([v,t]) => `<option value="${v}" ${args.state===v?'selected':''}>${t}</option>`).join('')}</select></label>` : `<label>主题<select name="book"><option value="">全部主题</option>${books.map(b => `<option value="${esc(b.name)}" ${args.book===b.name?'selected':''}>${esc(b.name)}</option>`).join('')}</select></label>`}<div class="filter-actions"><button class="button primary" type="submit">搜索</button><a class="button" href="${esc(href(path, path==='terms' ? {mode:cardMode(args)} : {}))}">重置</a></div></form>`;
}
function pager(data, path, args) {
  if(data.pages<=1)return '';
  return `<div class="pager"><button class="button small" data-page="${data.page-1}" ${data.page<=1?'disabled':''}>上一页</button><span>第 ${data.page} / ${data.pages} 页 · 共 ${data.total} 条</span><button class="button small" data-page="${data.page+1}" ${data.page>=data.pages?'disabled':''}>下一页</button></div>`;
}
function sessionsPage(data, args) {
  return heading('CONVERSATIONS','对话记录','按日期回看每次练习：聊了什么、怎么表达、下次接着练什么。') + filters('sessions',args,data.books) + `<div class="filter-meta"><span>找到 ${data.total} 次对话</span><span>按练习日期从近到远排列</span></div>` +
    (data.items.length ? `<div class="records">${data.items.map(s => `<article class="record-card">${sourceDate(s)}<div><h2><a href="${esc(href('sessions/'+s.id))}">${esc(s.title)}</a></h2><div class="meta">${tag(s.book)}<span>${s.card_count ?? s.expression_count} 张词语与表达卡</span>${s.recovered_on?'<span>历史补录</span>':''}</div><p>${esc(s.summary)}</p></div><div class="action"><a class="text-link" href="${esc(href('sessions/'+s.id))}">查看记录 ↗</a></div></article>`).join('')}</div>${pager(data,'sessions',args)}` : empty('没有找到匹配的对话','试试换个关键词，或扩大日期范围。','sessions'));
}
function readingGuide(e) {
  const g=e.reading_guide;
  if(!g || g.kind!=='suggestion' || !Array.isArray(g.groups) || !Array.isArray(g.memory))return '';
  const marked=group=>{
    const stress=new Set(group.stress.map(w=>w.toLocaleLowerCase()));
    return group.text.split(/([\p{L}\p{N}]+(?:['’][\p{L}\p{N}]+)*)/u).map(part=>stress.has(part.toLocaleLowerCase())?`<strong>${esc(part)}</strong>`:esc(part)).join('');
  };
  const arrows={rise:'↗',fall:'↘',level:'→','fall-rise':'↘↗',context:'↔'};
  return `<details class="reading-guide"><summary>怎么念 · 怎么记 <span>含英文提示</span></summary><div class="reading-body"><p class="fine">按意思分组，/ 处可轻停；粗体略重。网页换行不代表停顿。</p><p class="reading-line" lang="en">${g.groups.map(group=>`<span class="reading-group">${marked(group)}</span>`).join('<span class="reading-break" aria-label="可轻停"> / </span>')} <span class="reading-tone" aria-hidden="true">${arrows[g.tone]||''}</span></p><p class="tone-note">${esc(g.tone_note)}</p><h3>先记住这些表达块</h3><div class="memory-parts">${g.memory.map(p=>`<div><strong lang="en">${esc(p.text)}</strong><span>${esc(p.meaning)}</span></div>`).join('')}</div><p class="fine">记忆块方便起头和替换，不要求每块都停顿。这是参考读法，不是实际语音评分。</p></div></details>`;
}
function excerpt(e) {
  return `<article class="excerpt"><span class="small-label">我当时说</span><p class="original" lang="en">${esc(e.original || '这条没有记录原话。')}</p><span class="small-label">${e.original?.trim()===e.english.trim()?'这句话可以继续用':'表达参考'}</span><p class="model" lang="en">${esc(e.english)}</p><p class="chinese">${esc(e.chinese)}</p><p class="evidence-note">${esc(e.note)}</p>${e.source_quotes?.length>1?`<details class="source-quotes"><summary>这句话的求助与后续尝试</summary>${e.source_quotes.map(q=>`<p>${esc(q.quote)}</p>`).join('')}</details>`:''}${readingGuide(e)}</article>`;
}
function lessonPage(s) {
  const selected=new Set(s.review_priority_ids || []);
  const first=s.review_priority_ids?s.excerpts.filter(e=>selected.has(e.id)):s.excerpts.slice(0,3);
  const rest=s.review_priority_ids?s.excerpts.filter(e=>!selected.has(e.id)):s.excerpts.slice(3);
  const count=`${s.excerpts.length} 组完整表达 · ${s.card_count ?? s.expression_count} 张词句卡`;
  const coverage=s.review_coverage;
  return `<a class="back" href="#sessions">← 返回对话记录</a><div class="lesson-heading"><span class="eyebrow">${esc(fullDate(s.date))}</span><h1>${esc(s.title)}</h1><div class="meta">${tag(s.book)}<span>${count}</span>${tip('复盘与卡片','完整表达包含原话、推荐说法和帮助情况；词卡还可能包含从整句抽出的单词，所以数量不同。先看优先表达，再展开其余内容；到本次词卡核对全部收录。')}${s.recovered_on?'<span>补录于 '+esc(s.recovered_on)+'</span>':''}</div></div><div class="lesson-layout"><div><section class="lesson-summary"><h2>这次聊了什么</h2><p>${esc(s.summary || '本次没有单独保存摘要。')}</p></section><div class="section-head"><div><h2>${first.length?'先练这几句':'本次表达'}</h2><p class="fine">${s.review_priority_ids?'根据本次求助和表达问题选取；其余值得保留的内容仍在下方。':'先看原记录中的几句；其余表达可在下方展开。'}</p></div></div><div>${first.map(excerpt).join('') || (!rest.length?empty('这次没有新的表达需要收录','上方保留了本次总结。'):'')}</div>${rest.length?`<details class="remaining-expressions"><summary>展开其余 ${rest.length} 组表达与原话</summary>${rest.map(excerpt).join('')}</details>`:''}<details class="source-box"><summary>记录来源与完整性</summary><p>${esc(s.evidence_note || '此页仅展示当时保留下来的学习记录。')}</p>${coverage?`<p>已核对 ${coverage.available_learner_turns} 条可用学习者发言，其中 ${coverage.selected_learner_turns} 条关联到学习内容；招呼、已正确表达等内容无需重复制卡。这项核对不代表教学效果已验证。</p>`:''}<p>可用系统声音朗读表达参考；你的原话保留供对照，不参与朗读。<br>这些是精选学习片段，不是完整聊天逐字稿。表达建议不冒充 AI 在会中说过的原话。</p><p>课次编号：${esc(s.id)}</p>${s.source_ids?.length?'<p>来源：'+esc(s.source_ids.join(' · '))+'</p>':''}<a href="/records/${esc(s.id)}.md" target="_blank" rel="noopener">查看原始 Markdown 记录 ↗</a></details></div><aside class="lesson-aside">${s.coaching_notes?.length?`<section class="panel coach-adjustments"><h2>教练下次如何调整</h2>${list(s.coaching_notes)}</section>`:''}<section class="panel"><h2>这次的学习观察</h2>${list(s.progress || ['没有额外保存观察。'])}</section><section class="panel"><h2>下次优先练什么</h2><p class="fine">练习这些表达能力，使用新的生活场景。</p>${list(s.next_focus || ['本次没有额外学习建议。'])}</section>${s.supplement?`<section class="panel"><h2>我的补充</h2><p>${esc(s.supplement)}</p></section>`:''}<section class="panel"><h2>本次词句卡</h2><p>${count}</p><a class="text-link" href="${esc(href('terms',{session:s.id}))}">回顾本次全部词卡 ↗</a></section></aside></div>`;
}
function cardMode(args) {
  return ['speak','meaning','read'].includes(args.mode) ? args.mode : args.recall === '0' ? 'read' : 'speak';
}
function expressionCard(t, mode) {
  const question = mode === 'meaning' ? t.english : t.chinese;
  const answer = mode === 'meaning' ? t.chinese : t.english;
  const answerLabel = mode === 'meaning' ? '中文意思' : '英文表达';
  const frontLabel = question + '。点击翻面，查看' + answerLabel;
  const backLabel = answer + '。点击翻回，重新回想';
  const content = mode === 'read' ? `<h2 lang="en">${esc(t.english)}</h2><p class="chinese">${esc(t.chinese)}</p>` : `<button type="button" class="flip-control" data-answer="answer-${esc(t.id)}" data-front-label="${esc(frontLabel)}" data-back-label="${esc(backLabel)}" aria-label="${esc(frontLabel)}" aria-expanded="false" aria-controls="answer-${esc(t.id)}"><span class="flip-inner"><span class="flip-face flip-front" aria-hidden="false"><span class="flashcard-label">${mode === 'meaning' ? '想一想，它是什么意思？' : '试着用英语说出来'}</span><span class="flip-word ${mode === 'meaning' ? 'en' : 'zh'} ${question.length>60?'long':''}" lang="${mode === 'meaning' ? 'en' : 'zh-CN'}">${esc(question)}</span><span class="flip-hint">↻ 点击卡片，翻到答案</span></span><span class="flip-face flip-back" id="answer-${esc(t.id)}" aria-hidden="true" inert><span class="flashcard-label">${answerLabel}</span><span class="flip-word ${mode === 'meaning' ? 'zh' : 'en'} ${answer.length>60?'long':''}" lang="${mode === 'meaning' ? 'zh-CN' : 'en'}">${esc(answer)}</span><span class="flip-hint">↻ 点击卡片，再想一遍</span></span></span></button>`;
  return `<article class="term-card ${mode === 'read' ? '' : 'flashcard flip-item'}"><div class="meta">${tag(t.kind || t.book,'neutral')}<span>${esc(t.state_label)}</span></div>${content}<div class="card-bottom"><a href="${esc(href('sessions/'+t.source_session))}">${esc(shortDate(t.date))} · 回到这次对话</a>${t.concept_id?`<a href="${esc(href('progress/'+t.concept_id))}">查看练习历程 ↗</a>`:''}</div><details class="card-notes"><summary>用法与原话</summary><div><span class="flashcard-label">原记录中的表达</span><p>${esc(t.original || '这一条没有单独记录原话。')}</p><span class="flashcard-label">用法与观察</span><p>${esc(t.note)}</p></div></details>${readingGuide(t)}</article>`;
}
function termsPage(data, args) {
  const mode = cardMode(args), recall = mode !== 'read';
  const changeBook = name => { const next = {...args,book:name}; delete next.page; if(!name) delete next.book; return href('terms',next); };
  const scope=data.scope||{all_count:data.total,count:data.total};
  const selected=args.session;
  const switchScope=session=>href('terms',{mode,...(session?{session}:{})});
  return heading('WORDS & EXPRESSIONS','生词与表达','按课次回顾，或查看所有积累。') +
    `<section class="term-scope" aria-label="闪卡范围"><div class="scope-switch"><a class="chip ${!selected?'active':''}" ${!selected?'aria-current="page"':''} href="${esc(switchScope())}">全部积累 · ${scope.all_count}</a>${data.latest_session?`<a class="chip ${selected===data.latest_session.id?'active':''}" href="${esc(switchScope(data.latest_session.id))}">最近一次</a>`:''}</div><p><strong>${selected?'本次词句':'全部历史词句'}</strong> · ${scope.count} 张${selected?`<br>${esc(scope.session_title||'所选课次')} <a href="${esc(href('sessions/'+selected))}">查看复盘 ↗</a>`:''}</p></section>` +
    `<div class="chips"><a class="chip ${!args.book?'active':''}" href="${esc(changeBook(''))}">全部生词本</a>${data.books.map(b => `<a class="chip ${args.book===b.name?'active':''}" href="${esc(changeBook(b.name))}">${esc(b.name)} · ${b.count}</a>`).join('')}</div>` + `<details class="term-filters" ${args.q||args.from||args.to||args.state?'open':''}><summary>搜索与筛选 <span>关键词 · 日期 · 表达状态</span></summary>${filters('terms',args,data.books)}</details>` +
    `<div class="study-toolbar"><div class="study-modes" role="group" aria-label="查看方式"><button type="button" data-study-mode="speak" aria-pressed="${mode==='speak'}">练表达<span>中文 → 英文</span></button><button type="button" data-study-mode="meaning" aria-pressed="${mode==='meaning'}">认词义<span>英文 → 中文</span></button><button type="button" data-study-mode="read" aria-pressed="${mode==='read'}">中英对照<span>一起查看</span></button></div><p>${mode==='speak'?'先自己说一句，再点击卡片翻到英文答案。':mode==='meaning'?'先想一想词义，点击卡片翻到中文答案。':'中英文同时显示，方便查找和阅读。'}</p></div><div class="filter-meta"><span>${args.session?'来自所选对话 · ':''}${args.due==='1'?'建议回顾 · ':''}筛选后 ${data.total} 张 · 本页显示 ${data.items.length} 张 ${tip('表达状态','反映最近有证据的一次提示情况，不表示永久掌握或英语等级。查看详情可追溯原话和复述记录。自己翻卡不会改变学习状态。')}</span>${recall&&data.items.length?'<button type="button" class="button small" id="hide-answers">隐藏本页全部答案</button>':''}</div>`+
    (args.due==='1'?'<p class="section-note">已到建议重访日期；一次选几条就好，不是欠下的作业。<a href="'+esc(href('terms',{mode}))+'">查看全部表达</a></p>':'')+
    (data.items.length ? `<div class="terms-grid">${data.items.map(t => expressionCard(t,mode)).join('')}</div>${pager(data,'terms',args)}${recall?'<p class="boundary">翻看答案只用于自主回顾，不会被计为“已掌握”。需要确认表达能力时，回到对话里实际用一用。</p>':''}` : empty('没有找到匹配的表达','试试搜索中文意思，或重置筛选条件。','terms'));
}
function datesBefore(end, n) {
  const result = []; const d = new Date(end+'T12:00:00');
  d.setDate(d.getDate()-(n-1));
  for(let i=0;i<n;i++) { result.push([d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')); d.setDate(d.getDate()+1); }
  return result;
}
function storagePage(data) {
  return heading('YOUR LOCAL DATA','本地学习数据','学习档案属于你；网页从下面这个目录读取，Skill 提供规则和程序。')+`<section class="storage-current"><span class="eyebrow">当前学习目录</span><h2>${esc(data.location)}</h2><code id="learning-data-path">${esc(data.data_root)}</code><div class="storage-actions"><button class="button primary" type="button" data-open-folder>打开学习目录 ↗</button><button class="button" type="button" data-copy-path>复制目录路径</button></div><p>打开后可直接查看课次和数据文件；浏览和翻卡不会改变学习表现。</p>${data.embedded?'<p>这是旧版存储位置。升级或卸载前应保留数据；可让 Agent 帮你迁到独立目录。</p>':''}</section>${window.CoachStorage?.shell(data)||''}<div class="storage-grid"><section class="panel"><h2>Skill：可分享的框架</h2><p>情景与教学规则、保存和读取工具、网页样式和闪卡交互，以及通用教学示例与测试。</p><code>${esc(data.skill_root)}</code><p class="fine">你的档案和本机路径配置不属于开源包。打包发布时仍需检查实际内容。</p></section><section class="panel"><h2>学习目录：你的私人记录</h2><dl><dt>Sessions · Evidence · Archive</dt><dd>课次、精选原话与学习证据</dd><dt>profile.json</dt><dd>学习目标和练习偏好</dd><dt>Pending · Runtime</dt><dd>未完成保存与练习运行状态</dd><dt>Live/companion.sqlite3</dt><dd>近期双语转写和翻译缓存（SQLite）</dd><dt>state.json · INDEX.md</dt><dd>可由原记录重新生成的索引</dd></dl><p class="fine">长期学习记录是 Markdown 文件，内部含 JSON 数据块；保存精选片段，不是完整聊天。Codex 自身聊天记录和录屏另有存放位置。</p></section></div><section class="panel storage-options"><h2>保存和迁移</h2><div><strong>新用户默认存放在 Skill 外</strong><p>Agent 自动初始化独立目录，不需要先安装 Obsidian。已有配置继续使用，不会换成空档案。</p><code>${esc(data.default_data_root)}</code></div><div><strong>不同窗口使用同一份档案</strong><p>本机配置记录当前数据路径；路径不可用时先恢复连接，不另建空记录。</p><code>${esc(data.config_path)}</code></div><div><strong>换电脑或换知识库</strong><p>在上方下载完整备份；新电脑安装同一 Skill 后，用“恢复备份”选择空目录，或直接使用已复制的学习目录。不会自动云同步。</p></div><div><strong>本地保存 ≠ 全程离线</strong><p>学习档案保存在本机；AI 对话和翻译仍使用所连接的模型服务。</p></div></section>`;
}
async function openLearningFolder(button) {
  if(button.disabled)return;
  button.disabled=true;
  try {
    const storage=await api('/api/storage');
    const response=await fetch('/api/storage/open',{method:'POST',headers:{'Content-Type':'application/json','X-Coach-Token':storage.open_token},body:'{}',signal:AbortSignal.timeout(10000)});
    const result=await response.json();
    if(!response.ok)throw new Error(result.error||'未能打开目录');
    toast(result.message);
  } catch(error) {toast('未能打开学习目录，请到「本地学习数据」复制路径。');}
  finally {button.disabled=false;}
}
async function copyLearningPath() {
  try {await navigator.clipboard.writeText($('#learning-data-path').textContent);toast('已复制学习目录路径');}
  catch {toast('浏览器未允许复制，请选中页面上的路径复制。');}
}
const progressStages={encountered:'开始学习',supported:'有提示能完成',independent:'曾自主用出',stable:'表达已较稳定',revisit:'建议再练'};
function progressLink(c,args={}) { return href('progress/'+c.id,{return:href('progress',args)}); }
function progressRow(c,args={},summary=false) {
  return `<article class="progress-row"><div><h3><a href="${esc(progressLink(c,args))}" lang="en">${esc(c.term)}</a></h3><p>${esc(c.meaning)}</p></div><div><span class="tag ${c.needs_revisit?'neutral':c.level==='stable'?'green':''}">${esc(c.needs_revisit?'建议再练':c.level_label)}</span><p>${esc(c.change_text)}</p></div><div class="progress-row-meta"><span>${esc(c.latest_in_period)} · ${c.period_event_count} 条表现记录</span><a href="${esc(progressLink(c,args))}">查看历程 ↗</a></div></article>`;
}
function progressPage(data,args) {
  const opts=Object.entries(progressStages).map(([k,v])=>`<option value="${k}" ${args.stage===k?'selected':''}>${v}</option>`).join('');
  return `<a class="back" href="${esc(href('stats',{...(args.from?{from:args.from}:{}),...(args.to?{to:args.to}:{})}))}">← 返回学习回顾</a>`+heading('WORDS TAKING ROOT','词句进展','查找练习过的词、短语和句型，看看现在能怎样使用。')+
    `<form class="filters" data-filter="progress"><label class="search-field">查找词句或中文意思<input type="search" name="q" value="${esc(args.q||'')}" placeholder="例如 commute 或通勤"></label><label>练习开始日期<input type="date" name="from" value="${esc(args.from||'')}"></label><label>练习结束日期<input type="date" name="to" value="${esc(args.to||'')}"></label><label>练习状态<select name="stage"><option value="">全部状态</option>${opts}</select></label><div class="filter-actions"><button class="button primary">查找</button><a class="button" href="#progress">重置</a></div></form><div class="filter-meta"><span>找到 ${data.total} 个词句 ${tip('词句进展','这里收录有具体练习表现的词、短语和句型。只有收藏记录的词句仍在生词本中。缺少观察表示暂时无法判断，不表示没有学会。点击查看历程核对原话。')}</span><span>${data.as_of?'状态截至 '+esc(data.as_of):'显示最新记录的状态'}</span></div>`+
    (data.items.length?`<section class="progress-list">${data.items.map(c=>progressRow(c,args)).join('')}</section>${pager(data,'progress',args)}`:empty('还没有匹配的练习表现','可以换个筛选条件。练习中获得的帮助和后续表现，会在课后保存到这里。','progress'));
}
function progressDetail(c,args) {
  const outcomes={needs_help:'这次需要帮助',explained:'获得了解释',supported:'有提示完成',success:'成功完成'};
  const supports={model:'完整示范',keywords:'关键词提示',none:'无语言提示'};
  const back=/^#(?:progress|stats)(?:\?|$)/.test(args.return||'')?args.return:'#progress';
  return `<a class="back" href="${esc(back)}">← 返回词句进展</a>`+heading('YOUR PRACTICE STORY',c.term,c.meaning,`<a class="button" href="${esc(href('terms',{q:c.term,mode:'meaning'}))}">用闪卡回顾 ↗</a>`)+
    `<section class="panel progress-current"><div class="section-head"><h2>目前记录到的表现 ${tip('目前表现','理解、朗读和自主运用分别观察。朗读需要实际音频；翻卡不会记成成功。稳定表达需要跨日、换场景的自主使用，后来又卡住会提示再练。可在下方每次记录里核对。')}</h2>${tag(c.needs_revisit?'建议再练':c.level_label,c.level==='stable'?'green':'')}</div><p class="fine">截至 ${esc(c.last_date)} · 共 ${c.event_count} 条表现记录。下方月份筛选只影响历史列表。</p><div class="ability-grid">${Object.entries(c.dimensions).map(([key,d])=>`<div class="ability ${d.successful?'achieved':''}"><span>${esc(d.label)}</span><strong>${d.successful?({meaning:'能理解词义',reading:'能顺畅读出',use:'能自主用出'}[key]):esc(d.status)}</strong><small>${esc(d.date||'尚无相关记录')}</small></div>`).join('')}</div><p class="next-practice"><strong>下次可以试试</strong> ${esc(c.next_step)}</p></section>`+
    `<section class="milestone-strip" aria-label="已经发生的学习节点">${c.milestones.map(m=>`<a href="${esc(href('sessions/'+m.session))}"><span>${esc(m.label)}</span><strong>${esc(m.date)}</strong></a>`).join('')}</section>`+
    `<section class="panel progress-history"><div class="section-head"><div><h2>每次练习的记录</h2><p>按实际练习日期从近到远排列，每页最多 10 条。</p></div></div><form class="filters" data-filter="progress/${esc(c.id)}"><label>练习月份<select name="month"><option value="">全部月份</option>${c.months.map(m=>`<option value="${m}" ${args.month===m?'selected':''}>${m}</option>`).join('')}</select></label><button class="button">查看记录</button></form><ol class="learning-timeline">${c.history.items.map(e=>`<li><div class="timeline-date">${esc(e.date)}<span>${esc(c.dimensions[e.dimension].label)}</span></div><div><strong>${esc(outcomes[e.result])}</strong><div class="timeline-meta">${['supported','success'].includes(e.result)?`<span>${esc(supports[e.support])}</span>`:''}<a href="${esc(href('sessions/'+e.session))}">回到这次对话 ↗</a></div><details class="evidence-disclosure"><summary>${e.quote_kind==='session_note'?'查看旧课次说明与依据':'查看原话与练习说明'}</summary><blockquote>${esc(e.quote)}</blockquote><p>${esc(e.note)}</p><p class="fine">${e.quote_kind==='session_note'?'从已保存的课次说明整理，没有逐字提问记录。':'保留下来的精选学习片段。'}</p></details></div></li>`).join('')}</ol>${!c.history.items.length?empty('这个月没有记录','换一个月份，或查看全部月份。'):''}${pager(c.history,'progress/'+c.id,args)}</section>`;
}
function statsPage(data,args) {
  const lastDate=args.to||Object.keys(data.activity).at(-1)||overview.today;
  const days=datesBefore(lastDate,7),maximum=Math.max(1,...days.map(d=>data.activity[d]||0));
  const scope={...(args.from?{from:args.from}:{}),...(args.to?{to:args.to}:{})};
  return heading('LOOK BACK','学习回顾','选一段时间，看练习频率、词句变化和具体依据。', '<a class="button" href="#overview">回首页，开始练习 ↗</a>')+
    `<form class="filters" data-filter="stats"><label>开始日期<input type="date" name="from" value="${esc(args.from||'')}"></label><label>结束日期<input type="date" name="to" value="${esc(args.to||'')}"></label><div class="filter-actions"><button class="button primary">查看这段时间</button><a class="button" href="#stats">全部时间</a></div><a class="chip" href="${esc(href('stats',{from:datesBefore(overview.today,7)[0],to:overview.today}))}">最近 7 天</a><a class="chip" href="${esc(href('stats',{from:datesBefore(overview.today,30)[0],to:overview.today}))}">最近 30 天</a></form>`+
    `<div class="numbers">${metric(data.counts.sessions,'已保存对话','所选期间保存的课次数。同一天多次对话分别计数；去对话记录核对。')}${metric(data.counts.days,'练习天数','所选期间有课次记录的不同日期数量。没有记录不等于没有学习。')}${metric(data.counts.terms,'新增词句卡片','首次来源在所选期间的表达及抽取知识点。短语和包含它的整句可能各有卡片，不是掌握词汇量。到生词本查看。')}</div>`+
    `<section class="progress-summary"><div class="section-head"><div><h2>这段时间的词句变化 ${tip('词句变化','只使用所选期间及此前的记录，后来发生的表现不会混入。首次记录不等于进步；有之前表现可比较时才说明变化。这里优先显示至多 3 个词句，完整记录在词句进展。')}</h2><p>${data.progress_total?`${data.progress_total} 个词句留下了练习表现，点击查看具体历程。`:'这段时间还没有保存逐次练习表现。'}</p></div><a class="text-link" href="${esc(href('progress',scope))}">查看全部进展 ↗</a></div>${data.highlights.length?`<div class="progress-list">${data.highlights.map(c=>progressRow(c,scope,true)).join('')}</div>`:empty('下一次表现，可以从这里开始记录','已经收藏的词句仍在生词本里。之后练习时，Agent 会保存值得回顾的表现。')}</section>`+
    `<div class="stats-grid"><section class="panel"><div class="section-head"><h2>练习足迹 ${tip('练习足迹','柱高表示当天保存的对话次数。展示所选范围内、截至右侧日期的最近 7 天；点击日期查看课次。较长期间的完整记录可通过对话页查询。')}</h2><span class="fine">${esc(shortDate(days[0]))} — ${esc(shortDate(lastDate))}</span></div><div class="activity-bars">${days.map(d=>`<a class="day-column" href="${esc(href('sessions',{from:d,to:d}))}" aria-label="${esc(d)}，${data.activity[d]||0} 次对话"><strong>${data.activity[d]||'·'}</strong><span class="bar" style="height:${Math.max(3,(data.activity[d]||0)/maximum*115)}px"></span><span>${shortDate(d)}</span></a>`).join('')}</div><a class="text-link" href="${esc(href('sessions',scope))}">查看这段时间的全部对话 ↗</a></section><section class="panel"><h2>这些变化怎么读 ${tip('回顾用途','对话次数说明练习频率，词句变化说明有证据的表现；两者不是一回事。没有记录就无法判断，不自动算退步。需要核对时查看词句历程和来源课次；要开始练习回学习首页。')}</h2><p>练了多少，看左边的足迹；表达有没有变化，看上面的词句历程。</p><p>一次跟读或翻卡不代表已经掌握。没有记录的能力，暂时无法判断。</p><a class="text-link" href="${esc(href('progress',scope))}">核对具体词句的依据 ↗</a></section></div>`+
    `<section class="panel recent-observations"><div class="section-head"><h2>课次里的学习观察</h2><a class="text-link" href="${esc(href('sessions',scope))}">到对话记录查看全部 ↗</a></div>${data.observations.map(o=>`<div class="observation"><span>${esc(o.date)}</span><p>${esc(o.text)}</p><a href="${esc(href('sessions/'+o.id))}">查看这次练习 ↗</a></div>`).join('')||'<p class="fine">这段时间没有保存课次观察。</p>'}</section>`;
}

async function showTerm(id) {
  try {
    const t = await api('/api/terms/'+encodeURIComponent(id));
    $('#dialog-content').innerHTML = `${tag(t.book)}<h2 class="dialog-title" id="dialog-title" lang="en">${esc(t.english)}</h2><p class="muted">${esc(t.chinese)}</p>${speechButton(t.english)}${readingGuide(t)}<div class="dialog-section"><h3>我当时说</h3><p>${esc(t.original || '这条没有记录原话。')}</p></div><div class="dialog-section"><h3>用法与练习观察</h3><p>${esc(t.note)}</p><p class="evidence-note">${esc(t.state_label)} · 最近记录于 ${esc(t.updated)}<br>建议再聊：${esc(t.next_review)}。翻看答案不会改变这个状态。</p></div>${t.attempts?.length?`<details class="source-box"><summary>查看 ${t.attempts.length} 条练习观察</summary>${t.attempts.map(a=>`<p>${esc(a.date)} · ${esc(labels[a.prompt]||a.prompt)} · ${esc(a.note||'旧记录未保存更详细的提示过程。')}</p>`).join('')}</details>`:''}<div class="dialog-section"><h3>回到来源对话</h3><div class="source-links">${t.sources.map(s=>`<a href="${esc(href('sessions/'+s.id))}">${esc(shortDate(s.date))} · ${esc(s.title)} ↗</a>`).join('')}</div></div>`;
    $('#term-dialog').showModal();
  } catch(error) {toast(error.message);}
}
async function render() {
  const version = ++renderVersion, {path,args} = route();
  const section = path.split('/')[0];
  document.body.classList.toggle('live-view', section==='live');
  const navSection=section==='progress'?'stats':section==='review'?'sessions':section;
  $('#term-dialog').close();
  window.CoachLive?.unmount();
  main.setAttribute('aria-busy','true');
  document.querySelectorAll('[data-nav]').forEach(el => { el.classList.toggle('active',el.dataset.nav===navSection); if(el.dataset.nav===navSection) el.setAttribute('aria-current','page');else el.removeAttribute('aria-current'); });
  const names = {live:'双语伴随',overview:'学习首页',review:'本次复盘',sessions:'对话记录',terms:'生词与表达',stats:'学习回顾',progress:'词句进展',storage:'本地学习数据'};
  $('#breadcrumb').textContent = '我的学习 / '+(names[section]||'档案');
  try {
    // A saved lesson or live feed should not wait for an unrelated overview request.
    if(path==='stats'&&!overview) overview=await api('/api/overview');
    let data, markup;
    if(path==='live'){
      main.innerHTML=window.CoachLive.shell();
      data=await api('/api/live',args);markup=window.CoachLive.shell();
    }
    else if(path==='review'){
      data=await api('/api/review',args);
      if(version!==renderVersion)return;
      rememberReview(data,args);
      if(data.status==='saved'){location.replace(href('sessions/'+data.session_id));return;}
      markup=heading('YOUR PRACTICE REVIEW','本次练习复盘','完成后，这里会自动显示总结和本次词句。')+
        `<section id="review-preview" class="review-preview" aria-label="已可先看的表达建议" ${data.preview?.length?'':'hidden'}>${reviewPreview(data)}</section>`+
        `<section class="review-wait" role="status"><span class="review-indicator" aria-hidden="true"></span><h2 id="review-title">${reviewMessage(data).title}</h2><p id="review-state">${esc(reviewMessage(data).body)}</p><p class="fine">可以先看其他记录；页面上方会保留本次整理状态和返回入口。</p><button class="button" type="button" data-retry-review ${data.status==='error'?'':'hidden'}>重试本场复盘</button> <a class="button" href="#terms">先看全部词句</a></section>`;
    }
    else if(path==='overview'){data=await api('/api/overview');overview=data;markup=home(data);}
    else if(path==='sessions'){data=await api('/api/sessions',{...args,limit:10});markup=sessionsPage(data,args);}
    else if(path.startsWith('sessions/')){data=await api('/api/'+path);markup=lessonPage(data);}
    else if(path==='terms'){data=await api('/api/terms',{...args,limit:12});markup=termsPage(data,args);}
    else if(path==='stats'){data=await api('/api/stats',args);markup=statsPage(data,args);}
    else if(path==='progress'){data=await api('/api/progress',args);markup=progressPage(data,args);}
    else if(path.startsWith('progress/')){data=await api('/api/'+path,args);markup=progressDetail(data,args);}
    else if(path==='storage'){data=await api('/api/storage');markup=storagePage(data);}
    else throw new Error('这个页面不存在，请从左侧导航重新打开。');
    if(version!==renderVersion)return;
    markup=markup.replace('可用系统声音朗读表达参考；你的原话保留供对照，不参与朗读。<br>','你的原话保留供对照；书面表达建议不冒充会中原话。<br>');
    main.innerHTML=markup;
    if(data.profile){overview=data;$('#goal').textContent=data.profile.goal;}
    else if(!overview)loadGoalInBackground();
    if(path==='live')window.CoachLive.mount(data,args);else updateMeta(data);
    if(path==='storage')window.CoachStorage?.mount(data);
    paintReviewNotice();
    document.title=(names[section]||'我的学习')+' · 英语学习档案';
    window.scrollTo({top:0,behavior:'instant'});
  } catch(error) {
    if(version!==renderVersion)return;
    main.innerHTML=empty('这次没有读到记录',error.message,section==='stats'?'stats':section==='terms'?'terms':'sessions');
  } finally { if(version===renderVersion) main.setAttribute('aria-busy','false'); }
}
function reviewMessage(data) {
  if(data.status==='saved')return {title:'本次复盘已保存',body:'表达、词义和下次练习重点已经可以查看。'};
  if(data.status==='error')return {title:'复盘暂未完成',body:data.error||'已保留待办和草稿，可重试；原有学习记录不受影响。'};
  if(data.preview?.length)return {title:`已有 ${data.preview.length} 句可先看`,body:'完整复盘仍在补全词义、读法与本次观察，保存后会自动显示。'};
  if(data.status==='queued')return {title:'本地服务已接收复盘',body:'任务已排队；可以离开当前聊天，生成和保存会继续。'};
  if(data.status==='reading')return {title:'正在读取本场对话',body:'只核对这次练习的转写和相关学习记录。'};
  if(data.status==='generating')return {title:'正在生成复盘',body:'分别整理句型、生词与朗读提示。无需等待聊天 Agent 完成其他收尾。'};
  if(data.status==='checking')return {title:'正在校验复盘',body:'检查原话来源、遗漏的学习点和朗读提示，再写入档案。'};
  if(data.status==='needs_attention')return {title:'整理比预期更久',body:'本次复盘尚未完成。可以先看其他页面；这里会继续检查，保存后提供入口。'};
  if(data.status==='saving')return {title:'正在保存并核对记录',body:'正在关联词句、保存来源并检查学习档案。'};
  if(data.status==='preparing')return {title:'正在整理本次表达',body:'正在核对对话中的表达问题、词义和优先练习点。'};
  if(data.status==='practicing')return {title:'等待 Voice 关闭',body:'关闭 Voice 语音窗口后，后台才会收到结束信号并自动整理。只说“结束”而窗口仍开着时，可能尚未启动复盘。'};
  return {title:'正在等待课后整理开始',body:'语音已结束或等待结束确认；收到整理进度后会在这里更新。'};
}
function reviewPreview(data) {
  if(!data.preview?.length)return '';
  return `<h2>先看这几句</h2><p class="fine">表达建议 · 完整复盘${data.status==='error'?'暂未完成，可重试':'仍在补全'}。这里不代表已经掌握，也不会提前计入学习记录。</p>`+
    data.preview.map(x=>`<article class="review-preview-expression"><p class="fine">当时说：${esc(x.original)}</p><p class="preview-english" lang="en">${esc(x.english)}</p>${speechButton(x.english)}<p>${esc(x.chinese)}</p></article>`).join('');
}
function reviewKey(data) {return data.thread_id+'/'+data.voice_id;}
function rememberReview(data,args={}) {
  const item={...data,thread_id:data.thread_id||args.thread,voice_id:data.voice_id||args.voice};
  if(!item.thread_id||!item.voice_id)return;
  const key=reviewKey(item), prior=trackedReviews.get(key);
  trackedReviews.set(key,item);
  if(item.status==='saved' && prior && prior.status!=='saved' && !reviewSeen.has(key)) {
    reviewSeen.set(key,true);toast((item.title||'英语练习')+'的复盘已保存，可从页面上方打开。');
  }
}
function reviewLink(item) {
  return item.status==='saved' ? href('sessions/'+item.session_id) : href('review',{thread:item.thread_id,voice:item.voice_id});
}
function reviewLabel(item) {
  const stamp=item.practice_time;
  const time=stamp?new Date(stamp).toLocaleString('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}):'';
  return `${item.title || '本次英语练习'}${time?' · '+time:''}`;
}
function paintReviewNotice() {
  const panel=$('#review-notice');if(!panel)return;
  const current=route(),all=[...trackedReviews.values()].sort((a,b)=>(b.created_epoch||0)-(a.created_epoch||0));
  const live=current.path==='live'?window.CoachLive?.state?.():null;
  const exact=all.find(x=>(current.path==='review'&&x.thread_id===current.args.thread&&x.voice_id===current.args.voice)
    ||(current.path==='live'&&((current.args.run&&x.run_id===current.args.run)||(live?.voice_id&&x.thread_id===live.thread_id&&x.voice_id===live.voice_id)))
    ||(current.path==='sessions/'+x.session_id));
  const rows=all.filter(x=>x.status!=='practicing'||x===exact);
  const item=exact||rows[0];
  panel.hidden=!item||(current.path==='live'&&!exact);if(panel.hidden)return;
  if(current.path==='live') {
    panel.hidden=true;
    const link=$('#live-review');
    if(exact&&link){link.hidden=false;link.href=reviewLink(exact);link.textContent=exact.status==='saved'?'复盘已保存 ↗':exact.status==='practicing'?'本次复盘 ↗':exact.status==='error'?'复盘待重试 ↗':exact.preview?.length?'复盘可先看 ↗':'复盘整理中 ↗';link.title=reviewMessage(exact).body;}
    return;
  }
  const message=reviewMessage(item),other=rows.filter(x=>x!==item);
  const title=exact?message.title:message.title.replace('本次','最近').replace('练习进行中','另一场练习进行中');
  const markup=`<div class="review-notice-main"><div><strong>${esc(title)}</strong><span>${esc(reviewLabel(item))}</span></div><a class="button small" href="${esc(reviewLink(item))}">${item.status==='saved'?'打开复盘':'查看整理进度'} ↗</a></div>${other.length?`<details><summary>其他最近复盘（${other.length}）</summary>${other.map(x=>`<a href="${esc(reviewLink(x))}">${esc(reviewLabel(x))} · ${esc(reviewMessage(x).title.replace('本次','该次'))} ↗</a>`).join('')}</details>`:''}`;
  // Preserve focus and disclosure state on unchanged polls.
  if(panel.dataset.markup!==markup){panel.innerHTML=markup;panel.dataset.markup=markup;}
}
function applyReviewToCurrentPage(data) {
  const current=route();
  if(current.path!=='review'||current.args.thread!==data.thread_id||current.args.voice!==data.voice_id)return;
  if(data.status==='saved'){location.replace(href('sessions/'+data.session_id));return;}
  const title=$('#review-title'),state=$('#review-state');
  if(title)title.textContent=reviewMessage(data).title;
  if(state)state.textContent=reviewMessage(data).body;
  const retry=document.querySelector('[data-retry-review]');if(retry)retry.hidden=data.status!=='error';
  const preview=$('#review-preview');
  if(preview){const markup=reviewPreview(data);preview.hidden=!markup;if(preview.dataset.markup!==markup){preview.innerHTML=markup;preview.dataset.markup=markup;}}
}
async function refreshReviews() {
  if(reviewPolling)return;
  reviewPolling=true;
  try {
    if(document.hidden)return;
    const data=await api('/api/reviews');
    for(const item of data.items||[])rememberReview(item);
    const current=route();
    if(current.path==='review' && !(data.items||[]).some(x=>x.thread_id===current.args.thread&&x.voice_id===current.args.voice)) {
      rememberReview(await api('/api/review',current.args),current.args);
    }
    paintReviewNotice();
    for(const item of trackedReviews.values())applyReviewToCurrentPage(item);
  } catch(error) {
    const current=route(), state=$('#review-state');
    if(current.path==='review'&&state)state.textContent='暂时未能检查保存结果，页面会继续重试。'+error.message;
  } finally {
    reviewPolling=false;
    const pending=[...trackedReviews.values()].some(x=>['waiting','queued','reading','generating','checking','preparing','saving'].includes(x.status));
    scheduleReviews(pending?1500:5000);
  }
}
function scheduleReviews(delay=1500) {clearTimeout(reviewTimer);reviewTimer=setTimeout(refreshReviews,delay);}
document.addEventListener('visibilitychange',()=>{if(!document.hidden)scheduleReviews(0);});
document.addEventListener('submit', event => {
  const form=event.target.closest('[data-filter]'); if(!form)return;event.preventDefault();
  const current=route(), args={...current.args};delete args.page;delete args.progress_page;delete args.observation_page;
  for(const [key,value] of new FormData(form)){if(value)args[key]=value;else delete args[key];}
  if(args.from&&args.to&&args.from>args.to){toast('开始日期不能晚于结束日期。');return;}
  const next=href(form.dataset.filter,args);if(location.hash===next)render();else location.hash=next;
});
document.addEventListener('click', event => {
  if(event.target.closest('.skip')){event.preventDefault();main.focus();main.scrollIntoView();return;}
  const menu=$('#live-details');if(menu?.open&&!event.target.closest('#live-details'))menu.open=false;
  const help=event.target.closest('.help>button');
  if(help){const parent=help.parentElement;parent.classList.toggle('open');help.setAttribute('aria-expanded',parent.classList.contains('open'));return;}
  if(!event.target.closest('.help'))document.querySelectorAll('.help.open').forEach(el=>{el.classList.remove('open');$('button',el).setAttribute('aria-expanded','false');});
  const retry=event.target.closest('[data-retry-review]');if(retry){retryReview(retry);return;}
  const folder=event.target.closest('[data-open-folder]');if(folder){openLearningFolder(folder);return;}
  if(event.target.closest('[data-copy-path]')){copyLearningPath();return;}
  const page=event.target.closest('[data-page]'); if(page&&!page.disabled){const r=route();location.hash=href(r.path,{...r.args,page:page.dataset.page});}
  const term=event.target.closest('[data-term]');if(term)showTerm(term.dataset.term);
  const modeButton=event.target.closest('[data-study-mode]');
  if(modeButton){const r=route(),args={...r.args,mode:modeButton.dataset.studyMode};delete args.recall;const next=href('terms',args);if(location.hash!==next)location.hash=next;}
  const reveal=event.target.closest('[data-answer]');
  if(reveal){setAnswer(reveal,reveal.getAttribute('aria-expanded')!=='true');}
  if(event.target.closest('#hide-answers')){document.querySelectorAll('[data-answer]').forEach(button=>setAnswer(button,false));document.querySelectorAll('.reading-guide[open],.card-notes[open]').forEach(el=>{el.open=false;});toast('本页答案和提示已隐藏，可以再想一遍');}
});
const flipJobs = new WeakMap();
async function setAnswer(button, show) {
  const answer=document.getElementById(button.dataset.answer);
  if(!answer)return;
  const previous=flipJobs.get(button);previous?.animation?.cancel();
  const job={};flipJobs.set(button,job);
  const inner=button.querySelector('.flip-inner');
  const front=button.querySelector('.flip-front');
  button.setAttribute('aria-expanded',String(show));
  button.setAttribute('aria-label',show?button.dataset.backLabel:button.dataset.frontLabel);
  const swap=()=>{front.setAttribute('aria-hidden',String(show));front.inert=show;answer.setAttribute('aria-hidden',String(!show));answer.inert=!show;};
  if(!inner.animate||matchMedia('(prefers-reduced-motion: reduce)').matches){swap();return;}
  // The card closes to a positive width, changes faces, then opens. Text never
  // crosses a negative transform, including rapid reversals and browser compositing.
  job.animation=inner.animate([{transform:'scaleX(1)'},{transform:'scaleX(.02)'}],{duration:110,easing:'ease-in',fill:'forwards'});
  try{await job.animation.finished;}catch{return;}
  if(flipJobs.get(button)!==job)return;
  swap();job.animation.cancel();
  job.animation=inner.animate([{transform:'scaleX(.02)'},{transform:'scaleX(1)'}],{duration:130,easing:'ease-out'});
  try{await job.animation.finished;}catch{}
  if(flipJobs.get(button)===job)flipJobs.delete(button);
}
$('#close-dialog').addEventListener('click',()=>$('#term-dialog').close());
$('#term-dialog').addEventListener('click',e=>{if(e.target===$('#term-dialog')){const rect=e.target.getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)e.target.close();}});
$('#refresh').addEventListener('click',async()=>{overview=null;await render();if(!main.textContent.includes('这次没有读到记录'))toast('已读取最新保存的学习记录');});
window.addEventListener('hashchange',render);
render();
scheduleReviews();

async function retryReview(button) {
  if(button.disabled)return;button.disabled=true;
  try {
    const {args}=route(),storage=await api('/api/storage');
    const response=await fetch('/api/review/retry',{method:'POST',headers:{'Content-Type':'application/json','X-Coach-Token':storage.open_token},body:JSON.stringify({thread:args.thread,voice:args.voice})});
    const result=await response.json();if(!response.ok)throw new Error(result.error);
    toast('本地复盘任务已接收。');scheduleReviews(0);
  }catch(error){toast(error.message);}finally{button.disabled=false;}
}

document.addEventListener('keydown',event=>{if(event.key==='Escape'){const menu=$('#live-details');if(menu?.open){menu.open=false;$('summary',menu)?.focus();}}});

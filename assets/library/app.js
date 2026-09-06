'use strict';
const $ = (s, root = document) => root.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const main = $('#content');
const labels = {not_tested:'尚未尝试',source_text:'看原句说出',keywords:'借关键词说出',independent:'曾独立说出',transfer:'曾换场景使用'};
const bookEnglish = {'旅行出行':'Out & about','宠物咨询':'Care & ask','日常聊天':'Everyday life'};
let overview, overviewLoading, renderVersion = 0, toastTimer, reviewTimer;
const href = (path, args = {}) => '#' + path + (Object.keys(args).length ? '?' + new URLSearchParams(args) : '');
const route = () => { const [path, query = ''] = location.hash.slice(1).split('?'); return {path:path || 'overview', args:Object.fromEntries(new URLSearchParams(query))}; };
const shortDate = d => d ? d.slice(5).replace('-', '.') : '';
const fullDate = d => d ? `${d.slice(0,4)} 年 ${Number(d.slice(5,7))} 月 ${Number(d.slice(8,10))} 日` : '';
const tag = (text, type = '') => `<span class="tag ${type}">${esc(text)}</span>`;
const tip = (name, body) => `<span class="help"><button type="button" aria-label="${esc(name)}说明" aria-expanded="false">?</button><span class="help-body" role="tooltip">${esc(body)}</span></span>`;
const list = items => items.map(x => `<p>${esc(x)}</p>`).join('');
const empty = (title, body, path) => `<div class="empty"><strong>${esc(title)}</strong>${esc(body)}${path ? `<br><a class="button" href="${esc(href(path))}">查看全部记录</a>` : ''}</div>`;
const heading = (kicker, title, description, action = '') => `<div class="page-heading"><div><span class="eyebrow">${esc(kicker)}</span><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${action}</div>`;
const metric = (count, name, description) => `<div class="metric"><strong>${count}</strong><span>${name}${description ? tip(name, description) : ''}</span></div>`;
const sourceDate = s => `<div class="date-stamp">${esc(s.date.slice(0,4))}<strong>${shortDate(s.date)}</strong></div>`;

async function api(path, args = {}) {
  const response = await fetch(path + (Object.keys(args).length ? '?' + new URLSearchParams(args) : ''), {cache:'no-store'});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '读取失败，请刷新重试。');
  return result;
}
function toast(text) {
  $('#toast').textContent = text; $('#toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 2600);
}
function updateMeta(data) {
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
  const {counts, latest, books} = data;
  const feature = latest?.excerpts?.[0];
  return heading('MY SPEAKING JOURNAL', '我的学习档案', '把练习留下来，让下一次表达更自然。') +
    `<div class="numbers">${metric(counts.sessions,'已保存对话','按已保存的课次去重计数，不是所有聊天窗口数。点击对话记录核对课次；缺少的练习不会被估算进去。')}${metric(counts.terms,'词句卡片','表达和从整句抽取的知识点各有一张卡片，不等于背会的单词数。去生词与表达查看原话、用法和提示情况。')}${metric(counts.days,'练习天数','按课次的实际练习日期去重。同一天的多次对话算一天，补录日期不算新练习。')}${metric(counts.books,'主题生词本','按现有课次主题自动分组，方便查找。它们共用同一份表达记录，不额外复制内容。')}</div>` +
    (latest ? `<section class="hero" aria-label="最近一次练习"><div class="hero-quote"><span class="eyebrow">A PHRASE FROM YOUR PRACTICE · ${esc(shortDate(latest.date))}</span><blockquote lang="en">${esc(feature?.english || latest.title)}</blockquote><p>${esc(feature?.chinese || '')}</p></div><div class="hero-summary">${tag('最近一次 · ' + latest.book)}<h2>${esc(latest.title)}</h2><p>${esc(latest.summary)}</p><a class="button primary" href="${esc(href('sessions/' + latest.id))}">查看这次总结 <span aria-hidden="true">↗</span></a></div></section>` : empty('第一段练习，还在等你','对 Agent 说「练英语」，保存后这里就会出现你的第一篇记录。')) +
    `<div class="home-grid"><section><div class="section-head"><h2>最近聊过什么</h2><a class="text-link" href="#sessions">全部记录 ↗</a></div><div class="panel">${data.recent.map(s => `<a class="session-link" href="${esc(href('sessions/' + s.id))}">${sourceDate(s)}<div><h3>${esc(s.title)}</h3><p>${esc(s.book)} · ${s.expression_count} 条表达</p></div><span class="arrow">↗</span></a>`).join('') || '<p class="muted">还没有课次记录。</p>'}</div><div class="practice-note"><strong>下一场从头开始</strong><p>AI 会结合学习背景选择新场景，先介绍地点、角色和目标，再开始英语对话。</p></div></section><section><div class="section-head"><h2>我的生词本</h2><a class="text-link" href="#terms">全部表达 ↗</a></div><div class="books">${books.map(b => `<a class="book" href="${esc(href('terms',{book:b.name}))}"><span class="book-en" lang="en">${esc(bookEnglish[b.name] || b.name)}</span><h3>${esc(b.name)}</h3><p>${b.count} 条表达 · ${b.sessions} 次对话</p></a>`).join('')}</div><p class="section-note">根据已有练习主题整理，单词、短语和整句一起收录。</p><div class="quick-review"><div class="section-head"><div><h2>只想回顾两分钟</h2><p>先看中文，想一想怎么说。</p></div><a class="text-link" href="${esc(href('terms',{recall:'1',due:'1'}))}">开始回顾 ↗</a></div>${data.review_terms.map(t => `<a class="review-small" href="${esc(href('terms',{q:t.chinese,mode:'speak'}))}">${esc(t.chinese)}<span>${esc(t.book)} · ${esc(t.state_label)}</span></a>`).join('') || '<p class="fine">目前没有到建议复习日期的表达，可以从生词本选一句回顾。</p>'}</div></section></div>`;
}
function filters(path, args, books) {
  const terms = path === 'terms';
  return `<form class="filters" data-filter="${path}"><label class="search-field">${terms ? '查找生词、句子或中文意思' : '查找主题、原话或总结'}<input name="q" type="search" value="${esc(args.q || '')}" placeholder="输入关键词，按回车搜索" autocomplete="off"></label><label>从哪天<input type="date" name="from" aria-label="开始日期" value="${esc(args.from || '')}"></label><label>到哪天<input type="date" name="to" aria-label="结束日期" value="${esc(args.to || '')}"></label>${terms ? `<label>表达状态<select name="state"><option value="">全部状态</option>${Object.entries(labels).map(([v,t]) => `<option value="${v}" ${args.state===v?'selected':''}>${t}</option>`).join('')}</select></label>` : `<label>主题<select name="book"><option value="">全部主题</option>${books.map(b => `<option value="${esc(b.name)}" ${args.book===b.name?'selected':''}>${esc(b.name)}</option>`).join('')}</select></label>`}<div class="filter-actions"><button class="button primary" type="submit">搜索</button><a class="button" href="${esc(href(path, path==='terms' ? {mode:cardMode(args)} : {}))}">重置</a></div></form>`;
}
function pager(data, path, args) {
  return `<div class="pager"><button class="button small" data-page="${data.page-1}" ${data.page<=1?'disabled':''}>上一页</button><span>第 ${data.page} / ${data.pages} 页 · 共 ${data.total} 条</span><button class="button small" data-page="${data.page+1}" ${data.page>=data.pages?'disabled':''}>下一页</button></div>`;
}
function sessionsPage(data, args) {
  return heading('CONVERSATIONS','对话记录','按日期回看每次练习：聊了什么、怎么表达、下次接着练什么。') + filters('sessions',args,data.books) + `<div class="filter-meta"><span>找到 ${data.total} 次对话</span><span>按练习日期从近到远排列</span></div>` +
    (data.items.length ? `<div class="records">${data.items.map(s => `<article class="record-card">${sourceDate(s)}<div><h2><a href="${esc(href('sessions/'+s.id))}">${esc(s.title)}</a></h2><div class="meta">${tag(s.book)}<span>${s.expression_count} 条表达</span>${s.recovered_on?'<span>历史补录</span>':''}</div><p>${esc(s.summary)}</p></div><div class="action"><a class="text-link" href="${esc(href('sessions/'+s.id))}">查看记录 ↗</a></div></article>`).join('')}</div>${pager(data,'sessions',args)}` : empty('没有找到匹配的对话','试试换个关键词，或扩大日期范围。','sessions'));
}
function lessonPage(s) {
  return `<a class="back" href="#sessions">← 返回对话记录</a><div class="lesson-heading"><span class="eyebrow">${esc(fullDate(s.date))}</span><h1>${esc(s.title)}</h1><div class="meta">${tag(s.book)}<span>${s.expression_count} 条表达</span>${tag('精选练习片段','neutral')}${s.recovered_on?'<span>补录于 '+esc(s.recovered_on)+'</span>':''}</div></div><div class="lesson-layout"><div><section class="lesson-summary"><h2>这次聊了什么</h2><p>${esc(s.summary || '本次没有单独保存摘要。')}</p></section><div class="section-head"><h2>我说过的话</h2><span class="fine">原话与复盘要点</span></div><div>${s.excerpts.map(e => `<article class="excerpt"><span class="small-label">我当时说</span><p class="original" lang="en">${esc(e.original || '这条没有记录原话。')}</p><span class="small-label">${e.original?.trim()===e.english.trim()?'这句话可以继续用':'表达参考'}</span><p class="model" lang="en">${esc(e.english)}</p><p class="chinese">${esc(e.chinese)}</p><p class="evidence-note">${esc(e.note)}</p></article>`).join('') || empty('这次未保存逐句片段','上方保留了本次总结。')}</div><details class="source-box"><summary>记录来源与完整性</summary><p>${esc(s.evidence_note || '此页仅展示当时保留下来的学习记录。')}</p><p>这些是精选片段，不是完整聊天逐字稿。表达建议也不冒充逐字保存的 AI 原话。</p><p>课次编号：${esc(s.id)}</p>${s.source_ids?.length?'<p>来源：'+esc(s.source_ids.join(' · '))+'</p>':''}<a href="/records/${esc(s.id)}.md" target="_blank" rel="noopener">查看原始 Markdown 记录 ↗</a></details></div><aside class="lesson-aside"><section class="panel"><h2>这次的学习观察</h2>${list(s.progress || ['没有额外保存观察。'])}</section><section class="panel"><h2>当时的学习建议</h2><p class="fine">以下为历史记录，用于回顾，不续演旧情节。</p>${list(s.next_focus || ['本次没有额外学习建议。'])}</section>${s.supplement?`<section class="panel"><h2>我的补充</h2><p>${esc(s.supplement)}</p></section>`:''}<section class="panel"><h2>收进生词本了</h2><p>${esc(s.book)} · ${s.expression_count} 条表达</p><a class="text-link" href="${esc(href('terms',{session:s.id}))}">回顾这些表达 ↗</a></section></aside></div>`;
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
  return `<article class="term-card ${mode === 'read' ? '' : 'flashcard flip-item'}"><div class="meta">${tag(t.kind || t.book,'neutral')}<span>${esc(t.state_label)}</span></div>${content}<div class="card-bottom"><a href="${esc(href('sessions/'+t.source_session))}">${esc(shortDate(t.date))} · 回到这次对话</a>${t.concept_id?`<a href="${esc(href('progress/'+t.concept_id))}">查看练习历程 ↗</a>`:''}</div><details class="card-notes"><summary>用法与原话</summary><div><span class="flashcard-label">原记录中的表达</span><p>${esc(t.original || '这一条没有单独记录原话。')}</p><span class="flashcard-label">用法与观察</span><p>${esc(t.note)}</p></div></details></article>`;
}
function termsPage(data, args) {
  const mode = cardMode(args), recall = mode !== 'read';
  const changeBook = name => { const next = {...args,book:name}; delete next.page; if(!name) delete next.book; return href('terms',next); };
  return heading('WORDS & EXPRESSIONS','生词与表达','先想一想，再揭晓答案。把记下的词句，变成自己会说的话。') +
    `<div class="chips"><a class="chip ${!args.book?'active':''}" href="${esc(changeBook(''))}">全部生词本</a>${data.books.map(b => `<a class="chip ${args.book===b.name?'active':''}" href="${esc(changeBook(b.name))}">${esc(b.name)} · ${b.count}</a>`).join('')}</div>` + `<details class="term-filters" ${args.q||args.from||args.to||args.state?'open':''}><summary>搜索与筛选 <span>关键词 · 日期 · 表达状态</span></summary>${filters('terms',args,data.books)}</details>` +
    `<div class="study-toolbar"><div class="study-modes" role="group" aria-label="查看方式"><button type="button" data-study-mode="speak" aria-pressed="${mode==='speak'}">练表达<span>中文 → 英文</span></button><button type="button" data-study-mode="meaning" aria-pressed="${mode==='meaning'}">认词义<span>英文 → 中文</span></button><button type="button" data-study-mode="read" aria-pressed="${mode==='read'}">中英对照<span>一起查看</span></button></div><p>${mode==='speak'?'先自己说一句，点击卡片翻到英文答案。':mode==='meaning'?'先想一想词义，点击卡片翻到中文答案。':'中英文同时显示，方便查找和阅读。'}</p></div><div class="filter-meta"><span>${args.session?'来自所选对话 · ':''}${args.due==='1'?'建议回顾 · ':''}找到 ${data.total} 条表达 ${tip('表达状态','反映最近有证据的一次提示情况，不表示永久掌握或英语等级。查看详情可追溯原话和复述记录。自己翻卡不会改变学习状态。')}</span>${recall&&data.items.length?'<button type="button" class="button small" id="hide-answers">隐藏本页全部答案</button>':''}</div>`+
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
  return heading('YOUR LOCAL ARCHIVE','档案与存储','页面随 Skill 提供，练习记录属于你。一个数据位置，供不同窗口继续使用。')+`<section class="storage-current"><span class="eyebrow">当前正在读取</span><h2>${esc(data.location)}</h2><code>${esc(data.data_root)}</code><p>这是学习档案的实际数据目录。当前页面的课次、词句和进步记录都来自这里。</p></section><div class="storage-grid"><section class="panel"><h2>Skill 里放什么</h2><p>对话规则、保存与读取工具，以及 HTML、样式和闪卡交互。</p><code>${esc(data.skill_root)}</code><p class="fine">这些是程序文件，升级时可以替换；分发给其他用户时不附带你的学习数据。</p></section><section class="panel"><h2>数据目录里放什么</h2><dl><dt>Sessions</dt><dd>课次总结、精选原话和当次知识点证据</dd><dt>Evidence</dt><dd>从旧记录提取的、可追溯的知识点证据</dd><dt>Pending</dt><dd>尚未完成保存的恢复记录</dd><dt>profile.json</dt><dd>目标、语言和练习偏好</dd><dt>state.json</dt><dd>可重建的汇总索引</dd></dl><p class="fine">Voice 默认只沉淀学习所需片段；未取得原始音频时，不声称保存了录音。</p></section></div><section class="panel storage-options"><h2>新用户的两种存放方式</h2><div><strong>没有指定路径</strong><p>Agent 自动在 Skill 内的独立 data 目录初始化，不需要先安装 Obsidian。</p><code>${esc(data.default_data_root)}</code><p class="fine">data 是私人记录。写入后会在 Skill 外保存一份恢复副本；更新、打包或卸载前，Agent 仍需核对并保留数据。第三方安装器、手动删除整个 .codex 或磁盘损坏不受此保护。</p></div><div><strong>已有知识库或 Obsidian</strong><p>告诉 Agent 目标文件夹即可。Agent 先复制已有数据、校验完整性，再切换路径，保留原目录；不会把两份档案同时当作当前数据。</p></div><div><strong>跨窗口如何找到同一份档案</strong><p>每次练习前，Agent 读取本机的路径配置，再恢复最近的课次和知识点。配置的路径不可用时会明确说明，不另外创建一份空档案。</p><code>${esc(data.config_path)}</code><p class="fine">换电脑时需要一起迁移学习数据，并在新电脑重新设置路径。页面不会自动同步到云端。</p></div></section>`;
}
const progressStages={encountered:'开始学习',supported:'有提示能完成',independent:'曾自主用出',stable:'表达已较稳定',revisit:'建议再练'};
function progressLink(c,args={}) { return href('progress/'+c.id,{return:href('progress',args)}); }
function progressRow(c,args={},summary=false) {
  return `<article class="progress-row"><div><h3><a href="${esc(progressLink(c,args))}" lang="en">${esc(c.term)}</a></h3><p>${esc(c.meaning)}</p></div><div><span class="tag ${c.needs_revisit?'neutral':c.level==='stable'?'green':''}">${esc(c.needs_revisit?'建议再练':c.level_label)}</span><p>${esc(c.change_text)}</p></div><div class="progress-row-meta"><span>${esc(c.latest_in_period)} · ${c.period_event_count} 条表现记录</span><a href="${esc(progressLink(c,args))}">查看历程 ↗</a></div></article>`;
}
function progressPage(data,args) {
  const opts=Object.entries(progressStages).map(([k,v])=>`<option value="${k}" ${args.stage===k?'selected':''}>${v}</option>`).join('');
  return `<a class="back" href="${esc(href('stats',{...(args.from?{from:args.from}:{}),...(args.to?{to:args.to}:{})}))}">← 返回统计回顾</a>`+heading('WORDS TAKING ROOT','词句进展','查找练习过的词、短语和句型，看看现在能怎样使用。')+
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
  return heading('REFLECT & CONTINUE','统计回顾','看看这段时间练了什么，有哪些变化，下次可以接着练什么。')+
    `<form class="filters" data-filter="stats"><label>开始日期<input type="date" name="from" value="${esc(args.from||'')}"></label><label>结束日期<input type="date" name="to" value="${esc(args.to||'')}"></label><div class="filter-actions"><button class="button primary">查看这段时间</button><a class="button" href="#stats">全部时间</a></div><a class="chip" href="${esc(href('stats',{from:datesBefore(overview.today,7)[0],to:overview.today}))}">最近 7 天</a><a class="chip" href="${esc(href('stats',{from:datesBefore(overview.today,30)[0],to:overview.today}))}">最近 30 天</a></form>`+
    `<div class="numbers">${metric(data.counts.sessions,'已保存对话','所选期间保存的课次数。同一天多次对话分别计数；去对话记录核对。')}${metric(data.counts.days,'练习天数','所选期间有课次记录的不同日期数量。没有记录不等于没有学习。')}${metric(data.counts.terms,'新增词句卡片','首次来源在所选期间的表达及抽取知识点。短语和包含它的整句可能各有卡片，不是掌握词汇量。到生词本查看。')}</div>`+
    `<section class="progress-summary"><div class="section-head"><div><h2>这段时间的词句变化 ${tip('词句变化','只使用所选期间及此前的记录，后来发生的表现不会混入。首次记录不等于进步；有之前表现可比较时才说明变化。这里优先显示至多 3 个词句，完整记录在词句进展。')}</h2><p>${data.progress_total?`${data.progress_total} 个词句留下了练习表现，点击查看具体历程。`:'这段时间还没有保存逐次练习表现。'}</p></div><a class="text-link" href="${esc(href('progress',scope))}">查看全部进展 ↗</a></div>${data.highlights.length?`<div class="progress-list">${data.highlights.map(c=>progressRow(c,scope,true)).join('')}</div>`:empty('下一次表现，可以从这里开始记录','已经收藏的词句仍在生词本里。之后练习时，Agent 会保存值得回顾的表现。')}</section>`+
    `<div class="stats-grid"><section class="panel"><div class="section-head"><h2>练习足迹 ${tip('练习足迹','柱高表示当天保存的对话次数。展示所选范围内、截至右侧日期的最近 7 天；点击日期查看课次。较长期间的完整记录可通过对话页查询。')}</h2><span class="fine">${esc(shortDate(days[0]))} — ${esc(shortDate(lastDate))}</span></div><div class="activity-bars">${days.map(d=>`<a class="day-column" href="${esc(href('sessions',{from:d,to:d}))}" aria-label="${esc(d)}，${data.activity[d]||0} 次对话"><strong>${data.activity[d]||'·'}</strong><span class="bar" style="height:${Math.max(3,(data.activity[d]||0)/maximum*115)}px"></span><span>${shortDate(d)}</span></a>`).join('')}</div><a class="text-link" href="${esc(href('sessions',scope))}">查看这段时间的全部对话 ↗</a></section><section class="panel"><h2>下次可以回顾</h2><p class="fine">从本期练过的内容里选两条就好。</p>${data.review.map(c=>`<div class="review-suggestion"><a href="${esc(progressLink(c,scope))}" lang="en">${esc(c.term)}</a><p>${esc(c.next_step)}</p></div>`).join('')||'<p>可以从生词本选一句，再回到对话里实际用一用。</p>'}<a class="text-link" href="#terms">打开生词本 ↗</a></section></div>`+
    `<section class="panel recent-observations"><div class="section-head"><h2>课次里的学习观察</h2><a class="text-link" href="${esc(href('sessions',scope))}">到对话记录查看全部 ↗</a></div>${data.observations.map(o=>`<div class="observation"><span>${esc(o.date)}</span><p>${esc(o.text)}</p><a href="${esc(href('sessions/'+o.id))}">查看这次练习 ↗</a></div>`).join('')||'<p class="fine">这段时间没有保存课次观察。</p>'}</section>`;
}

async function showTerm(id) {
  try {
    const t = await api('/api/terms/'+encodeURIComponent(id));
    $('#dialog-content').innerHTML = `${tag(t.book)}<h2 class="dialog-title" id="dialog-title" lang="en">${esc(t.english)}</h2><p class="muted">${esc(t.chinese)}</p><div class="dialog-section"><h3>我当时说</h3><p>${esc(t.original || '这条没有记录原话。')}</p></div><div class="dialog-section"><h3>用法与练习观察</h3><p>${esc(t.note)}</p><p class="evidence-note">${esc(t.state_label)} · 最近记录于 ${esc(t.updated)}<br>建议再聊：${esc(t.next_review)}。翻看答案不会改变这个状态。</p></div>${t.attempts?.length?`<details class="source-box"><summary>查看 ${t.attempts.length} 条练习观察</summary>${t.attempts.map(a=>`<p>${esc(a.date)} · ${esc(labels[a.prompt]||a.prompt)} · ${esc(a.note||'旧记录未保存更详细的提示过程。')}</p>`).join('')}</details>`:''}<div class="dialog-section"><h3>回到来源对话</h3><div class="source-links">${t.sources.map(s=>`<a href="${esc(href('sessions/'+s.id))}">${esc(shortDate(s.date))} · ${esc(s.title)} ↗</a>`).join('')}</div></div>`;
    $('#term-dialog').showModal();
  } catch(error) {toast(error.message);}
}
async function render() {
  const version = ++renderVersion, {path,args} = route();
  clearTimeout(reviewTimer);
  const section = path.split('/')[0];
  const navSection=section==='progress'?'stats':section==='review'?'sessions':section;
  $('#term-dialog').close();
  window.CoachLive?.unmount();
  main.setAttribute('aria-busy','true');
  document.querySelectorAll('[data-nav]').forEach(el => { el.classList.toggle('active',el.dataset.nav===navSection); if(el.dataset.nav===navSection) el.setAttribute('aria-current','page');else el.removeAttribute('aria-current'); });
  const names = {live:'双语伴随',overview:'概览',review:'本次复盘',sessions:'对话记录',terms:'生词与表达',stats:'统计回顾',progress:'词句进展',storage:'档案与存储'};
  $('#breadcrumb').textContent = '我的学习 / '+(names[section]||'档案');
  try {
    // A saved lesson or live feed should not wait for an unrelated overview request.
    if(path==='stats'&&!overview) overview=await api('/api/overview');
    let data, markup;
    if(path==='live'){data=await api('/api/live',args);markup=window.CoachLive.shell();}
    else if(path==='review'){
      data=await api('/api/review',args);
      if(version!==renderVersion)return;
      if(data.status==='saved'){location.replace(href('sessions/'+data.session_id));return;}
      markup=heading('YOUR PRACTICE REVIEW','本次复盘','保存后会自动显示在这里。')+
        '<div class="empty" role="status"><strong>这次复盘尚未保存</strong><p>原话、表达建议和练习观察保存后，页面会自动更新，无需手动刷新。</p><p class="fine" id="review-state">正在等待本次记录。页面本身不会生成或保存复盘。</p></div>';
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
    main.innerHTML=markup;
    if(data.profile){overview=data;$('#goal').textContent=data.profile.goal;}
    else if(!overview)loadGoalInBackground();
    if(path==='live')window.CoachLive.mount(data,args);else updateMeta(data);
    if(path==='review')watchReview(version,args,Date.now()+300000);
    document.title=(names[section]||'我的学习')+' · 英语学习档案';
    window.scrollTo({top:0,behavior:'instant'});
  } catch(error) {
    if(version!==renderVersion)return;
    main.innerHTML=empty('这次没有读到记录',error.message,section==='stats'?'stats':section==='terms'?'terms':'sessions');
  } finally { if(version===renderVersion) main.setAttribute('aria-busy','false'); }
}
function watchReview(version,args,deadline) {
  reviewTimer=setTimeout(async()=>{
    if(version!==renderVersion)return;
    if(Date.now()>=deadline){$('#review-state').textContent='暂未收到保存的复盘。可以稍后点击“刷新记录”；若仍未出现，请让 Agent 检查保存结果。';return;}
    if(!document.hidden){
      try {
        const data=await api('/api/review',args);
        if(version!==renderVersion)return;
        if(data.status==='saved'){location.replace(href('sessions/'+data.session_id));return;}
        $('#review-state').textContent='正在等待本次记录。页面本身不会生成或保存复盘。';
      } catch(error) {
        if(version!==renderVersion)return;
        $('#review-state').textContent='暂时未能检查保存结果：'+error.message;
      }
    }
    if(version===renderVersion)watchReview(version,args,deadline);
  },1000);
}
document.addEventListener('submit', event => {
  const form=event.target.closest('[data-filter]'); if(!form)return;event.preventDefault();
  const current=route(), args={...current.args};delete args.page;delete args.progress_page;delete args.observation_page;
  for(const [key,value] of new FormData(form)){if(value)args[key]=value;else delete args[key];}
  if(args.from&&args.to&&args.from>args.to){toast('开始日期不能晚于结束日期。');return;}
  const next=href(form.dataset.filter,args);if(location.hash===next)render();else location.hash=next;
});
document.addEventListener('click', event => {
  if(event.target.closest('.skip')){event.preventDefault();main.focus();main.scrollIntoView();return;}
  const help=event.target.closest('.help>button');
  if(help){const parent=help.parentElement;parent.classList.toggle('open');help.setAttribute('aria-expanded',parent.classList.contains('open'));return;}
  if(!event.target.closest('.help'))document.querySelectorAll('.help.open').forEach(el=>{el.classList.remove('open');$('button',el).setAttribute('aria-expanded','false');});
  const page=event.target.closest('[data-page]'); if(page&&!page.disabled){const r=route();location.hash=href(r.path,{...r.args,page:page.dataset.page});}
  const term=event.target.closest('[data-term]');if(term)showTerm(term.dataset.term);
  const modeButton=event.target.closest('[data-study-mode]');
  if(modeButton){const r=route(),args={...r.args,mode:modeButton.dataset.studyMode};delete args.recall;const next=href('terms',args);if(location.hash!==next)location.hash=next;}
  const reveal=event.target.closest('[data-answer]');
  if(reveal){setAnswer(reveal,reveal.getAttribute('aria-expanded')!=='true');}
  if(event.target.closest('#hide-answers')){document.querySelectorAll('[data-answer]').forEach(button=>setAnswer(button,false));toast('本页答案已隐藏，可以再想一遍');}
});
function setAnswer(button, show) {
  const answer=document.getElementById(button.dataset.answer);
  if(!answer)return;
  button.setAttribute('aria-expanded',String(show));
  button.setAttribute('aria-label',show?button.dataset.backLabel:button.dataset.frontLabel);
  button.classList.toggle('is-flipped',show);
  const front=button.querySelector('.flip-front');
  front.setAttribute('aria-hidden',String(show)); front.inert=show;
  answer.setAttribute('aria-hidden',String(!show)); answer.inert=!show;
}
$('#close-dialog').addEventListener('click',()=>$('#term-dialog').close());
$('#term-dialog').addEventListener('click',e=>{if(e.target===$('#term-dialog')){const rect=e.target.getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)e.target.close();}});
$('#refresh').addEventListener('click',async()=>{overview=null;await render();if(!main.textContent.includes('这次没有读到记录'))toast('已读取最新保存的学习记录');});
window.addEventListener('hashchange',render);
render();

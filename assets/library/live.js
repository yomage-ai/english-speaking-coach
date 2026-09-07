'use strict';
window.CoachLive = (() => {
  let request, timer, resizeObserver, generation = 0, options = {}, current, follow = true, shownRun, fingerprint = '';
  let chinese = localStorage.getItem('coach-live-chinese') !== 'on-demand';
  const e = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const get = s => document.querySelector(s);
  const stamp = s => s ? new Date(s).toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—';
  const statusNames = {starting:'正在连接翻译',translating:'正在补充中文',recovering:'正在恢复已结束的对话',draining:'正在处理最后几句',waiting_voice:'字幕已就绪 · 等待本次 Voice',waiting_transcript:'正在等待新转写',ended:'本次伴随已结束',expired:'已暂停伴随',error:'伴随需要检查'};
  function shell() {
    return `<div class="page-heading"><div><span class="eyebrow">LISTEN, SPEAK & FOLLOW</span><h1>双语伴随</h1><p id="live-scene">继续用英文聊。没听懂时，看一眼这里。</p></div><span class="live-status" id="live-status" role="status">正在读取…</span></div>
      <div id="live-notice" class="live-notice" role="status" hidden></div>
      <section class="live-panel" aria-label="双方英文与中文翻译">
        <div class="live-toolbar"><div><strong>这次说了什么</strong><span class="help"><button type="button" aria-label="双语伴随说明" aria-expanded="false">?</button><span class="help-body" role="tooltip">英文来自绑定 Voice 的文字转写，中文由后台 Codex 翻译，可能稍晚出现。若长时间没有新句子，先检查页面状态，再让 Agent 检查本次绑定与 Voice 是否已写出转写。字幕只辅助理解；课后精选记录在“对话记录”。</span></span><span class="fine" id="live-count"></span></div>
          <label class="live-toggle"><input id="live-chinese" type="checkbox" ${chinese?'checked':''}>始终显示中文</label></div>
        <div class="live-history-tools"><label>查看场次<select id="live-runs" aria-label="选择双语伴随场次"></select></label><span id="live-time" class="fine"></span></div>
        <div id="live-feed" class="live-feed" tabindex="0" aria-label="双语对话，可滚动回看"></div>
        <div class="live-pager"><button class="button" id="live-older" type="button">← 更早内容</button><span id="live-page" class="fine"></span><button class="button" id="live-newer" type="button">较新内容 →</button><button class="button primary" id="live-follow" type="button">正在跟随最新 ↓</button><button class="button" id="live-pause" type="button">暂停跟随</button><a class="button" id="live-review" hidden>本次复盘 ↗</a></div>
      </section><p class="live-footnote">只显示本次绑定的双方文字，不录音。中文使用现有 Codex 登录翻译，会使用该账户额度。临时缓存与正式学习记录分开，7 天前的缓存会在下一次开始伴随时清理。</p>`;
  }
  function notice(text) {const el=get('#live-notice');if(el){el.hidden=!text;el.textContent=text;}}
  function hintCard(hint) {
    if(!hint||options.page)return '';
    return `<aside class="live-hint" aria-label="当前表达提示"><div class="live-speaker"><strong>${hint.kind==='help'?'这一句可以这样说':'接下来可以聊'}</strong><span class="help"><button type="button" aria-label="表达提示说明" aria-expanded="false">?</button><span class="help-body" role="tooltip">这是根据最新发言生成的书面建议，不是 Voice 原话，也不代表已经掌握。一次保留一个说法；说顺后继续场景。断句按意思轻停，不必每块都停。</span></span></div>${hint.english?`<p class="live-english" lang="en">${e(hint.english)}</p><p class="live-translation">${e(hint.chinese)}</p>${hint.groups?.length>1?`<p class="live-groups"><span>轻停参考</span> ${hint.groups.map(e).join(' / ')}</p>`:''}`:''}${hint.next_cue?`<p class="live-next" lang="en">${e(hint.next_cue)}</p>`:''}</aside>`;
  }
  function utterance(x, open, state) {
    const fragment=x.fragment,tail=fragment?.kind==='word_tail';
    const annotation=tail?`<p class="live-fragment">转写续接 · 可能与前段连读 <strong lang="en">${e(fragment.joined_word)}</strong>，不是单独词条。</p>`:fragment?'<p class="live-fragment">前句续接 · 原始转写片段</p>':'';
    const translation=tail?'':x.status==='translated'?chinese?`<p class="live-translation" lang="zh-CN">${e(x.chinese)}</p>`:`<details class="live-answer" data-segment="${e(x.id)}" ${open.has(x.id)?'open':''}><summary>看中文</summary><p lang="zh-CN">${e(x.chinese)}</p></details>`:`<p class="live-pending">${x.status==='failed'?'这句翻译失败，英文已保留':state?.status==='error'?'翻译已暂停，英文已保留':'中文稍后出现…'}</p>`;
    return `<article class="live-utterance ${x.role==='user'?'live-user':'live-coach'}"><div class="live-speaker"><span>${x.role==='user'?'你 · YOU':'教练 · COACH'}</span><time>${e(stamp(x.timestamp))}</time></div><p class="live-english" lang="en">${e(x.text)}</p>${annotation}${translation}</article>`;
  }
  function paint(data) {
    current = data;
    const s=data.state, feed=get('#live-feed');if(!feed)return;
    if(get('#live-scene'))get('#live-scene').textContent=s?.scene_introduction||'继续用英文聊。没听懂时，看一眼这里。';
    get('#sync').textContent='伴随检查于 '+stamp(data.server_time);get('#revision').textContent='双语伴随';
    get('#live-status').textContent=s?.stale?'后台暂未响应':s?(statusNames[s.status]||s.status):'尚未开始伴随';
    get('#live-status').classList.toggle('live-error',!!(s?.stale||s?.error));
    let messages=[];
    if(s?.demo)messages.push('虚构测试演示 · 这里用于查看翻译效果，没有写入正式学习档案。');
    if(s?.recovery_mode==='after_voice')messages.push(s.recovery_reason==='missing_binding'?'结束后恢复 · 本场会中没有连接字幕；这里是从指定日志补充的双语内容，不代表实时同步。':'结束后重新翻译或补充尾段 · 原话保留，新增译文不代表会中实时同步。');
    if(s?.status==='ended')messages.push('本次对话已结束。课后复盘会整理本次表达与词义。');
    if(s?.stale)messages.push('最近未收到后台心跳，请让 Agent 检查伴随服务。页面仍可回看已有内容。');
    if(s?.error)messages.push(s.error);
    if(s?.invalid_lines)messages.push(`有 ${s.invalid_lines} 行日志未能读取，请让 Agent 检查遗漏。`);
    notice(messages.join(' '));
    const runOptions=[`<option value="">当前伴随</option>`,...data.history.map(r=>`<option value="${e(r.id)}">${e(new Date(r.voice_started_at||r.created_at).toLocaleString('zh-CN'))} · ${r.demo?'测试演示':r.recovery_mode==='after_voice'?'结束后恢复':'英语练习'}</option>`)].join('');
    if(get('#live-runs').innerHTML!==runOptions){get('#live-runs').innerHTML=runOptions;get('#live-runs').value=options.run||'';}
    get('#live-count').textContent=` · ${data.total} 条发言`;
    const pending=(data.counts.pending||0)+(data.counts.translating||0);
    get('#live-time').textContent=s?`最近转写 ${stamp(s.last_transcript_at)}${pending?` · ${pending} 条等待中文`:''}`:'开始后由 Agent 自动绑定当前 Voice';
    const review=get('#live-review');if(review){review.hidden=!s?.voice_id;if(s?.voice_id)review.href='#review?'+new URLSearchParams({thread:s.thread_id,voice:s.voice_id});}
    const signature=JSON.stringify([s?.id,data.items.map(x=>[x.seq,x.text,x.status,x.chinese,x.fragment]),data.teaching,chinese]);
    if(signature!==fingerprint) {
      const scroll=feed.scrollTop;
      const open=new Set([...feed.querySelectorAll('details[open]')].map(x=>x.dataset.segment));
      if(s?.id!==shownRun){shownRun=s?.id;follow=true;}
      if(!data.items.length) {
        const ended=['ended','expired','error'].includes(s?.status);
        feed.innerHTML=`<div class="live-empty"><span aria-hidden="true">Aa ↗</span><h2>${!s?'让对话留在英文里':ended?'这次没有收到双方转写':s.ready?'可以继续说英语了':'正在准备双语伴随'}</h2><p>${!s?'对 Agent 说“开双语伴随，继续练英语”。Agent 会负责绑定与打开；你不需要找文件。':ended?'可以继续正常练习。需要双语伴随时，让 Agent 检查日志并重新绑定。':s.ready?'先继续和 Voice 聊。收到本次转写后，英文会先出现，中文随后补齐。':'页面不会启动麦克风。Agent 正在检查后台翻译连接。'}</p>${s?.ready?'<p class="fine">如果已经说了几句仍是空白，让 Agent 检查 Voice 是否在会中写出转写。</p>':''}</div>`;
      } else {
        feed.innerHTML=data.items.map(x=>utterance(x,open,s)).join('')+hintCard(data.teaching);
      }
      fingerprint=signature;
      if(follow&&!options.page)feed.scrollTop=feed.scrollHeight;else feed.scrollTop=scroll;
    }
    get('#live-page').textContent=!follow&&!options.page?`已暂停 · ${data.items.length} 条 / 共 ${data.total} 条`:options.page?`历史第 ${data.page} / ${data.pages} 页`:`最新 ${data.items.length} 条 · 共 ${data.total} 条`;
    get('#live-pause').hidden=!follow;
    get('#live-older').disabled=data.page<=1;get('#live-newer').disabled=data.page>=data.pages;
    get('#live-follow').textContent=follow&&!options.page?'正在跟随最新 ↓':data.page<data.pages?'有新内容 · 回到最新 ↓':'回到最新 ↓';
    get('#live-follow').setAttribute('aria-pressed',String(follow&&!options.page));
  }
  async function tick(token) {
    try {
      request?.abort();request=new AbortController();
      const timeout=setTimeout(()=>request.abort(),8000);
      let r;try{r=await fetch('/api/live?'+new URLSearchParams(options),{cache:'no-store',signal:request.signal});}finally{clearTimeout(timeout);}
      const d=await r.json();if(!r.ok)throw new Error(d.error||'读取失败');
      if(token!==generation)return;paint(d);
    } catch(error) {
      if(token!==generation)return;notice('页面未连接到本地服务。已有内容仍可回看；请让 Agent 检查服务。');
      get('#live-status').textContent='本地连接中断';
    }
    if(token===generation)timer=setTimeout(()=>tick(token),1200);
  }
  function unmount(){resizeObserver?.disconnect();clearTimeout(timer);request?.abort();generation++;fingerprint='';}
  function refresh(){clearTimeout(timer);tick(++generation);}
  function mount(data,args) {
    options={...args};follow=!options.page;paint(data);
    resizeObserver?.disconnect();
    resizeObserver=new ResizeObserver(()=>{if(follow&&!options.page){const f=get('#live-feed');if(f)f.scrollTop=f.scrollHeight;}});
    resizeObserver.observe(get('#live-feed'));
    get('#live-chinese').addEventListener('change',event=>{chinese=event.target.checked;localStorage.setItem('coach-live-chinese',chinese?'always':'on-demand');paint(current);});
    get('#live-runs').addEventListener('change',event=>{location.hash='#live'+(event.target.value?'?run='+event.target.value:'');});
    get('#live-older').addEventListener('click',()=>{options.page=String(current.page-1);follow=false;refresh();get('#live-feed').scrollTop=0;});
    get('#live-newer').addEventListener('click',()=>{options.page=String(current.page+1);follow=false;refresh();get('#live-feed').scrollTop=0;});
    get('#live-follow').addEventListener('click',()=>{delete options.page;follow=true;refresh();const f=get('#live-feed');f.scrollTop=f.scrollHeight;});
    get('#live-pause').addEventListener('click',()=>{follow=false;clearTimeout(timer);request?.abort();generation++;paint(current);});
    timer=setTimeout(()=>tick(generation),1200);
  }
  return {shell,mount,unmount};
})();

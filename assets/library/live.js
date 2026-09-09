'use strict';
window.CoachLive = (() => {
  let request, timer, resizeObserver, generation = 0, options = {}, current, follow = true, shownRun, fingerprint = '';
  let chinese = localStorage.getItem('coach-live-chinese') !== 'on-demand';
  const e = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const get = s => document.querySelector(s);
  const stamp = s => s ? new Date(s).toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—';
  const statusNames = {starting:'正在连接翻译',translating:'正在补充中文',recovering:'正在恢复已结束的对话',draining:'正在处理最后几句',waiting_voice:'尚未绑定活动 Voice',waiting_transcript:'正在等待新转写',ended:'本次伴随已结束',stopped:'伴随已停止 · 可回看',expired:'已暂停伴随',error:'伴随需要检查'};
  function shell() {
    return `<section class="live-panel" aria-label="双方原话与中文翻译">
        <div class="live-toolbar"><div><strong>双语伴随</strong><span class="help"><button type="button" aria-label="双语伴随说明" aria-expanded="false">?</button><span class="help-body" role="tooltip">原话来自本次 Voice 转写，中文由后台翻译。失败不会停止接收原话，可重试补充。关闭 Voice 后自动整理复盘；口头说结束不一定会关闭语音窗口。</span></span><span class="fine" id="live-count"></span></div>
          <div class="live-actions"><label class="live-toggle"><input id="live-chinese" type="checkbox" ${chinese?'checked':''}>中文</label><a id="live-review" class="button small" hidden title="关闭 Voice 后自动整理；口头说结束不一定会关闭语音窗口。">本次复盘 ↗</a>
          <details id="live-details" class="live-details"><summary>更多</summary><div class="live-options"><label>查看场次<select id="live-runs" aria-label="选择双语伴随场次"></select></label><h2>本次场景</h2><p id="live-scene"></p><h2>学习档案</h2><div class="live-links"><a href="#overview">学习首页</a><a href="#sessions">对话记录</a><a href="#terms">生词与表达</a><a href="#stats">学习回顾</a><a href="#storage">本地学习数据</a><button class="quiet" data-open-folder type="button">打开学习目录 ↗</button></div><h2>伴随说明</h2><p>只展示绑定 Voice 的转写，不录音。中文使用现有 Codex 登录与账户额度；字幕缓存与正式学习档案分开。</p><p>关闭 Voice 后自动生成复盘；生成时可以离开聊天，从本页或对话记录返回。</p><details><summary>诊断详情</summary><p id="live-diagnostic">暂无异常</p></details></div></details></div></div>
        <div class="live-info"><span class="live-status" id="live-status" role="status">正在读取…</span><span id="live-time" class="fine"></span></div>
        <div id="live-notice" class="live-notice" role="status" hidden><span id="live-notice-text"></span><button id="live-retry-translation" class="button small" type="button" hidden>重试中文</button></div>
        <div id="live-feed" class="live-feed" tabindex="0" aria-label="双语对话，可滚动回看"></div>
        <div class="live-pager"><button class="button" id="live-older" type="button">← 更早</button><span id="live-page" class="fine"></span><button class="button" id="live-newer" type="button">较新 →</button><button class="button primary" id="live-follow" type="button">跟随最新 ↓</button><button class="button" id="live-pause" type="button">暂停滚动</button></div>
      </section>`;
  }
  function notice(text) {const el=get('#live-notice');if(el){el.hidden=!text;get('#live-notice-text').textContent=text;}}
  function hintCard(hint) {
    if(!hint||options.page||options.offset!==undefined)return '';
    return `<aside class="live-hint" aria-label="当前表达提示"><div class="live-speaker"><strong>${hint.kind==='help'?'这一句可以这样说':'接下来可以聊'}</strong><span class="help"><button type="button" aria-label="表达提示说明" aria-expanded="false">?</button><span class="help-body" role="tooltip">这是根据最新发言生成的书面建议，不是 Voice 原话，也不代表已经掌握。一次保留一个说法；说顺后继续场景。断句按意思轻停，不必每块都停。</span></span></div>${hint.english?`<p class="live-english" lang="en">${e(hint.english)}</p><p class="live-translation">${e(hint.chinese)}</p>${hint.groups?.length>1?`<p class="live-groups"><span>轻停参考</span> ${hint.groups.map(e).join(' / ')}</p>`:''}`:''}${hint.next_cue?`<p class="live-next" lang="en">${e(hint.next_cue)}</p>`:''}</aside>`;
  }
  function utterance(x, open, state) {
    const fragment=x.fragment,tail=fragment?.kind==='word_tail';
    const annotation=tail?`<p class="live-fragment">转写续接 · 可能与前段连读 <strong lang="en">${e(fragment.joined_word)}</strong>，不是单独词条。</p>`:fragment?'<p class="live-fragment">前句续接 · 原始转写片段</p>':'';
    const translation=tail?'':x.status==='translated'?chinese?`<p class="live-translation" lang="zh-CN">${e(x.chinese)}</p>`:`<details class="live-answer" data-segment="${e(x.id)}" ${open.has(x.id)?'open':''}><summary>看中文</summary><p lang="zh-CN">${e(x.chinese)}</p></details>`:`<p class="live-pending">${x.status==='failed'?'这句中文待补，可重试':state?.translation_status==='unavailable'?'中文待补':['ended','error','expired','stopped'].includes(state?.status)?'中文尚未完成，原文已保留':'中文稍后出现…'}</p>`;
    return `<article data-row="${e(x.id)}" class="live-utterance ${x.role==='user'?'live-user':'live-coach'}"><div class="live-speaker"><span>${x.role==='user'?'你 · YOU':'教练 · COACH'}</span><time>${e(stamp(x.timestamp))}</time></div><p class="live-english" lang="en">${e(x.text)}</p>${annotation}${translation}</article>`;
  }
  function paint(data) {
    current = data;
    const s=data.state, feed=get('#live-feed');if(!feed)return;
    if(get('#live-scene'))get('#live-scene').textContent=s?.scene_introduction||'继续用英文聊。没听懂时，看一眼这里。';
    get('#sync').textContent='伴随检查于 '+stamp(data.server_time);get('#revision').textContent='双语伴随';
    get('#live-status').textContent=s?.stale?'后台暂未响应':s?(!s.voice_id&&!data.total?'尚未绑定活动 Voice':s.translation_status==='unavailable'&&!['ended','error','expired','stopped'].includes(s.status)?'原话继续更新 · 中文暂不可用':statusNames[s.status]||s.status):'尚未开始伴随';
    get('#live-status').classList.toggle('live-error',!!(s?.stale||s?.error||s?.translation_error));
    let messages=[];
    if(s?.demo)messages.push('虚构测试演示 · 这里用于查看翻译效果，没有写入正式学习档案。');
    if(s?.imported)messages.push('这是迁移保留的历史字幕。新的练习会重新绑定当前电脑的 Voice，历史原文与译文可继续回看。');
    if(s?.recovery_mode==='after_voice')messages.push('课后补译 · 原话保留');
    if(s?.stale)messages.push('最近未收到后台心跳，请让 Agent 检查伴随服务。页面仍可回看已有内容。');
    if(s?.error)messages.push('转写需要检查，已有内容可回看。');
    if(s?.translation_error)messages.push(s.desired==='stopped'?'中文尚未补齐，原话已保留。':'中文暂不可用，原话继续更新。');
    if(s?.review_error)messages.push('复盘登记需要检查，原话与翻译继续更新。');
    const failed=data.counts.failed||0, pending=(data.counts.pending||0)+(data.counts.translating||0);
    const ended=['ended','error','expired','stopped'].includes(s?.status);
    if(failed&&!s?.translation_error)messages.push(`${failed} 句中文待补，其余内容继续更新。`);
    const timing=s?.translation_timing;
    const speed=timing?`最近一批 ${timing.segments} 句${Number.isFinite(timing.first_sentence_seconds)?` · 首句 ${timing.first_sentence_seconds.toFixed(1)} 秒`:''}${Number.isFinite(timing.request_seconds)?` · 请求完成 ${timing.request_seconds.toFixed(1)} 秒`:''}`:'';
    const sourceState=s?(s.voice_id?`Voice 已绑定；收到 ${data.total} 句原话`:'没有活动 Voice 身份；尚无可翻译的原话'):'';
    get('#live-diagnostic').textContent=[sourceState,s?.error,s?.translation_error,s?.review_error,s?.teaching_error?`书面提示：${s.teaching_error}`:'',...Object.values(s?.translation_rejected||{}),speed].filter(Boolean).join(' · ')||'暂无异常';
    const retry=get('#live-retry-translation');if(retry){retry.hidden=!!s?.imported||!((s?.translation_error||failed||(ended&&pending))&&s.status!=='recovering');retry.disabled=!!s?.recovery_requested;retry.textContent=s?.recovery_requested?'补译已排队':'重试中文';}
    if(s?.invalid_lines)messages.push(`有 ${s.invalid_lines} 行日志未能读取，请让 Agent 检查遗漏。`);
    notice(messages.join(' '));
    const runOptions=[`<option value="">当前伴随</option>`,...data.history.map(r=>`<option value="${e(r.id)}">${e(new Date(r.voice_started_at||r.created_at).toLocaleString('zh-CN'))} · ${r.demo?'测试演示':r.recovery_mode==='after_voice'?'结束后恢复':'英语练习'}</option>`)].join('');
    if(get('#live-runs').innerHTML!==runOptions){get('#live-runs').innerHTML=runOptions;get('#live-runs').value=options.run||'';}
    get('#live-count').textContent=` · ${data.total} 句`;
    get('#live-time').textContent=s?`转写 ${stamp(s.last_transcript_at)}${pending?` · ${pending} 句待翻译`:''}`:'开始后自动绑定本次 Voice';
    const review=get('#live-review');if(review){review.hidden=!s?.voice_id;if(s?.voice_id)review.href='#review?'+new URLSearchParams({thread:s.thread_id,voice:s.voice_id});}
    const signature=JSON.stringify([s?.id,s?.voice_id,s?.status,s?.translation_status,s?.ready,data.items.map(x=>[x.seq,x.text,x.status,x.chinese,x.fragment]),data.teaching,chinese,options.page,options.offset]);
    if(signature!==fingerprint) {
      const scroll=feed.scrollTop;
      const top=feed.getBoundingClientRect?.().top;
      const anchor=[...feed.querySelectorAll('[data-row]')].find(el=>el.getBoundingClientRect().bottom>top);
      const anchorID=anchor?.dataset.row, anchorTop=anchor?.getBoundingClientRect().top;
      const open=new Set([...feed.querySelectorAll('details[open]')].map(x=>x.dataset.segment));
      if(s?.id!==shownRun){shownRun=s?.id;follow=true;}
      if(!data.items.length) {
        const ended=['ended','stopped','expired','error'].includes(s?.status);
        const unbound=s&&!s.voice_id;
        feed.innerHTML=`<div class="live-empty"><span aria-hidden="true">Aa ↗</span><h2>${!s?'尚未开始双语伴随':unbound?'尚未绑定活动 Voice':ended?'这次没有收到双方转写':'已绑定 Voice，等待原话'}</h2><p>${!s||unbound?'实时双语需要活动 Voice。打开 Voice 后，Agent 会核对本场身份并绑定；文字练习可直接在聊天中继续。':ended?'Agent 需要检查本场转写来源；刷新页面或重试翻译不能补出缺失的原话。':'收到本场转写后，英文会先出现，中文随后补充。如果已经说了几句仍是空白，Agent 需要检查宿主是否提供会中转写。'}</p></div>`;
      } else {
        feed.innerHTML=data.items.map(x=>utterance(x,open,s)).join('')+hintCard(data.teaching);
      }
      fingerprint=signature;
      if(follow&&!options.page)feed.scrollTop=feed.scrollHeight;else {
        feed.scrollTop=scroll;
        const restored=[...feed.querySelectorAll('[data-row]')].find(el=>el.dataset.row===anchorID);
        if(restored)feed.scrollTop+=restored.getBoundingClientRect().top-anchorTop;
      }
    }
    get('#live-page').textContent=!follow&&!options.page?`已暂停滚动 · 共 ${data.total} 句`:options.page?`第 ${data.page}/${data.pages} 页`:`最新 ${data.items.length} / ${data.total} 句`;
    get('#live-pause').hidden=!follow;
    get('#live-older').disabled=data.page<=1;get('#live-newer').disabled=data.page>=data.pages;
    get('#live-older').hidden=data.pages<=1;get('#live-newer').hidden=data.pages<=1;
    get('#live-follow').textContent=follow&&!options.page?'跟随最新 ↓':'回到最新 ↓';
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
  function unmount(){resizeObserver?.disconnect();clearTimeout(timer);request?.abort();generation++;fingerprint='';current=null;}
  function refresh(){clearTimeout(timer);tick(++generation);}
  function mount(data,args) {
    options={...args};follow=!options.page;paint(data);
    resizeObserver?.disconnect();
    resizeObserver=new ResizeObserver(()=>{if(follow&&!options.page){const f=get('#live-feed');if(f)f.scrollTop=f.scrollHeight;}});
    resizeObserver.observe(get('#live-feed'));
    const retry=get('#live-retry-translation');if(retry)retry.addEventListener('click',async()=>{const run=current?.state?.id, token=generation;if(!run)return;retry.disabled=true;try{const storage=await fetch('/api/storage',{cache:'no-store'});const info=await storage.json();if(!storage.ok)throw new Error(info.error||'读取失败');const response=await fetch('/api/live/retry',{method:'POST',headers:{'Content-Type':'application/json','X-Coach-Token':info.open_token},body:JSON.stringify({run})});const result=await response.json();if(!response.ok)throw new Error(result.error||'重试失败');if(token===generation)refresh();}catch(error){if(token===generation)notice(error.message);}finally{if(token===generation)retry.disabled=false;}});
    get('#live-chinese').addEventListener('change',event=>{chinese=event.target.checked;localStorage.setItem('coach-live-chinese',chinese?'always':'on-demand');paint(current);});
    get('#live-runs').addEventListener('change',event=>{location.hash='#live'+(event.target.value?'?run='+event.target.value:'');});
    get('#live-older').addEventListener('click',()=>{delete options.offset;options.page=String(Math.max(1,current.page-1));follow=false;refresh();get('#live-feed').scrollTop=0;});
    get('#live-newer').addEventListener('click',()=>{delete options.offset;options.page=String(current.page+1);follow=false;refresh();get('#live-feed').scrollTop=0;});
    get('#live-follow').addEventListener('click',()=>{delete options.page;delete options.offset;follow=true;refresh();const f=get('#live-feed');f.scrollTop=f.scrollHeight;});
    get('#live-pause').addEventListener('click',()=>{options.offset=String(current.offset??Math.max(0,current.total-40));follow=false;paint(current);});
    timer=setTimeout(()=>tick(generation),1200);
  }
  return {shell,mount,unmount,state:()=>current?.state};
})();

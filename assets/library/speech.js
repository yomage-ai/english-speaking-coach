// Browser/system speech only. No microphone, remote voice, or learning writes.
'use strict';
window.CoachSpeech = (() => {
  const synth = window.speechSynthesis;
  let active = null, rate = 1;
  const supported = () => synth && typeof window.SpeechSynthesisUtterance === 'function';
  function status(button, message) {
    const label = button.closest('.speech-control')?.querySelector('.speech-status');
    if (label) label.textContent = message;
  }
  function reset(job, message) {
    if (active !== job) return;
    active = null;
    clearTimeout(job.timer);
    job.button.textContent = '朗读英文';
    job.button.setAttribute('aria-pressed', 'false');
    status(job.button, message);
  }
  function stop() {
    if (!active) return;
    reset(active, '已停止');
    // Invalidate callbacks before cancel(): some engines fire them synchronously.
    synth.cancel();
  }

  function chunks(text) {
    const clean=text.replace(/[–—]/g, ', ').replace(/\s+/g, ' ').trim();
    const sentences=clean.match(/[^.!?;:]+[.!?;:]?|[.!?]+/g)?.map(x=>x.trim()).filter(Boolean)||[clean];
    const out=[];
    for (const sentence of sentences) {
      if (sentence.length<=140) {out.push(sentence);continue;}
      let rest=sentence;
      while(rest.length>140) {
        const head=rest.slice(0,141), cut=Math.max(head.lastIndexOf(', '),head.lastIndexOf(' '));
        const at=cut>=50?cut:140;
        out.push(rest.slice(0,at).trim());rest=rest.slice(at).trim();
      }
      if(rest)out.push(rest);
    }
    return out;
  }

  function chooseVoice() {
    const english=synth.getVoices().filter(v=>v.localService===true&&/^en(?:[-_]|$)/i.test(v.lang));
    const score=voice=>{
      const name=voice.name||'';
      if(/\b(Samantha|Alex|Ava|Allison|Daniel|Karen|Moira|Rishi|Serena|Tessa)\b/i.test(name))return 0;
      if(/enhanced|premium/i.test(name))return 1;
      if(voice.default)return 2;
      if(/^en-US$/i.test(voice.lang))return 3;
      return 4;
    };
    return english.sort((a,b)=>score(a)-score(b))[0];
  }

  function speakNext(job) {
    if(active!==job)return;
    if(job.index>=job.parts.length){reset(job,'朗读结束');return;}
    const utterance=new window.SpeechSynthesisUtterance(job.parts[job.index]);
    job.utterance=utterance;
    utterance.voice=job.voice;utterance.lang=job.voice.lang;utterance.rate=job.rate;
    utterance.onstart=()=>{
      if(active!==job||job.utterance!==utterance)return;
      clearTimeout(job.timer);
      status(job.button,`正在朗读 · ${job.voice.name}${job.rate<1?' · 慢速':''}`);
      job.timer=setTimeout(()=>{
        if(active!==job||job.utterance!==utterance)return;
        reset(job,'朗读未能完整播放，请再次点击。');synth.cancel();
      },Math.max(12000,utterance.text.length*260/job.rate));
    };
    utterance.onend=()=>{
      if(active!==job||job.utterance!==utterance)return;
      clearTimeout(job.timer);job.index++;
      job.timer=setTimeout(()=>speakNext(job),40);
    };
    utterance.onerror=event=>{
      if(active!==job||job.utterance!==utterance)return;
      reset(job,['canceled','interrupted'].includes(event.error)?'已停止':'系统未能完整朗读，请重试或换用系统浏览器。');
    };
    job.timer=setTimeout(()=>{
      if(active!==job||job.utterance!==utterance)return;
      reset(job,'系统未开始朗读，请重试或换用系统浏览器。');synth.cancel();
    },6000);
    try{synth.speak(utterance);}catch{reset(job,'系统未能朗读，请换用系统浏览器重试。');}
  }
  function refresh() {
    if (active?.button.isConnected === false) stop();
    document.querySelectorAll('[data-speech-rate]').forEach(button => {
      button.setAttribute('aria-pressed', String(rate < 1));
    });
  }
  function play(button) {
    if (active?.button === button) { stop(); return; }
    stop();
    const text = button.dataset.speakEnglish?.trim();
    if (!text) return;
    if (!supported()) {
      status(button, '此浏览器不支持系统朗读，请用 Safari、Chrome 或 Edge 打开本页。');
      return;
    }
    const voices = synth.getVoices();
    const voice = chooseVoice();
    if (!voice) {
      status(button, voices.length
        ? '没有可用的本地英语声音。请在系统语音设置添加英语声音，或换用系统浏览器。'
        : '系统声音尚未就绪，请稍后再点；若持续无声，请换用系统浏览器。');
      return;
    }
    const job = {button, voice, rate, parts:chunks(text), index:0, utterance:null, timer:null};
    active = job;
    button.textContent = '停止朗读'; button.setAttribute('aria-pressed', 'true');
    status(button, '准备朗读…');
    // Chrome can interrupt a new utterance when cancel() and speak() happen in
    // the same event turn. Give cancellation one short tick to settle.
    synth.cancel();
    job.timer=setTimeout(()=>speakNext(job),80);
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-speak-english]');
    if (button) { play(button); return; }
    const speed = event.target.closest('[data-speech-rate]');
    if (speed) {
      stop(); rate = rate < 1 ? 1 : 0.78; refresh();
      status(speed, rate < 1 ? '已选慢速，再点朗读英文。' : '已选正常语速，再点朗读英文。');
    }
  });
  window.addEventListener('pagehide', stop);
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  document.getElementById('term-dialog')?.addEventListener('close', stop);
  // Warm the voice list without speaking; later clicks re-read asynchronous voices.
  if (supported()) synth.getVoices();
  return {stop, refresh, chunks};
})();

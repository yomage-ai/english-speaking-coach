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
    const english = voices.filter(v => v.localService === true && /^en(?:[-_]|$)/i.test(v.lang));
    const voice = english.find(v => v.default) || english.find(v => /^(Samantha|Alex)$|Microsoft.*(?:Zira|David|Aria|Jenny)/i.test(v.name)) || english.find(v => /^en-US$/i.test(v.lang)) || english[0];
    if (!voice) {
      status(button, voices.length
        ? '没有可用的本地英语声音。请在系统语音设置添加英语声音，或换用系统浏览器。'
        : '系统声音尚未就绪，请稍后再点；若持续无声，请换用系统浏览器。');
      return;
    }
    const utterance = new window.SpeechSynthesisUtterance(text);
    utterance.voice = voice; utterance.lang = voice.lang; utterance.rate = rate;
    const job = {button, utterance, timer: null}; // Retain the utterance until completion.
    active = job;
    button.textContent = '停止朗读'; button.setAttribute('aria-pressed', 'true');
    status(button, '准备朗读…');
    utterance.onstart = () => {
      if (active !== job) return;
      clearTimeout(job.timer);
      status(button, `正在朗读 · ${voice.name}`);
      job.timer = setTimeout(() => {
        if (active !== job) return;
        reset(job, '朗读已停止，可再次点击播放。'); synth.cancel();
      }, Math.max(60000, text.length * 200 / rate));
    };
    utterance.onend = () => reset(job, '朗读结束');
    utterance.onerror = event => reset(job, ['canceled', 'interrupted'].includes(event.error)
      ? '已停止' : '系统未能朗读，请重试或换用系统浏览器，并检查音量与英语声音。');
    job.timer = setTimeout(() => {
      if (active !== job) return;
      reset(job, '系统未开始朗读，请重试或换用系统浏览器。'); synth.cancel();
    }, 6000);
    try { synth.speak(utterance); }
    catch { reset(job, '系统未能朗读，请换用系统浏览器重试。'); }
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-speak-english]');
    if (button) { play(button); return; }
    const speed = event.target.closest('[data-speech-rate]');
    if (speed) {
      stop(); rate = rate < 1 ? 1 : 0.8; refresh();
      status(speed, rate < 1 ? '已选慢速，再点朗读英文。' : '已选正常语速，再点朗读英文。');
    }
  });
  window.addEventListener('pagehide', stop);
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  document.getElementById('term-dialog')?.addEventListener('close', stop);
  // Warm the voice list without speaking; later clicks re-read asynchronous voices.
  if (supported()) synth.getVoices();
  return {stop, refresh};
})();

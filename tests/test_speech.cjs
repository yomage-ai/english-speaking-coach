// Exercise browser speech failures and cancellation without accessing real voices/data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../assets/library/speech.js'), 'utf8');
const local = {name:'Test English',lang:'en-US',localService:true};
function browser(voices = [local], supported = true) {
  const events = {}, windowEvents = {}, controls = [], spoken = [], timers = new Map();
  let next = 0, cancels = 0, dialogClose;
  const synth = {getVoices:()=>voices, speak:u=>spoken.push(u), cancel(){cancels++;},
    setVoices(v){voices=v;}};
  const document = {hidden:false,addEventListener:(key,fn)=>events[key]=fn,
    querySelectorAll:()=>controls.map(c=>c.speed),
    getElementById:()=>({addEventListener:(key,fn)=>dialogClose=fn})};
  const window = {speechSynthesis:supported?synth:undefined,SpeechSynthesisUtterance:class {constructor(t){this.text=t;}},
    addEventListener:(key,fn)=>windowEvents[key]=fn};
  vm.runInNewContext(source,{window,document,setTimeout(fn){timers.set(++next,fn);return next;},clearTimeout:id=>timers.delete(id)});
  function control(text) {
    const status = {textContent:''};
    const root = {querySelector:()=>status};
    const make = (dataset, selector) => ({dataset,textContent:'朗读英文',attrs:{},
      setAttribute(k,v){this.attrs[k]=v;},closest(s){return s==='.speech-control'?root:s===selector?this:null;}});
    const c = {status,button:make({speakEnglish:text},'[data-speak-english]'),speed:make({},'[data-speech-rate]')};
    controls.push(c);return c;
  }
  return {synth,spoken,control,window,document,timers,events,windowEvents,
    click:target=>events.click({target}),close:()=>dialogClose(),cancels:()=>cancels,
    runNext(){const id=[...timers.keys()].sort((a,b)=>a-b)[0],f=timers.get(id);timers.delete(id);f();},
    expire(){this.runNext();}};
}
{
  const b=browser([{...local,localService:false,name:'Remote'}, {name:'Chinese',lang:'zh-CN',localService:true},local]);
  const a=b.control('Could you help me?'), c=b.control('I would like some tea.');
  b.click(a.button);assert.equal(b.spoken.length,0,'Playback waits for cancel to settle');b.runNext();
  const first=b.spoken[0];assert.equal(first.text,'Could you help me?');assert.equal(first.voice,local);
  first.onstart();assert.match(a.status.textContent,/正在朗读/);
  b.click(c.button);b.runNext();const second=b.spoken[1];assert.equal(b.cancels(),3);
  first.onend();first.onerror({error:'interrupted'});assert.equal(c.button.attrs['aria-pressed'],'true','Old callbacks cannot clear new playback');
  second.onend();b.runNext();assert.equal(c.button.attrs['aria-pressed'],'false');assert.equal(b.timers.size,0);
  b.click(a.speed);assert.equal(a.speed.attrs['aria-pressed'],'true');assert.equal(c.speed.attrs['aria-pressed'],'true');
  b.click(a.button);b.runNext();assert.equal(b.spoken.at(-1).rate,0.78);b.click(a.button);assert.equal(a.status.textContent,'已停止');
  b.click(c.button);b.document.hidden=true;b.events.visibilitychange();assert.equal(c.status.textContent,'已停止');
  b.click(c.button);b.close();assert.equal(c.status.textContent,'已停止');
  b.click(c.button);b.windowEvents.pagehide();assert.equal(c.status.textContent,'已停止');
  assert.deepEqual(Array.from(b.window.CoachSpeech.chunks('One long thought, followed by another. Final question?')),['One long thought, followed by another.','Final question?']);
  assert.ok(Array.from(b.window.CoachSpeech.chunks('This is a deliberately long spoken sentence, '.repeat(8))).every(x=>x.length<=140));
}
{
  const b=browser([]), c=b.control('Hello.');b.click(c.button);assert.equal(b.spoken.length,0);assert.match(c.status.textContent,/尚未就绪/);
  b.synth.setVoices([{...local,localService:false}]);b.click(c.button);assert.equal(b.spoken.length,0);assert.match(c.status.textContent,/本地英语/);
  b.synth.setVoices([local]);b.click(c.button);b.runNext();assert.equal(b.spoken.length,1,'A later click must reload asynchronously available voices');
  b.expire();assert.match(c.status.textContent,/未开始/);assert.equal(c.button.attrs['aria-pressed'],'false');
  b.click(c.button);b.runNext();b.spoken.at(-1).onerror({error:'not-allowed'});assert.match(c.status.textContent,/未能完整朗读/);
  b.synth.speak=()=>{throw Error('unavailable');};b.click(c.button);b.runNext();assert.equal(c.button.attrs['aria-pressed'],'false');assert.equal(b.timers.size,0);
}
{
  const b=browser([],false), c=b.control('Hello.');b.click(c.button);assert.match(c.status.textContent,/不支持/);
}
console.log('System speech: local English only, cancellation, slow rate, lifecycle and failure recovery passed.');

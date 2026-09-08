// Synthetic caption controller: no microphone, archive writes or paid model calls.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map(),timers=new Map();let observer,timerId=0,response;
const el=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',scrollTop:0,scrollHeight:3000,handlers:{},querySelectorAll:()=>[],classList:{toggle(){}},setAttribute(){},addEventListener(k,v){this.handlers[k]=v;}});return elements.get(id);};
const ctx=vm.createContext({window:{},document:{querySelector:el},localStorage:{getItem(){return null},setItem(){}},location:{},Date,URLSearchParams,AbortController,console,
ResizeObserver:class{constructor(fn){observer=fn}observe(){}disconnect(){}},
setTimeout(fn){timers.set(++timerId,fn);return timerId},clearTimeout(id){timers.delete(id)},fetch:async()=>({ok:true,json:async()=>response})});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../assets/library/live.js'),'utf8'),ctx);
const data=(total,status='pending',chinese='')=>({server_time:'2026-01-01T00:00:00Z',state:{id:'synthetic',status:'waiting_transcript',thread_id:'one',voice_id:'two'},history:[],total,counts:{pending:status==='pending'?1:0},items:[{seq:total,id:String(total),role:'user',text:'Synthetic line '+total,status,chinese}],page:2,pages:2});
(async()=>{
const live=ctx.window.CoachLive,feed=el('#live-feed');response=data(41);live.mount(response,{});
assert.equal(feed.scrollTop,3000);assert.match(feed.innerHTML,/Synthetic line 41/);
feed.scrollTop=0;feed.scrollHeight=3500;observer();assert.equal(feed.scrollTop,3500,'Panel resizing retains latest content');
response=data(41,'translated','测试句');const [id,tick]=[...timers][0];timers.delete(id);await tick();assert.match(feed.innerHTML,/测试句/);assert.equal(feed.scrollTop,3500);
response=data(42);await el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.match(feed.innerHTML,/Synthetic line 42/);
el('#live-pause').handlers.click();assert.ok(timers.size>0,'Pausing scrolling keeps new captions polling');feed.scrollTop=100;observer();assert.equal(feed.scrollTop,100);
response=data(42,'translated','稍后补到的中文');const [pauseId,pauseTick]=[...timers][0];timers.delete(pauseId);await pauseTick();assert.match(feed.innerHTML,/稍后补到的中文/);assert.equal(feed.scrollTop,100,'Delayed translations preserve manual position');
response=data(43);el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.match(feed.innerHTML,/Synthetic line 43/);assert.equal(feed.scrollTop,3500);
response={...data(44,'translated','错误的独立词义'),items:[{id:'tail',seq:44,role:'user',text:'- buster',status:'translated',chinese:'错误的独立词义',fragment:{kind:'word_tail',joined_word:'blockbuster'}}],teaching:{kind:'help',english:'Could we see a movie?',chinese:'可以看电影吗？',groups:['Could we see a movie?'],next_cue:''}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.match(feed.innerHTML,/blockbuster/);assert.doesNotMatch(feed.innerHTML,/错误的独立词义/);assert.match(feed.innerHTML,/这一句可以这样说/);
response=data(45);el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.doesNotMatch(feed.innerHTML,/这一句可以这样说/,'A new turn cannot retain an old hint');
assert.equal(el('#live-retry-translation').hidden,true,'Healthy captions must not offer an irrelevant retry');
response={...data(46),state:{...data(46).state,translation_status:'unavailable',translation_error:'Fictional connection failure',desired:'running'}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.equal(el('#live-retry-translation').hidden,false);assert.match(feed.innerHTML,/Synthetic line 46/);
response={...response,state:{...response.state,status:'stopped',desired:'stopped',imported:true}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.equal(el('#live-retry-translation').hidden,false,'Closed captions retain their targeted retry');assert.match(el('#live-status').textContent,/可回看/);
live.unmount();assert.equal(timers.size,0);console.log('Passed live behavior: initial follow, resize, delayed translation, next segment, pause and resume.');
})().catch(e=>{console.error(e);process.exitCode=1});

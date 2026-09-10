// Synthetic caption controller: no microphone, archive writes or paid model calls.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map(),timers=new Map();let observer,timerId=0,response,requests=[];
const el=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',scrollTop:0,scrollHeight:3000,handlers:{},querySelectorAll:()=>[],classList:{toggle(){}},setAttribute(){},addEventListener(k,v){this.handlers[k]=v;}});return elements.get(id);};
const ctx=vm.createContext({window:{},document:{querySelector:el},localStorage:{getItem(){return null},setItem(){}},location:{},Date,URLSearchParams,AbortController,console,
ResizeObserver:class{constructor(fn){observer=fn}observe(){}disconnect(){}},
setTimeout(fn){timers.set(++timerId,fn);return timerId},clearTimeout(id){timers.delete(id)},fetch:async(url,options)=>{requests.push({url,options});return {ok:true,json:async()=>response}}});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../assets/library/live.js'),'utf8'),ctx);
const data=(total,status='pending',chinese='')=>({server_time:'2026-01-01T00:00:00Z',state:{id:'synthetic',status:'waiting_transcript',thread_id:'one',voice_id:'two'},history:[],total,counts:{pending:status==='pending'?1:0},items:[{seq:total,id:String(total),role:'user',text:'Synthetic line '+total,status,chinese}],page:2,pages:2});
(async()=>{
const live=ctx.window.CoachLive,feed=el('#live-feed');response=data(41);live.mount(response,{});
assert.equal(feed.scrollTop,3000);assert.match(feed.innerHTML,/Synthetic line 41/);
feed.scrollTop=0;feed.scrollHeight=3500;observer();assert.equal(feed.scrollTop,3500,'Panel resizing retains latest content');
response=data(41,'translated','测试句');const [id,tick]=[...timers][0];timers.delete(id);await tick();assert.match(feed.innerHTML,/测试句/);assert.equal(feed.scrollTop,3500);
response=data(42);await el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.match(feed.innerHTML,/Synthetic line 42/);
el('#live-pause').handlers.click();assert.ok(timers.size>0,'Pausing scrolling keeps new captions polling');feed.scrollTop=100;observer();assert.equal(feed.scrollTop,100);
response=data(42,'translated','稍后补到的中文');const [pauseId,pauseTick]=[...timers][0];timers.delete(pauseId);await pauseTick();assert.match(feed.innerHTML,/稍后补到的中文/);assert.match(requests.at(-1).url,/offset=2/,'Paused reading requests the same window');assert.equal(feed.scrollTop,100,'Delayed translations preserve manual position');
response=data(43);el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.match(feed.innerHTML,/Synthetic line 43/);assert.equal(feed.scrollTop,3500);
response={...data(44,'translated','错误的独立词义'),items:[{id:'tail',seq:44,role:'user',text:'- buster',status:'translated',chinese:'错误的独立词义',fragment:{kind:'word_tail',joined_word:'blockbuster'}}],teaching:{kind:'help',english:'Could we see a movie?',chinese:'可以看电影吗？',groups:['Could we see a movie?'],next_cue:''}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.match(feed.innerHTML,/blockbuster/);assert.doesNotMatch(feed.innerHTML,/错误的独立词义/);assert.doesNotMatch(feed.innerHTML,/这一句可以这样说/,'Legacy prediction payloads must be ignored');
response=data(45);el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.doesNotMatch(feed.innerHTML,/这一句可以这样说/,'Live predictions stay removed after a new turn');
assert.equal(el('#live-retry-translation').hidden,true,'Healthy captions must not offer an irrelevant retry');
response={...data(46),state:{...data(46).state,translation_status:'unavailable',translation_error:'Fictional connection failure',desired:'running'}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.equal(el('#live-retry-translation').hidden,false);assert.match(feed.innerHTML,/Synthetic line 46/);
response={...response,state:{...response.state,status:'stopped',desired:'stopped',imported:true}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.equal(el('#live-retry-translation').hidden,true,'Imported captions cannot retry an unavailable old-machine source');assert.match(el('#live-status').textContent,/可回看/);
response={...data(47),state:{...data(47).state,status:'ended',desired:'stopped'}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));assert.equal(el('#live-retry-translation').hidden,false,'Ended pending rows offer recovery even without a connection error');
// A legacy empty binding never claims readiness, even if a model connected.
response={...data(0),total:0,items:[],counts:{},state:{id:'empty',status:'waiting_voice',ready:true,thread_id:'one',voice_id:null}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));
assert.match(el('#live-status').textContent,/尚未绑定活动 Voice/);
assert.doesNotMatch(feed.innerHTML,/已就绪|可以继续说英语了/);
assert.match(el('#live-diagnostic').textContent,/没有活动 Voice 身份/);
// Receiving a Voice identity with otherwise unchanged empty state repaints the cue.
response={...response,state:{...response.state,voice_id:'two',status:'waiting_transcript'}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));
assert.match(feed.innerHTML,/已绑定 Voice，等待原话/);
assert.doesNotMatch(feed.innerHTML,/尚未绑定活动 Voice/);
response={...response,state:{...response.state,status:'error',error:'源日志在字节 120 有损坏的完整行'}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));
assert.match(el('#live-diagnostic').textContent,/字节 120/);
assert.match(feed.innerHTML,/不能补出缺失的原话/);
// Restore a pending closed run for the existing scoped-retry test below.
response={...data(47),state:{...data(47).state,status:'ended',desired:'stopped'}};
el('#live-follow').handlers.click();await new Promise(r=>setImmediate(r));
// Navigating during token lookup cannot retarget a retry to another Voice.
let releaseStorage,posted;
ctx.fetch=async(url,options)=>{if(url==='/api/storage')return await new Promise(resolve=>{releaseStorage=()=>resolve({ok:true,json:async()=>({open_token:'test-token'})})});posted=JSON.parse(options.body);return {ok:true,json:async()=>({status:'retry_requested'})}};
const retryTask=el('#live-retry-translation').handlers.click();
live.unmount();live.mount({...data(1),state:{...data(1).state,id:'another-run'}},{});
releaseStorage();await retryTask;assert.equal(posted.run,'synthetic','Retry kept the clicked run');
live.unmount();assert.equal(timers.size,0);console.log('Passed live behavior: initial follow, resize, delayed translation, next segment, pause and resume.');
})().catch(e=>{console.error(e);process.exitCode=1});

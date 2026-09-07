// Isolated browser-controller tests: no learner archive or model calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../assets/library/app.js'), 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));

function browser(hash, responder) {
  const elements = new Map(), calls = [], timers = new Map(), redirects = [];
  let timerId = 0;
  const element = id => {
    if(!elements.has(id)) elements.set(id, {innerHTML:'',textContent:'',dataset:{},
      close(){},addEventListener(){},setAttribute(){},removeAttribute(){},
      classList:{toggle(){},remove(){}},getBoundingClientRect(){return {};}});
    return elements.get(id);
  };
  const location = {hash,replace(value){redirects.push(value);this.hash=value;}};
  const document = {body:element('body'),hidden:false,title:'',querySelector:element,querySelectorAll:()=>[],addEventListener(){}};
  const context = vm.createContext({document,location,URLSearchParams,Date,console,AbortSignal,
    window:{addEventListener(){},scrollTo(){}},
    setTimeout(fn){timers.set(++timerId,fn);return timerId;},clearTimeout(id){timers.delete(id);},
    async fetch(url,options){calls.push(url);return {ok:true,json:async()=>responder(url,options)};}});
  vm.runInContext(source,context);
  return {context,elements,calls,timers,redirects,location,document,
    async tick(){const [id,fn]=[...timers][0];timers.delete(id);await fn();await flush();}};
}

const meta = {revision:'fictional-revision',source_updated_at:'2026-01-01T12:00:00+00:00'};
const overview = {...meta,profile:{goal:'Synthetic goal'},today:'2026-01-01'};
const lesson = {...meta,id:'SES-20260101-002',date:'2026-01-01',title:'Synthetic review',
  book:'Test',summary:'Only a fixture',excerpts:[],expression_count:0,source_ids:[]};

(async()=>{
  let saved = false;
  const first = browser('#review?thread=one&voice=two',url=>url.startsWith('/api/review')
    ? {...meta,status:saved?'saved':'waiting',session_id:saved?lesson.id:null} : overview);
  await flush();
  assert.equal(first.calls[0],'/api/review?thread=one&voice=two');
  assert.match(first.elements.get('#content').innerHTML,/等待课后整理开始/);
  assert.equal(first.redirects.length,0);
  first.document.hidden=true;
  const count=first.calls.length;await first.tick();assert.equal(first.calls.length,count);
  first.document.hidden=false;saved=true;await first.tick();
  assert.deepEqual(first.redirects,['#sessions/'+lesson.id]);

  let release;
  const pending=new Promise(resolve=>{release=resolve;});
  const second=browser('#review?thread=one&voice=two',url=>url.startsWith('/api/review')?pending:lesson);
  second.location.hash='#sessions/'+lesson.id;
  await vm.runInContext('render()',second.context);
  release({...meta,status:'saved',session_id:'SES-20260101-999'});
  await flush();
  assert.equal(second.redirects.length,0,'A late response must not redirect a different route');

  const third=browser('#sessions/'+lesson.id,url=>url==='/api/overview'?new Promise(()=>{}):lesson);
  await flush();
  assert.equal(third.calls[0],'/api/sessions/'+lesson.id);
  assert.match(third.elements.get('#content').innerHTML,/Synthetic review/,
    'The lesson must render while background overview loading remains unresolved');
  const animations=[],attrs=new Map();
  const face=()=>({attrs:{},setAttribute(k,v){this.attrs[k]=v;}}),front=face(),back=face();
  const inner={animate(frames){let done,fail;const finished=new Promise((r,j)=>{done=r;fail=j;});const a={finished,done,cancel(){fail(new Error('cancelled'));},frames};animations.push(a);return a;}};
  const button={dataset:{answer:'back',frontLabel:'Chinese',backLabel:'English'},setAttribute(k,v){attrs.set(k,v)},querySelector(s){return s==='.flip-inner'?inner:front;}};
  third.document.getElementById=()=>back;third.context.button=button;third.context.matchMedia=()=>({matches:false});
  vm.runInContext('setAnswer(button,true)',third.context);
  vm.runInContext('setAnswer(button,false)',third.context);
  vm.runInContext('setAnswer(button,true)',third.context);
  await flush();animations.at(-1).done();await flush();animations.at(-1).done();await flush();
  assert.equal(front.attrs['aria-hidden'],'true');assert.equal(back.attrs['aria-hidden'],'false');
  assert.equal(attrs.get('aria-expanded'),'true');
  for(const a of animations)for(const f of a.frames)assert.match(f.transform,/^scaleX\((1|\.02)\)$/,'Every animation frame uses a positive scale');
  third.context.matchMedia=()=>({matches:true});await vm.runInContext('setAnswer(button,false)',third.context);
  assert.equal(front.attrs['aria-hidden'],'false');assert.equal(back.attrs['aria-hidden'],'true');
  let job={...meta,thread_id:'one',voice_id:'two',title:'Current bakery',created_epoch:2,status:'preparing'};
  const durable=browser('#review?thread=one&voice=two',url=>url==='/api/reviews'?{...meta,items:[job]}:url.startsWith('/api/review?')?job:url==='/api/overview'?overview:lesson);
  await flush();
  durable.location.hash='#sessions/'+lesson.id;
  await vm.runInContext('render()',durable.context);
  await vm.runInContext('refreshReviews()',durable.context);
  assert.match(durable.elements.get('#review-notice').innerHTML,/Current bakery/);
  assert.match(durable.elements.get('#review-notice').innerHTML,/查看整理进度/);
  job={...job,status:'saved',session_id:'SES-20260101-003'};
  await vm.runInContext('refreshReviews()',durable.context);
  assert.equal(durable.redirects.length,0,'Saving while browsing an old lesson never pulls the learner away');
  assert.match(durable.elements.get('#review-notice').innerHTML,/#sessions\/SES-20260101-003/);
  assert.match(durable.elements.get('#review-notice').innerHTML,/打开复盘/);
  assert.match(durable.elements.get('#review-notice').innerHTML,/最近复盘已保存/);
  assert.doesNotMatch(durable.elements.get('#review-notice').innerHTML,/本次复盘已保存/);
  const unchanged=durable.elements.get('#review-notice').innerHTML;
  await vm.runInContext('refreshReviews()',durable.context);
  assert.equal(durable.elements.get('#review-notice').innerHTML,unchanged);
  durable.location.hash='#live?run=current-run';
  vm.runInContext("rememberReview({thread_id:'current',voice_id:'voice',run_id:'current-run',status:'practicing',title:'Current bus',created_epoch:3});paintReviewNotice()",durable.context);
  assert.match(durable.elements.get('#review-notice').innerHTML,/练习进行中/);
  assert.match(durable.elements.get('#review-notice').innerHTML,/Current bus/);
  assert.doesNotMatch(durable.elements.get('#review-notice').innerHTML,/本次复盘已保存/);
  durable.location.hash='#sessions/'+lesson.id;
  const richer={...lesson,coaching_notes:['Give a relevant next step.'],excerpts:Array.from({length:5},(_,i)=>({id:'e'+i,original:'learner '+i,english:'Model '+i,chinese:'含义 '+i,note:'Untested review advice'})),review_priority_ids:['e0','e2'],card_count:6};
  durable.context.richer=richer;
  const html=vm.runInContext('lessonPage(richer)',durable.context);
  assert.match(html,/5 组完整表达 · 6 张词句卡/);assert.match(html,/展开其余 3 组表达/);
  assert.match(html,/教练下次如何调整/);assert.match(html,/Give a relevant next step/);
  for(let i=0;i<5;i++)assert.match(html,new RegExp('Model '+i));
  const delayed=vm.runInContext("reviewMessage({status:'needs_attention',elapsed_seconds:1000})",durable.context);
  assert.doesNotMatch(delayed.title,/中断/,'Elapsed time alone cannot prove the job stopped');
  const guide={kind:'suggestion',groups:[{text:'Could I try this on?',stress:['try']}],tone:'rise',tone_note:'A possible question.',memory:[{text:'Could I …?',meaning:'Ask politely <script>'}]};
  durable.context.guided={...richer.excerpts[0],english:'Could I try this on?',reading_guide:guide};
  const annotated=vm.runInContext('excerpt(guided)',durable.context);
  assert.match(annotated,/<strong>try<\/strong>/);
  assert.match(annotated,/&lt;script&gt;/);assert.doesNotMatch(annotated,/<script>/);
  assert.match(annotated,/<p class="model" lang="en">Could I try this on\?<\/p>/);
  assert.doesNotMatch(annotated,/<details class="reading-guide"[^>]* open/,'Hints are opt-in');
  const unannotated=vm.runInContext('excerpt(richer.excerpts[0])',durable.context);
  assert.doesNotMatch(unannotated,/reading-guide/,'Old records remain usable without fabricated annotations');
  let openOptions,opens=0;
  const folder=browser('#storage',(url,options)=>{
    if(url==='/api/storage/open'){opens++;openOptions=options;return {message:'Requested'};}
    if(url==='/api/storage')return {data_root:'/fictional/records',open_token:'server-token'};
    return overview;
  });
  await flush();assert.doesNotMatch(folder.elements.get('#content').innerHTML,/这次没有读到记录/);folder.context.folderButton={disabled:false};
  await vm.runInContext('openLearningFolder(folderButton)',folder.context);
  assert.equal(opens,1);assert.equal(openOptions.method,'POST');assert.equal(openOptions.body,'{}');
  assert.equal(openOptions.headers['X-Coach-Token'],'server-token');
  assert.equal(folder.context.folderButton.disabled,false);
  console.log('Passed page checks: exact review, stale response, nonblocking lesson, rapid flip reversals, reduced motion, persistent review navigation, full coverage and coach feedback.');
})().catch(error=>{console.error(error);process.exitCode=1;});

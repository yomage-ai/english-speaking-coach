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
  const document = {hidden:false,title:'',querySelector:element,querySelectorAll:()=>[],addEventListener(){}};
  const context = vm.createContext({document,location,URLSearchParams,Date,console,
    window:{addEventListener(){},scrollTo(){}},
    setTimeout(fn){timers.set(++timerId,fn);return timerId;},clearTimeout(id){timers.delete(id);},
    async fetch(url){calls.push(url);return {ok:true,json:async()=>responder(url)};}});
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
  assert.match(first.elements.get('#content').innerHTML,/尚未保存/);
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
  console.log('Passed 3 page update checks (exact route, stale response, nonblocking lesson).');
})().catch(error=>{console.error(error);process.exitCode=1;});

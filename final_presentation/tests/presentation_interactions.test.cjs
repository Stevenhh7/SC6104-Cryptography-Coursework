// DOM-independent checks of the actual presentation event handlers.
// Browser layout and transitions are checked separately in the live preview.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.argv[2] || path.resolve(__dirname, '..');
const checks = [];
function node() {
  return {
    handlers: {}, attributes: {}, children: [], dataset: {}, style: {},
    textContent: '', innerHTML: '', hidden: false,
    classList: {add(){}, remove(){}, toggle(){}},
    addEventListener(type, fn){this.handlers[type] = fn;},
    setAttribute(name, value){this.attributes[name] = value;},
    append(...children){this.children.push(...children);},
    replaceChildren(...children){this.children=[...children];},
    querySelectorAll(){return [];}, closest(){return null;}
  };
}
function environment(page, embedded = true) {
  const nodes = new Map(), intervals = new Map(); let intervalId = 0;
  const document = {...node(), body: {...node(), dataset: {page, embedded: String(embedded)}},
    getElementById(id){if(!nodes.has(id))nodes.set(id,node()); return nodes.get(id);},
    createElement: node, createTextNode: value=>({textContent:String(value)}), querySelector(){return null;}, querySelectorAll(){return [];}};
  const parent = {messages: [], postMessage(data){this.messages.push(data);}};
  const window = {...node(), location: {origin:'http://localhost', href:''}, parent,
    matchMedia(){return {matches:false};},
    RSAMotion: {capture(){return null;},play(){},patch(target, markup){target.innerHTML=markup;}}};
  if(!embedded)window.parent=window;
  const context = vm.createContext({window, document, console,
    sessionStorage:{getItem(){return null;},setItem(){}},
    setInterval(fn){intervals.set(++intervalId,fn);return intervalId;},
    clearInterval(id){intervals.delete(id);}});
  return {nodes, intervals, document, window, parent, context,
    load(name){vm.runInContext(fs.readFileSync(path.join(root,'presentation/assets',name),'utf8'),context,{filename:name});},
    key(key){document.handlers.keydown({key,target:node(),preventDefault(){}});},
    click(id){document.getElementById(id).handlers.click();}};
}
function animation(page,embedded=true){
  const env=environment(page,embedded);
  env.load('math.js');env.load('verified-data.js');env.load('final-data.js');env.load('slides.js');return env;
}
for(const [page,count] of [['attack',6],['batch',8],['edges',5]]){
  const e=animation(page);
  for(let i=1;i<count;i++)e.click('next');
  assert.equal(e.nodes.get('progress-text').textContent,`${count} / ${count}`);
  assert.equal(e.nodes.get('next').disabled,true);
  e.click('previous');assert.equal(e.nodes.get('progress-text').textContent,`${count-1} / ${count}`);
  e.click('play');for(const tick of [...e.intervals.values()])tick();
  assert.equal(e.intervals.size,0);assert.equal(e.nodes.get('play').attributes['aria-pressed'],'false');
  e.click('restart');assert.equal(e.nodes.get('progress-text').textContent,`1 / ${count}`);
  e.click('play');assert.equal(e.intervals.size,1);
  e.window.handlers.message({source:e.parent,origin:'http://localhost',data:{type:'rsa-presentation:visibility',active:false}});
  assert.equal(e.intervals.size,0);assert.equal(e.nodes.get('progress-text').textContent,`1 / ${count}`);
  e.key('PageDown');assert.equal(e.parent.messages.at(-1).delta,1);assert.equal(e.window.location.href,'');
  e.key('PageUp');assert.equal(e.parent.messages.at(-1).delta,-1);
  e.key('3');assert.equal(e.parent.messages.at(-1).page,3);
  checks.push(`${page}: forward/back, restart, automatic stop, hidden pause, deck navigation`);
}
const edges=animation('edges');for(let i=0;i<3;i++)edges.click('next');
edges.nodes.get('scene-content').handlers.change({target:{id:'fallback',checked:false}});
assert.equal(edges.nodes.get('step-title').textContent,'Preserve the unresolved state');
assert.match(edges.nodes.get('scene-content').innerHTML,/budget: 0/);
assert.doesNotMatch(edges.nodes.get('scene-content').innerHTML,/factor_found/);
edges.nodes.get('scene-content').handlers.change({target:{id:'fallback',checked:true}});
assert.equal(edges.nodes.get('step-title').textContent,'Split with pairwise fallback');
assert.match(edges.nodes.get('scene-content').innerHTML,/factor_found/);
checks.push('fallback off preserves unresolved; fallback on restores factor recovery');
const standalone=animation('attack',false);standalone.key('PageDown');
assert.equal(standalone.window.location.href,'batch-gcd.html');
checks.push('standalone page navigation preserved');
const deck=environment('');
const slides=Array.from({length:8},(_,index)=>{
  const slide=node();slide.dataset.title=`title-${index}`;
  const frame=index>=1&&index<=3?{...node(),contentWindow:{messages:[],postMessage(data){this.messages.push(data);}}}:null;
  slide.querySelector=()=>frame;return slide;
});
deck.document.querySelectorAll=selector=>selector==='.slide'?slides:[];
const demoButtons = Array.from({length:4}, (_,i)=>{const button=node(), li=node();button.dataset.demoStep=String(i);button.closest=()=>li;return button;});
const evidencePanel=node();
deck.document.querySelector=selector=>selector==='.demo-evidence'?evidencePanel:null;
deck.document.querySelectorAll=selector=>selector==='.slide'?slides:selector==='[data-demo-step]'?demoButtons:[];
deck.load('final-data.js');
deck.load('final.js');
deck.nodes.get('pages').children[1].handlers.click();
assert.equal(deck.nodes.get('page-label').textContent,'2 / 8');
const attackWindow=slides[1].querySelector().contentWindow;
deck.window.handlers.message({source:attackWindow,origin:'http://localhost',data:{type:'rsa-presentation:turn',delta:1}});
assert.equal(deck.nodes.get('page-label').textContent,'3 / 8');
assert.equal(attackWindow.messages.at(-1).active,false);
assert.equal(slides[2].querySelector().contentWindow.messages.at(-1).active,true);
// Inactive iframe messages must not change the current deck page.
deck.window.handlers.message({source:attackWindow,origin:'http://localhost',data:{type:'rsa-presentation:turn',delta:1}});
assert.equal(deck.nodes.get('page-label').textContent,'3 / 8');
deck.window.handlers.message({source:slides[2].querySelector().contentWindow,origin:'http://localhost',data:{type:'rsa-presentation:select',page:3}});
assert.equal(deck.nodes.get('page-label').textContent,'4 / 8');
deck.window.handlers.message({source:slides[3].querySelector().contentWindow,origin:'http://localhost',data:{type:'rsa-presentation:turn',delta:1}});
assert.equal(deck.nodes.get('page-label').textContent,'5 / 8');
checks.push('deck page labels, active-frame navigation, pause dispatch and edge-page exit');
assert.equal(deck.nodes.get('timings').children.length,4);
assert.match(deck.nodes.get('speedup').textContent,/32.8/);
assert.match(deck.nodes.get('timeout-note').textContent,/No speedup/);
assert.equal(deck.nodes.get('control-rows').children.length,5);
assert.equal(deck.nodes.get('pool-bars').children.length,3);
assert.equal(deck.nodes.get('control-count').textContent,10);
assert.equal(deck.nodes.get('negative-count').textContent,2);
for(let i=0;i<3;i++)deck.click('reveal');
assert.equal(deck.nodes.get('reveal').disabled,true);
assert.equal(deck.nodes.get('verification').hidden,false);
assert.equal(deck.nodes.get('demo-number').children[0].textContent,'6');
demoButtons[1].handlers.click();
assert.equal(deck.nodes.get('demo-number').children[0].textContent,'5');
assert.equal(deck.nodes.get('plaintext').hidden,true);
deck.click('reset');
assert.equal(deck.nodes.get('public-boundary').hidden,false);
assert.equal(deck.nodes.get('demo-number').children[0].textContent,'100');
const embeddedProof=animation('attack');
assert.match(embeddedProof.nodes.get('side-proof').innerHTML,/100 distinct moduli.*5 keys recovered/);
embeddedProof.key('n');
assert.equal(embeddedProof.nodes.get('notes').hidden,true);
assert.match(standalone.nodes.get('side-proof').innerHTML,/14 unique moduli/);
checks.push('actual experiment data, stage selection, reset, unified embedded evidence and hidden notes');
console.log(JSON.stringify({passed:true,checks},null,2));

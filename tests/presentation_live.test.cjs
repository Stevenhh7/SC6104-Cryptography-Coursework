// Exercise the real live UI handler with chunked responses; no browser emulation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const code = fs.readFileSync(path.join(__dirname, '../presentation/assets/live.js'), 'utf8');
function node() {
  const classes = new Set();
  return {handlers:{},textContent:'',hidden:false,disabled:false,children:[],
    classList:{toggle(name,yes){if(yes)classes.add(name);else classes.delete(name);},contains(name){return classes.has(name);}},
    addEventListener(type,fn){this.handlers[type]=fn;},append(child){this.children.push(child);},replaceChildren(){this.children=[];}};
}
async function environment({events=[],protocol='http:',unavailable=false,networkError=false}={}) {
  const nodes=new Map(),stages=Array.from({length:5},node);
  const byId=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
  const document={getElementById:byId,createElement:node,querySelectorAll(){return stages;}};
  const fetch=async(url,options={})=>{
    if(url.endsWith('/status')){if(unavailable)throw Error('offline');return {ok:true,json:async()=>({runner:'rsa-presentation-v1',busy:false,python:'3.13.3'})};}
    if(networkError)throw Error('connection lost');
    assert.equal(options.method,'POST');assert.equal(options.body,'{}');
    const bytes=Buffer.from(events.map(event=>JSON.stringify(event)).join('\n')+'\n');let offset=0;
    return {ok:true,headers:{get:()=> 'application/x-ndjson; charset=utf-8'},body:{getReader:()=>({
      async read(){if(offset===bytes.length)return {done:true};const next=Math.min(offset+17,bytes.length);const value=bytes.subarray(offset,next);offset=next;return {value,done:false};},async cancel(){}
    })}};
  };
  vm.runInNewContext(code,{window:{location:{protocol}},document,fetch,AbortSignal,TextDecoder,Uint8Array,Date,console,setTimeout});
  await new Promise(setImmediate);
  return {nodes,stages,byId};
}
(async()=>{
  let env=await environment({protocol:'file:'});
  assert.equal(env.byId('live-run').disabled,true);assert.match(env.byId('live-status').textContent,/Offline/);
  env=await environment({unavailable:true});assert.match(env.byId('live-status').textContent,/unavailable/);
  env=await environment({events:[{type:'stage',stage:0,text:'Actual input → 密文'}, {type:'output',text:'stdout'}, {type:'result',passed:true,factorable:5,messages:6,repaired_found:0,elapsed_seconds:1.5,finished_at:new Date().toISOString(),backend:'gmpy2/GMP'}]});
  assert.equal(env.byId('live-run').disabled,false);
  await env.byId('live-run').handlers.click();
  assert.match(env.byId('live-status').textContent,/Passed/);
  assert.match(env.byId('live-output').textContent,/Actual input → 密文/);
  assert.equal(env.byId('live-result').hidden,false);assert.equal(env.byId('live-result').children.length,4);
  assert.equal(env.stages.every(stage=>stage.classList.contains('complete')),true);
  for(const options of [{events:[{type:'output',text:'partial output'}]}, {networkError:true}, {events:[{type:'stage',stage:2,text:'Recovering'},{type:'error',text:'Invalid factor'}]}]) {
    env=await environment(options);await env.byId('live-run').handlers.click();
    assert.equal(env.byId('live-result').hidden,true);assert.match(env.byId('live-status').textContent,/did not complete/);
    assert.match(env.byId('live-output').textContent,/ERROR:/);assert.equal(env.byId('live-run').disabled,false);
  }
  console.log('PASS: offline / unavailable runner, streamed UTF-8 success, partial stream, connection loss and pipeline error.');
})().catch(error=>{console.error(error);process.exitCode=1;});

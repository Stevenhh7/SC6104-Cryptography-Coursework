(() => {
  'use strict';
  const data=window.RSA_FINAL_DATA, slides=[...document.querySelectorAll('.slide')];
  const byId=id=>document.getElementById(id);
  const labels=['Research goal','Shared primes','Batch GCD','Edge cases','Performance','Public-input attack','Key replacement','Conclusion'];
  let page=0,demoStep=0;
  function show(index){
    page=Math.max(0,Math.min(slides.length-1,index));
    slides.forEach((slide,i)=>{slide.hidden=i!==page;});
    byId('time').textContent=slides[page].dataset.time;
    byId('page-label').textContent=(page+1)+' / '+slides.length;
    byId('previous').disabled=page===0;byId('next').disabled=page===slides.length-1;
    [...byId('pages').children].forEach((button,i)=>button.setAttribute('aria-current',i===page?'page':'false'));
  }
  labels.forEach((label,i)=>{const button=document.createElement('button');button.type='button';button.textContent=i+1;button.title=label;button.setAttribute('aria-label',(i+1)+'. '+label);button.addEventListener('click',()=>show(i));byId('pages').append(button);});
  byId('previous').addEventListener('click',()=>show(page-1));byId('next').addEventListener('click',()=>show(page+1));
  document.addEventListener('keydown',event=>{if(document.querySelector('dialog[open]')||event.target.closest('button,a,input'))return;if(event.key==='ArrowRight'||event.key==='PageDown'){event.preventDefault();show(page+1);}if(event.key==='ArrowLeft'||event.key==='PageUp'){event.preventDefault();show(page-1);}});
  byId('fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(_){byId('fullscreen').textContent='Use browser full screen';}});
  document.querySelectorAll('[data-dialog]').forEach(button=>button.addEventListener('click',()=>byId(button.dataset.dialog).showModal()));
  document.querySelectorAll('[data-close]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
  function cells(parent,values){const tr=document.createElement('tr');values.forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});parent.append(tr);}
  if(!data){byId('performance-title').textContent='Measured data not loaded';show(0);return;}
  data.performance.forEach(row=>cells(byId('timings'),[row.size.toLocaleString('en-US'),row.pairwise===null?'3/3 timed out':row.pairwise.toFixed(3)+' s',row.batch.toFixed(3)+' s']));
  const last=data.performance[data.performance.length-1];
  byId('performance-title').textContent=last.size.toLocaleString('en-US')+' moduli scanned in '+last.batch.toFixed(3)+' seconds';
  const comparable=data.performance.filter(row=>row.pairwise!==null).slice(-1)[0];
  byId('speedup').textContent=(comparable.pairwise/comparable.batch).toFixed(1)+'× faster at '+comparable.size.toLocaleString('en-US')+' moduli';
  byId('timeout-note').textContent='Pairwise at '+last.size.toLocaleString('en-US')+': all three workers exceeded '+data.benchmark_config.worker_timeout_seconds+' s. No speedup is calculated for that size.';
  const stageLabels={preprocess:'preprocessing',conversion:'backend conversion',product_tree:'product tree',remainder_tree:'remainder tree',final_gcd:'final GCD',fallback:'fallback',assemble:'result assembly'};
  const dominant=Object.entries(data.stages).sort((a,b)=>b[1]-a[1])[0];
  byId('dominant-stage').textContent='Largest measured component at '+last.size.toLocaleString('en-US')+' moduli: '+stageLabels[dominant[0]]+' ('+dominant[1].toFixed(3)+' s).';
  byId('before').textContent=data.demo.correctly_factored_moduli;byId('after').textContent=data.repaired_found;
  byId('roundtrip').textContent=data.repair.replaced_unique_moduli+' keys replaced. '+data.repair.new_key_roundtrip_records+' new messages passed legitimate OAEP round trips.';
  byId('attack-title').textContent=data.input.record_count+' records. '+data.input.unique_moduli+' distinct RSA moduli.';
  byId('fallback-detail').textContent=data.fallback_candidates+' full-overlap candidates, '+data.fallback_checks+' fallback GCD checks';
  byId('reconstruction-key').textContent='Recovered key: '+data.reconstruction.id;
  const checks=[['Modulus',data.reconstruction.bits+' bits'],['Public exponent',data.reconstruction.e],['Factors',data.reconstruction.p_bits+' + '+data.reconstruction.q_bits+' bits'],['p × q = n',data.reconstruction.factor_product_verified?'Verified':'Failed'],['e × d mod λ(n) = 1',data.reconstruction.inverse_verified?'Verified':'Failed']];
  checks.forEach(([name,value])=>{const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=name;dd.textContent=value;byId('reconstruction-checks').append(dt,dd);});
  const names={normal:'Fresh independent primes',duplicates_only:'Duplicates only',isolated_target:'Isolated weak target',shared_prime_demo:'Shared-prime demo',repaired:'Replaced keys'};
  data.controls.cases.filter(row=>row.algorithm==='batch').forEach(row=>cells(byId('control-rows'),[names[row.case],row.records+' / '+row.unique_moduli,row.correctly_factored,row.verified_messages]));
  byId('controls-status').textContent=data.controls.summary.scan_runs+' scans verified. Wrong OAEP label and corrupted ciphertext both rejected.';
  data.pool.forEach(row=>cells(byId('pool-rows'),[row.size,(row.median*100).toFixed(1)+'%']));
  function reveal(){
    document.querySelectorAll('.attack-steps li').forEach((li,i)=>li.classList.toggle('complete',i<=demoStep));
    byId('evidence-label').textContent=['PUBLIC INPUT','DETECTION RESULT','OAEP PLAINTEXT','VERIFIED RECOVERY'][demoStep];
    const count=demoStep===0?data.input.unique_moduli:demoStep===1?data.demo.correctly_factored_moduli:data.demo.verified_decryption_records;
    const label=demoStep===0?'distinct 2048-bit moduli':demoStep===1?'distinct keys factorable':'messages recovered';
    byId('demo-number').replaceChildren(document.createTextNode(count));const span=document.createElement('span');span.textContent=label;byId('demo-number').append(span);
    byId('demo-detail').textContent=demoStep===0?(data.input.record_count-data.input.unique_moduli)+' duplicate records preserve their original identities.':demoStep===1?'One shared-prime pair and one full-overlap triangle.':data.demo.verified_decryption_moduli+' distinct keys. One duplicated weak key accounts for the extra message.';
    byId('plaintext').hidden=demoStep<2;byId('plaintext').textContent=data.messages.slice(0,3).map(row=>row.plaintext_utf8).join('\n')+'\n… '+(data.messages.length-3)+' more messages recovered';
    byId('verification').hidden=demoStep<3;byId('verification').textContent='False positives: '+data.demo.false_positives+'. False negatives: '+data.demo.false_negatives+'. All '+data.demo.verified_decryption_records+' plaintexts match.';
    byId('reveal').textContent=['Show detection','Decrypt OAEP','Verify results','Verified'][demoStep];byId('reveal').disabled=demoStep===3;
  }
  byId('reveal').addEventListener('click',()=>{demoStep=Math.min(3,demoStep+1);reveal();});byId('reset').addEventListener('click',()=>{demoStep=0;reveal();});
  reveal();show(0);
})();

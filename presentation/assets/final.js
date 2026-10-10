(() => {
  'use strict';
  const data = window.RSA_FINAL_DATA;
  const slides = [...document.querySelectorAll('.slide')];
  const byId = id => document.getElementById(id);
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let page = 0, demoStep = 0, pageAnimation, evidenceAnimation;

  function syncFrame(slide, index) {
    slide.querySelector('iframe')?.contentWindow?.postMessage({type: 'rsa-presentation:visibility', active: index === page}, '*');
  }
  function show(index) {
    const previous = page;
    page = Math.max(0, Math.min(slides.length - 1, index));
    pageAnimation?.cancel();
    slides.forEach((slide, i) => { slide.hidden = i !== page; syncFrame(slide, i); });
    byId('section-label').textContent = slides[page].dataset.title;
    byId('page-label').textContent = `${page + 1} / ${slides.length}`;
    byId('previous').disabled = page === 0;
    byId('next').disabled = page === slides.length - 1;
    [...byId('pages').children].forEach((button, i) => button.setAttribute('aria-current', i === page ? 'page' : 'false'));
    byId('pages').children[page]?.scrollIntoView?.({block: 'nearest', inline: 'nearest', behavior: 'auto'});
    if (previous !== page && !reducedMotion.matches && slides[page].animate) {
      pageAnimation = slides[page].animate([{opacity: 0, transform: 'translateY(8px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: 300, easing: 'cubic-bezier(.2,.7,.2,1)'});
    }
  }
  slides.forEach((slide, i) => {
    slide.querySelector('iframe')?.addEventListener('load', () => syncFrame(slide, i));
    const button = document.createElement('button');
    button.type = 'button'; button.textContent = i + 1; button.title = slide.dataset.title;
    button.setAttribute('aria-label', `${i + 1}. ${slide.dataset.title}`);
    button.addEventListener('click', () => show(i)); byId('pages').append(button);
  });
  window.addEventListener('message', event => {
    const frame = slides[page].querySelector('iframe');
    if (!frame || event.source !== frame.contentWindow || event.origin !== window.location.origin) return;
    const message = event.data;
    if (message?.type === 'rsa-presentation:turn' && (message.delta === 1 || message.delta === -1)) show(page + message.delta);
    else if (message?.type === 'rsa-presentation:select' && Number.isInteger(message.page) && message.page >= 1 && message.page <= 3) show(message.page);
  });
  byId('previous').addEventListener('click', () => show(page - 1));
  byId('next').addEventListener('click', () => show(page + 1));
  document.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey || document.querySelector('dialog[open]') || event.target.closest('input,select,textarea')) return;
    if (event.key === 'ArrowRight' || event.key === 'PageDown') { event.preventDefault(); show(page + 1); }
    else if (event.key === 'ArrowLeft' || event.key === 'PageUp') { event.preventDefault(); show(page - 1); }
  });
  byId('fullscreen').addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch (_) { byId('fullscreen').textContent = 'Use browser full screen'; }
  });
  document.addEventListener('fullscreenchange', () => { byId('fullscreen').textContent = document.fullscreenElement ? 'Exit full screen' : 'Full screen'; });
  document.querySelectorAll('[data-dialog]').forEach(button => button.addEventListener('click', () => byId(button.dataset.dialog).showModal()));
  document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
  function cells(parent, values) {
    const tr = document.createElement('tr');
    values.forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
    parent.append(tr);
  }
  if (!data) { byId('performance-title').textContent = 'Experiment data unavailable'; show(0); return; }
  byId('cover-moduli').textContent = data.input.unique_moduli;
  byId('cover-recovered').textContent = data.demo.correctly_factored_moduli;
  byId('cover-messages').textContent = data.demo.verified_decryption_records;
  const repeats = data.benchmark_config.repeats;
  byId('repeats-label').textContent = `${repeats} runs per condition`;
  data.performance.forEach(row => cells(byId('timings'), [row.size.toLocaleString('en-US'), row.pairwise === null ? `${repeats}/${repeats} timed out` : `${row.pairwise.toFixed(3)} s`, `${row.batch.toFixed(3)} s`]));
  const last = data.performance.at(-1);
  byId('performance-title').textContent = `${last.size.toLocaleString('en-US')} moduli scanned in ${last.batch.toFixed(3)} seconds`;
  const comparable = data.performance.filter(row => row.pairwise !== null).at(-1);
  byId('speedup').textContent = `${(comparable.pairwise / comparable.batch).toFixed(1)}× faster at ${comparable.size.toLocaleString('en-US')} moduli`;
  byId('timeout-note').textContent = `Pairwise at ${last.size.toLocaleString('en-US')}: all ${repeats} workers exceeded ${data.benchmark_config.worker_timeout_seconds} s. No speedup is calculated for that size.`;
  const stageLabels = {preprocess: 'preprocessing', conversion: 'backend conversion', product_tree: 'product tree', remainder_tree: 'remainder tree', final_gcd: 'final GCD', fallback: 'fallback', assemble: 'result assembly'};
  const dominant = Object.entries(data.stages).sort((a, b) => b[1] - a[1])[0];
  byId('dominant-stage').textContent = `Largest measured component at ${last.size.toLocaleString('en-US')} moduli: ${stageLabels[dominant[0]]} (${dominant[1].toFixed(3)} s).`;
  byId('before').textContent = data.demo.correctly_factored_moduli;
  byId('after').textContent = data.repaired_found;
  byId('roundtrip').textContent = `${data.repair.replaced_unique_moduli} keys replaced across ${data.repair.affected_records} records. ${data.repair.new_key_roundtrip_records} new messages passed legitimate OAEP round trips.`;
  byId('attack-title').textContent = `${data.input.record_count} records. ${data.input.unique_moduli} distinct RSA moduli.`;
  byId('fallback-detail').textContent = `${data.fallback_candidates} full-overlap candidates · ${data.fallback_checks} fallback GCD checks`;
  byId('reconstruction-key').textContent = `Recovered key: ${data.reconstruction.id}`;
  const checks = [['Modulus', `${data.reconstruction.bits} bits`], ['Public exponent', data.reconstruction.e], ['Factors', `${data.reconstruction.p_bits} + ${data.reconstruction.q_bits} bits`], ['p × q = N', data.reconstruction.factor_product_verified ? 'Verified' : 'Failed'], ['e × d mod λ(N) = 1', data.reconstruction.inverse_verified ? 'Verified' : 'Failed']];
  checks.forEach(([name, value]) => { const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = name; dd.textContent = value; byId('reconstruction-checks').append(dt, dd); });
  const names = {normal: 'Fresh independent primes', duplicates_only: 'Duplicates only', isolated_target: 'Isolated weak target', shared_prime_demo: 'Shared-prime demo', repaired: 'Replaced keys'};
  data.controls.cases.filter(row => row.algorithm === 'batch').forEach(row => cells(byId('control-rows'), [names[row.case], `${row.records} / ${row.unique_moduli}`, row.correctly_factored, row.verified_messages]));
  byId('controls-status').textContent = data.controls.summary.passed ? `${data.controls.summary.scan_runs} scans verified. Wrong OAEP label and corrupted ciphertext both rejected.` : 'Control validation failed.';
  byId('control-count').textContent = data.controls.cases.filter(row => row.passed).length;
  byId('negative-count').textContent = data.controls.oaep_checks.filter(row => row.passed).length;
  data.pool.forEach(row => {
    const percent = `${(row.median * 100).toFixed(1)}%`;
    cells(byId('pool-rows'), [row.size, percent]);
    const bar = document.createElement('div'); bar.className = 'pool-bar-row';
    const label = document.createElement('span'); label.textContent = `Pool ${row.size}`;
    const track = document.createElement('div'); track.className = 'pool-bar-track';
    const fill = document.createElement('div'); fill.className = 'pool-bar-fill'; fill.style.width = percent; track.append(fill);
    const value = document.createElement('b'); value.textContent = percent;
    bar.append(label, track, value); byId('pool-bars').append(bar);
  });
  const stepButtons = [...document.querySelectorAll('[data-demo-step]')];
  function showDemo(step, animate = true) {
    demoStep = Math.max(0, Math.min(3, step));
    evidenceAnimation?.cancel();
    stepButtons.forEach((button, i) => { button.setAttribute('aria-current', i === demoStep ? 'step' : 'false'); button.closest('li').classList.toggle('complete', i < demoStep); });
    byId('evidence-label').textContent = ['PUBLIC INPUT', 'DETECTION RESULT', 'OAEP PLAINTEXT', 'VERIFIED RECOVERY'][demoStep];
    const count = demoStep === 0 ? data.input.unique_moduli : demoStep === 1 ? data.demo.correctly_factored_moduli : data.demo.verified_decryption_records;
    const label = demoStep === 0 ? 'distinct 2048-bit moduli' : demoStep === 1 ? 'distinct keys factorable' : 'messages recovered';
    byId('demo-number').replaceChildren(document.createTextNode(count));
    const span = document.createElement('span'); span.textContent = label; byId('demo-number').append(span);
    byId('demo-detail').textContent = [
      `${data.input.record_count - data.input.unique_moduli} duplicate records preserve their original identities.`,
      'One shared-prime pair and one full-overlap triangle.',
      `${data.demo.verified_decryption_moduli} distinct keys. A duplicate weak key accounts for the extra message.`,
      'Separate ground truth confirms the factors and recovered plaintexts.'
    ][demoStep];
    byId('public-boundary').hidden = demoStep > 0;
    byId('plaintext').hidden = demoStep < 2;
    byId('plaintext').textContent = data.messages.slice(0, 3).map(row => row.plaintext_utf8).join('\n') + `\n… ${data.messages.length - 3} more messages recovered`;
    byId('verification').hidden = demoStep < 3;
    byId('verification').replaceChildren();
    [`${data.demo.false_positives} false positives`, `${data.demo.false_negatives} missed keys`, `${data.demo.verified_decryption_records} plaintexts verified`].forEach(text => { const badge = document.createElement('span'); badge.textContent = text; byId('verification').append(badge); });
    byId('reveal').textContent = ['Show detection', 'Show OAEP recovery', 'Verify results', 'Verified'][demoStep];
    byId('reveal').disabled = demoStep === 3;
    const panel = document.querySelector('.demo-evidence');
    if (animate && !reducedMotion.matches && panel?.animate) evidenceAnimation = panel.animate([{opacity: .25, transform: 'translateY(7px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: 380, easing: 'cubic-bezier(.2,.7,.2,1)'});
  }
  stepButtons.forEach(button => button.addEventListener('click', () => showDemo(Number(button.dataset.demoStep))));
  byId('reveal').addEventListener('click', () => showDemo(demoStep + 1));
  byId('reset').addEventListener('click', () => showDemo(0));
  showDemo(0, false); show(0);
})();

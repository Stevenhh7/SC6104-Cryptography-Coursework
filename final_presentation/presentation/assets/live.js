(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const run = byId('live-run'), status = byId('live-status'), output = byId('live-output');
  const stages = [...document.querySelectorAll('[data-live-stage]')];
  let running = false, events = [], activeStage = -1;
  function setStage(index, failed = false) {
    activeStage = index;
    stages.forEach((node, i) => { node.classList.toggle('complete', i < index); node.classList.toggle('active', i === index); node.classList.toggle('failed', i === index && failed); });
  }
  async function checkRunner() {
    if (running) return;
    run.disabled = true;
    if (!/^https?:$/.test(window.location.protocol)) { status.textContent = 'Offline copy · live execution requires the local presentation server.'; return; }
    try {
      const response = await fetch('/api/live/status', {cache: 'no-store', signal: AbortSignal.timeout(3000)});
      const data = await response.json();
      if (!response.ok || data.runner !== 'rsa-presentation-v1') throw new Error('No runner');
      status.textContent = data.busy ? 'Another pipeline is running.' : `Ready · Python ${data.python} · local execution`;
      run.disabled = data.busy;
    } catch (_) { status.textContent = 'Live runner unavailable · recorded results remain available.'; }
  }
  function consume(event) {
    events.push(event);
    if (Number.isInteger(event.stage)) setStage(event.stage);
    if (event.text) output.textContent += event.text + '\n';
    if (event.type === 'stage') status.textContent = event.text;
    if (event.type === 'result') {
      if (!event.passed) throw new Error('Pipeline verification failed.');
      const result = byId('live-result'); result.replaceChildren(); result.hidden = false;
      [`${event.factorable} keys recovered`, `${event.messages} plaintexts matched`, `${event.repaired_found} factors after replacement`, `${event.elapsed_seconds.toFixed(2)} s total`].forEach(text => { const badge = document.createElement('span'); badge.textContent = text; result.append(badge); });
      status.textContent = `Passed · ${new Date(event.finished_at).toLocaleTimeString()} · ${event.backend}`;
      setStage(stages.length);
    }
    if (event.type === 'error') throw new Error(event.text);
    output.scrollTop = output.scrollHeight;
  }
  run.addEventListener('click', async () => {
    if (running) return;
    running = true; run.disabled = true; byId('live-download').disabled = true;
    events = []; output.textContent = ''; byId('live-result').hidden = true; setStage(-1);
    status.textContent = 'Starting Python…';
    let reader;
    try {
      const response = await fetch('/api/live/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}', signal: AbortSignal.timeout(130000)});
      if (!response.ok) throw new Error(`Runner returned HTTP ${response.status}.`);
      if (!response.headers.get('content-type')?.includes('application/x-ndjson')) throw new Error('The server does not support live execution.');
      reader = response.body.getReader();
      const decoder = new TextDecoder(); let pending = '';
      while (true) {
        const chunk = await reader.read();
        pending += decoder.decode(chunk.value || new Uint8Array(), {stream: !chunk.done});
        const lines = pending.split('\n'); pending = lines.pop();
        for (const line of lines) if (line.trim()) consume(JSON.parse(line));
        if (chunk.done) break;
      }
      if (pending.trim()) consume(JSON.parse(pending));
      if (!events.some(event => event.type === 'result' && event.passed)) throw new Error('The stream ended before verification completed.');
    } catch (error) {
      status.textContent = 'Run did not complete';
      output.textContent += `\nERROR: ${error.message}\n`;
      byId('live-result').hidden = true; setStage(activeStage, true);
      if (reader) await reader.cancel().catch(() => {});
    } finally { running = false; run.disabled = false; byId('live-download').disabled = false; }
  });
  byId('live-download').addEventListener('click', () => {
    const blob = new Blob([output.textContent + '\n\nEVENTS\n' + JSON.stringify(events, null, 2)], {type: 'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(blob), anchor = document.createElement('a');
    anchor.href = url; anchor.download = `rsa-live-run-${new Date().toISOString().replace(/[:.]/g, '-')}.txt`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  byId('open-live').addEventListener('click', checkRunner);
  checkRunner();
})();

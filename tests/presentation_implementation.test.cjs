// Run the two real code-page scripts and the embed bridge with a small DOM stub.
// These are behavior and source checks, not browser rendering checks.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.argv[2] || path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8').replace(/\r\n/g, '\n');
const decode = value => value.replace(/&(quot|lt|gt|amp|#x27|#39);/g,
  (_, entity) => ({quot:'"', lt:'<', gt:'>', amp:'&', '#x27':"'", '#39':"'"})[entity]);
function node() {
  const value = {
    handlers: {}, attributes: {}, children: [], dataset: {}, textContent: '', open: false,
    classes: new Set(),
    classList: {toggle(name, enabled) { if (enabled) this.owner.classes.add(name); else this.owner.classes.delete(name); }},
    addEventListener(type, callback) { this.handlers[type] = callback; },
    setAttribute(name, value) { this.attributes[name] = value; },
    append(child) { this.children.push(child); },
    replaceChildren() { this.children = []; },
    closest() { return null; },
    showModal() { this.open = true; }, close() { this.open = false; }
  };
  value.classList.owner = value;
  return value;
}
function loadPage(name, embedded = true, origin = 'http://localhost') {
  const markup = read(`presentation/embed/${name}-key-implementation.html`);
  const nodes = new Map([...markup.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], node()]));
  const dialogs = [...markup.matchAll(/<dialog id="([^"]+)"/g)].map(match => nodes.get(match[1]));
  const traceButtons = [...markup.matchAll(/<button data-trace="(\d+)"/g)].map(match => {
    const button = node(); button.dataset.trace = match[1]; return button;
  });
  const traceData = markup.match(/<script id="trace-data" type="application\/json">([\s\S]*?)<\/script>/);
  if (traceData) nodes.get('trace-data').textContent = traceData[1];
  const validationData = markup.match(/<script id="validation-data" type="application\/json">([\s\S]*?)<\/script>/);
  if (validationData) nodes.get('validation-data').textContent = validationData[1];
  const caseButtons = validationData ? JSON.parse(validationData[1]).map(item => {
    const button = node(); button.dataset.case = item.id; return button;
  }) : [];
  const exampleButtons = [...markup.matchAll(/data-example="(\d+)"/g)].map(match => {
    const button = node(); button.dataset.example = match[1]; return button;
  });
  const coreMarkup = markup.match(/<pre class="core"[^>]*>([\s\S]*?)<\/pre>/)?.[1] || '';
  const coreLines = [...coreMarkup.matchAll(/data-step="([^"]*)"/g)].map(match => {
    const line = node(); line.dataset.step = match[1]; return line;
  });
  const document = {...node(), body:{dataset:{embedded:String(embedded)}},
    getElementById: id => { assert.ok(nodes.has(id), `Missing element ${id}`); return nodes.get(id); },
    createElement: node,
    querySelector: selector => selector === 'dialog[open]' ? dialogs.find(dialog => dialog.open) || null : null,
    querySelectorAll: selector => ({'[data-trace]':traceButtons, '[data-case]':caseButtons, '[data-example]':exampleButtons, '.core .code-line':coreLines, 'dialog[open]':dialogs.filter(dialog => dialog.open)})[selector] || []
  };
  const parent = {messages:[], postMessage(data) { this.messages.push(data); }};
  const window = {...node(), parent, location:{origin}};
  if (!embedded) window.parent = window;
  const context = vm.createContext({document, window, console});
  for (const match of markup.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
    if (/\bsrc=|application\/json/.test(match[1])) continue;
    vm.runInContext(match[2], context, {filename:`${name}-inline.js`});
  }
  vm.runInContext(read('presentation/assets/implementation-embed.js'), context);
  return {nodes, dialogs, traceButtons, caseButtons, exampleButtons, coreLines, document, window, parent,
    click(id) { nodes.get(id).handlers.click(); },
    key(key, extras = {}) {
      let prevented = false;
      document.handlers.keydown?.({key, target:node(), preventDefault(){prevented = true;}, ...extras});
      return prevented;
    },
    hidden(extras = {}) {
      window.handlers.message?.({source:parent, origin, data:{type:'rsa-presentation:visibility', active:false}, ...extras});
    }
  };
}
const checks = [];
for (const name of ['a', 'b']) {
  const page = loadPage(name);
  const secondary = name === 'a' ? 'trace' : 'oaep';
  for (const dialog of ['source', secondary]) {
    page.click(`show-${dialog}`); assert.equal(page.nodes.get(`${dialog}-dialog`).open, true);
    const before = page.parent.messages.length;
    assert.equal(page.key('PageDown'), false); assert.equal(page.parent.messages.length, before);
    page.click(`close-${dialog}`); assert.equal(page.nodes.get(`${dialog}-dialog`).open, false);
  }
  for (const [key, delta] of [['PageDown',1], ['ArrowRight',1], ['PageUp',-1], ['ArrowLeft',-1]]) {
    assert.equal(page.key(key), true); assert.equal(page.parent.messages.at(-1).delta, delta);
    assert.equal(page.parent.messages.at(-1).type, 'rsa-presentation:turn');
  }
  const before = page.parent.messages.length;
  for (const modifier of ['ctrlKey','metaKey','altKey','shiftKey']) page.key('PageDown', {[modifier]:true});
  page.key('ArrowRight', {target:{closest(){return {};}}});
  page.key('Escape'); page.key('Enter');
  assert.equal(page.parent.messages.length, before);
  page.click('show-source');
  page.hidden({origin:'https://example.org'}); assert.equal(page.nodes.get('source-dialog').open, true);
  page.hidden({source:{}}); assert.equal(page.nodes.get('source-dialog').open, true);
  page.hidden({data:{type:'rsa-presentation:visibility', active:true}}); assert.equal(page.nodes.get('source-dialog').open, true);
  page.hidden(); assert.equal(page.nodes.get('source-dialog').open, false);
  const standalone = loadPage(name, false); standalone.key('PageDown');
  assert.equal(standalone.parent.messages.length, 0);
  const offline = loadPage(name, true, 'null'); offline.key('PageDown');
  assert.equal(offline.parent.messages.at(-1).delta, 1);
  checks.push(`${name.toUpperCase()}: dialogs, focus/modifier guards, embedded/offline navigation, hidden-page cleanup and standalone isolation`);
}
const a = loadPage('a');
assert.deepEqual(a.nodes.get('trace-rows').children.map(row => row.children[4].textContent), [3,3,1]);
a.traceButtons[1].handlers.click();
assert.deepEqual(a.nodes.get('trace-rows').children.map(row => row.children[4].textContent), [15,21,35]);
assert.ok(a.nodes.get('trace-rows').children.every(row => row.children[5].textContent === 'Needs fallback'));
assert.equal(a.traceButtons[1].attributes['aria-pressed'], 'true');
assert.match(a.nodes.get('trace-summary').textContent, /gcd\(15, 21\) = 3/);
a.traceButtons[0].handlers.click();
assert.equal(a.nodes.get('trace-rows').children[2].children[5].textContent, 'No shared factor');
assert.match(a.nodes.get('trace-tree').textContent, /Root P: \[45045\]/);
checks.push('A arithmetic trace: shared-prime example and full-overlap example remain distinct');

const aMarkup = read('presentation/embed/a-key-implementation.html');
const aLines = [...aMarkup.matchAll(/data-source="([^"]+)" data-line="(\d+)"><span class="num">\d+<\/span><span class="code-text">([\s\S]*?)<\/span>/g)];
assert.equal(aLines.length, 21);
for (const [, source, line, text] of aLines) {
  assert.equal(decode(text), read(source).split(/\r?\n/)[Number(line)-1], `${source}:${line}`);
}
const bMarkup = read('presentation/embed/b-key-implementation.html');
const bLines = [...bMarkup.matchAll(/<span class="num">(\d+)<\/span><span class="code-text">([\s\S]*?)<\/span>/g)];
assert.equal(bLines.length, 26);
for (const [, line, text] of bLines) {
  const expected = read('rsa_lab/crypto.py').split(/\r?\n/)[Number(line)-1];
  const decoded = decode(text);
  if ([15,19,24,28,48,52].includes(Number(line))) assert.equal(decoded.match(/^(\s*raise \w+)\(/)[1], expected.match(/^(\s*raise \w+)\(/)[1]);
  else assert.equal(decoded, expected, `rsa_lab/crypto.py:${line}`);
}
for (const name of ['a', 'b']) {
  const embedded = read(`presentation/embed/${name}-key-implementation.html`);
  const stripped = embedded.replace(/<body data-embedded="true"(?: data-implementation="b")?>/, '<body>')
    .replace(/<link rel="stylesheet" href="\.\.\/assets\/implementation-embed\.css\?v=[^"]+">\n<script src="\.\.\/assets\/implementation-embed\.js\?v=[^"]+" defer><\/script>\n/,'');
  assert.ok(stripped === read(`review_slides/${name}-key-implementation.html`), `${name.toUpperCase()} review-page content must be preserved`);
}
const b = loadPage('b');
const archivedCases = JSON.parse(b.nodes.get('validation-data').textContent);
assert.deepEqual(archivedCases.map(item => item.id), ['matched','wrong_oaep_label','corrupted_ciphertext']);
const verification = JSON.parse(read('artifacts/demo/verification.json'));
const controls = JSON.parse(read('artifacts/controls/validation.json'));
assert.equal(archivedCases[0].result, `${verification.verified_decryption_records} messages verified across ${verification.verified_decryption_moduli} distinct moduli`);
b.caseButtons.forEach((button, index) => {
  button.handlers.click();
  assert.equal(b.nodes.get('case-observed').textContent, archivedCases[index].observed);
  assert.equal(b.nodes.get('case-result').textContent, archivedCases[index].result);
  assert.equal(b.nodes.get('case-expected').textContent, archivedCases[index].expected);
  b.caseButtons.forEach((value, i) => assert.equal(value.attributes['aria-pressed'], String(i === index)));
});
controls.oaep_checks.forEach((item, index) => {
  assert.equal(archivedCases[index+1].id, item.case);
  assert.equal(archivedCases[index+1].observed, item.observed);
  assert.equal(archivedCases[index+1].expected, item.expected);
  assert.equal(archivedCases[index+1].passed, item.passed);
});
b.exampleButtons.forEach((button, index) => {
  button.handlers.click();
  assert.equal(b.coreLines.filter(line => line.classes.has('active')).length, 1);
  assert.equal(b.coreLines.find(line => line.classes.has('active')).dataset.step, String(index + 1));
});
for (const [id, source, first, last, indent] of [
  ['pipeline-code','rsa_lab/crypto.py',83,96,8],
  ['comparison-code','rsa_lab/evaluation.py',43,47,12],
]) {
  const actual = decode(bMarkup.match(new RegExp(`<pre id="${id}"><code>([\\s\\S]*?)</code></pre>`))[1]);
  const expected = read(source).split('\n').slice(first-1,last).map(line => line.slice(indent)).join('\n');
  assert.equal(actual, expected);
}
assert.match(bMarkup, /These selections display saved results; they do not execute Python\./);
checks.push('21 exact A source lines and 26 B logic lines; supplementary caller/evaluator excerpts, evidence selection, arithmetic highlights and review/embed parity');
console.log(JSON.stringify({passed:true, checks}, null, 2));

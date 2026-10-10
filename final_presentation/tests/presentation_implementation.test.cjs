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
  return {
    handlers: {}, attributes: {}, children: [], dataset: {}, textContent: '', open: false,
    addEventListener(type, callback) { this.handlers[type] = callback; },
    setAttribute(name, value) { this.attributes[name] = value; },
    append(child) { this.children.push(child); },
    replaceChildren() { this.children = []; },
    closest() { return null; },
    showModal() { this.open = true; }, close() { this.open = false; }
  };
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
  const document = {...node(), body:{dataset:{embedded:String(embedded)}},
    getElementById: id => { assert.ok(nodes.has(id), `Missing element ${id}`); return nodes.get(id); },
    createElement: node,
    querySelector: selector => selector === 'dialog[open]' ? dialogs.find(dialog => dialog.open) || null : null,
    querySelectorAll: selector => selector === '[data-trace]' ? traceButtons : selector === 'dialog[open]' ? dialogs.filter(dialog => dialog.open) : []
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
  return {nodes, dialogs, traceButtons, document, window, parent,
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
assert.equal(bLines.length, 15);
for (const [, line, text] of bLines) {
  const expected = read('rsa_lab/crypto.py').split(/\r?\n/)[Number(line)-1];
  const decoded = decode(text);
  if (decoded.includes('Error(...)')) assert.ok(expected.startsWith(decoded.replace('(...)','(')));
  else assert.equal(decoded, expected, `rsa_lab/crypto.py:${line}`);
}
for (const name of ['a', 'b']) {
  const embedded = read(`presentation/embed/${name}-key-implementation.html`);
  const stripped = embedded.replace('<body data-embedded="true">', '<body>')
    .replace('<link rel="stylesheet" href="../assets/implementation-embed.css?v=20261010-final3">\n<script src="../assets/implementation-embed.js?v=20261010-final3" defer></script>\n','');
  assert.ok(stripped === read(`review_slides/${name}-key-implementation.html`), `${name.toUpperCase()} review-page content must be preserved`);
}
checks.push('21 exact A source lines and 15 B lines (four explicitly abbreviated errors); original review pages preserved');
console.log(JSON.stringify({passed:true, checks}, null, 2));

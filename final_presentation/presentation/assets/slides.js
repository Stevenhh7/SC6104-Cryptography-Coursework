(function () {
  'use strict';
  const M = window.RSAMath;
  const motion = window.RSAMotion;
  const evidence = window.RSAValidation;
  const page = document.body.dataset.page;
  const embedded = document.body.dataset.embedded === 'true' && window.parent !== window;
  const finalEvidence = embedded && window.RSA_FINAL_DATA;
  const routes = [
    {id: 'attack', href: 'index.html', label: '01 · Shared prime'},
    {id: 'batch', href: 'batch-gcd.html', label: '02 · Batch GCD'},
    {id: 'edges', href: 'edge-cases.html', label: '03 · Correctness'}
  ];
  const currentPage = routes.findIndex(route => route.id === page);
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const number = value => value.toString();
  const attack = {n1: 77n, n2: 91n, e: 17n};
  attack.p = M.gcd(attack.n1, attack.n2);
  attack.q1 = attack.n1 / attack.p;
  attack.q2 = attack.n2 / attack.p;
  attack.lambda1 = M.lcm(attack.p - 1n, attack.q1 - 1n);
  attack.lambda2 = M.lcm(attack.p - 1n, attack.q2 - 1n);
  attack.d1 = M.inverse(attack.e, attack.lambda1);
  attack.d2 = M.inverse(attack.e, attack.lambda2);
  const batchValues = [15n, 21n, 143n];
  const batch = M.batch(batchValues);
  const records = [{id: 'A', n: 15n}, {id: 'B', n: 21n}, {id: 'C', n: 35n}, {id: 'A-copy', n: 15n}];
  const definitions = {
    attack: {
      eyebrow: 'A · Public-key-only factor detection',
      title: 'One shared prime. Two keys exposed.',
      subtitle: 'A greatest common divisor turns a public relationship into secret factors.',
      sceneLabel: 'From public moduli to private-key parameters',
      source: 'scanner.py · pairwise GCD',
      steps: [
        {title: 'Start with public inputs', copy: 'The two moduli and their exponents are public. The prime factors are initially unknown.',
          formula: 'N<sub>1</sub> = pq<sub>1</sub><br>N<sub>2</sub> = pq<sub>2</sub>',
          note: '先强调输入只有公钥 N 和 e，没有 p、q 或 d。77、91 和 e=17 是方便手算的教学例子；真实 2048-bit 样本使用 e=65537。',
          spoken: 'The scanner receives only public-key records. The secret prime factors are unknown.'},
        {title: 'Run Euclid’s algorithm', copy: 'Repeated division finds the greatest common divisor. Every value comes from the two public moduli.',
          formula: 'g = gcd(N<sub>1</sub>, N<sub>2</sub>)',
          note: '指着三个除法步骤：91 除以 77 余 14；77 除以 14 余 7；14 除以 7 余 0。最后一个非零余数就是 GCD。',
          spoken: 'Repeated division reveals the last nonzero remainder: seven.'},
        {title: 'Reveal the common prime', copy: 'The GCD is a nontrivial divisor of both moduli. Here it exposes the shared prime p = 7.',
          formula: 'gcd(77, 91) = <strong>7</strong>',
          note: '7 同时整除两个不同模数，且大于 1、小于两个模数，因此是真正的非平凡因子。密钥之间的共享关系使攻击成立。',
          spoken: 'The shared prime is exposed even though the two public moduli are different.'},
        {title: 'Recover the other factors', copy: 'Divide each public modulus by the recovered prime. Both moduli are now completely factored.',
          formula: 'q<sub>1</sub> = 77 / 7 = 11<br>q<sub>2</sub> = 91 / 7 = 13',
          note: 'GCD 给出一个因子，整数除法给出另一个因子。在实际扫描器中，输出前会检查因子非平凡、整除，以及因子与余因子的乘积。',
          spoken: 'Dividing by seven gives eleven and thirteen, completing both factorizations.'},
        {title: 'Connect factors to private keys', copy: 'The factors determine λ(N). Inverting the public exponent modulo λ(N) gives a private exponent.',
          formula: 'λ(N) = lcm(p − 1, q − 1)<br>d = e<sup>−1</sup> mod λ(N)',
          note: 'λ(77)=lcm(6,10)=30，17 的模 30 逆元是 23；λ(91)=12，逆元是 5。A 提供恢复的因子，B 从这个连接点重建密钥。',
          spoken: 'The recovered factors let us reconstruct a private exponent using a modular inverse.'},
        {title: 'Validate usable recovery', copy: 'The project’s integration test reconstructs a real 2048-bit private key and decrypts an OAEP test ciphertext.',
          formula: 'public inputs → factors → private key',
          note: '区分教学动画和真实验证：画面展示小整数算术；仓库测试使用 2048-bit 公钥，通过恢复因子重建私钥并完成 OAEP 解密。不能说任意 RSA-2048 都被破解。',
          spoken: 'Our 2048-bit integration check confirms that the recovered factors can be used to decrypt.'}
      ]
    },
    batch: {
      eyebrow: 'A · Product and squared-modulus remainder trees',
      title: 'Multiply up. Reduce down. Find factors.',
      subtitle: 'Reuse intermediate work instead of comparing every pair of public moduli.',
      sceneLabel: 'Batch GCD · exact teaching example',
      source: 'trees.py · product_tree() / squared_remainders()',
      steps: [
        {title: 'Begin with unique moduli', copy: 'For m distinct moduli, the baseline needs m(m − 1)/2 pairwise GCD computations.',
          formula: 'g<sub>i</sub> = gcd(N<sub>i</sub>, ∏<sub>j≠i</sub>N<sub>j</sub>)',
          note: '这三个模数用于清晰展示树的每一层。先说明目标是将每个模数与“其他模数的乘积”求 GCD。1000 个不同模数有 499,500 对。这个数是调用次数，不是速度提升倍数。',
          spoken: 'The baseline compares every pair. The batch method reuses products and remainders.'},
        {title: 'Combine neighboring leaves', copy: 'Multiply 15 and 21 to obtain 315. The unpaired 143 is carried upward once.',
          formula: '15 × 21 = 315<br>143 is carried unchanged',
          note: '指着动画向上的路径。相邻数两两相乘，奇数个输入的最后一个直接带到上一层，不重复乘一次。这里与 Python product_tree() 的行为一致。',
          spoken: 'Neighboring values are multiplied, while an unpaired last value is carried unchanged.'},
        {title: 'Reach the total product', copy: 'The root contains P, the product of every input modulus. Intermediate products remain available in the tree.',
          formula: 'P = 315 × 143 = 45,045',
          note: '总乘积在树根。不能直接 gcd(Nᵢ,P)，因为 P 含 Nᵢ，结果总是 Nᵢ。下一步需要平方模数取余。',
          spoken: 'At the root we obtain the total product, P.'},
        {title: 'Use squared moduli', copy: 'Reduce modulo each node product squared. The square preserves information needed after division by Nᵢ.',
          formula: 'r<sub>i</sub> = P mod N<sub>i</sub><sup>2</sup>',
          note: '为什么平方：P=NᵢQᵢ；rᵢ=Nᵢ(Qᵢ−kNᵢ)。除以 Nᵢ 后，得到与 Qᵢ 在模 Nᵢ 下同余的量。若仅对 Nᵢ 取模，余数必然是 0。',
          spoken: 'We reduce modulo the square. Reducing modulo the modulus itself would always give zero.'},
        {title: 'Propagate remainders downward', copy: 'The parent remainder can be reduced again at each child, because the child product squared divides the parent product squared.',
          formula: '(P mod V<sup>2</sup>) mod C<sup>2</sup><br>= P mod C<sup>2</sup>',
          note: '青色路径是余数向下传播。315²=99,225，大于 P，所以该节点余数还是 45,045；143²=20,449，余数是 4,147。',
          spoken: 'The remainder tree reuses each parent remainder when computing its children.'},
        {title: 'Read the leaf remainders', copy: 'Every leaf now has P modulo its modulus squared: 45, 63 and 4,147.',
          formula: 'r = [45, 63, 4,147]',
          note: '现在每个叶子有了自己的余数。143 在上一层已得到余数，直接传到叶子。三个余数均可被相应模数整除。',
          spoken: 'At the leaves, we have the three remainders needed for the final computation.'},
        {title: 'Divide exactly by each modulus', copy: 'The quotient rᵢ/Nᵢ is congruent to the product of the other moduli, modulo Nᵢ.',
          formula: 'r<sub>i</sub> / N<sub>i</sub><br>≡ ∏<sub>j≠i</sub>N<sub>j</sub> (mod N<sub>i</sub>)',
          note: '45/15=3；63/21=3；4147/143=29。代码会验证可以整除，以检查余数树的不变量。',
          spoken: 'Exact division produces a value with the same relevant modular information as the other-moduli product.'},
        {title: 'Calculate the final GCDs', copy: '15 and 21 share factor 3. No shared factor is found for 143 in this input collection.',
          formula: 'g<sub>i</sub> = gcd(N<sub>i</sub>, r<sub>i</sub>/N<sub>i</sub>)',
          note: '两个结果是 3，另一个是 1。精确表达：当前集合中未发现 143 的共享因子。树算法的性能仍需在相同数据和后端下实测，也需要计入特殊情况回退。',
          spoken: 'The final GCDs are three, three and one. Only two moduli expose a shared factor here.'}
      ]
    },
    edges: {
      eyebrow: 'A · Deduplication, fallback and validation',
      title: 'When GCD equals N, the job is not done.',
      subtitle: 'Keep duplicate records and full-overlap results distinct—and preserve unresolved cases.',
      sceneLabel: 'Two edge cases · one public-key collection',
      source: 'scanner.py · deduplication / full-overlap fallback',
      steps: [
        {title: 'Collect public records', copy: 'Four records contain three different moduli. A and A-copy use the same modulus.',
          formula: 'records = [15, 21, 35, 15]',
          note: '输入四条记录，其中两条 N 相同，但各条 ID 仍需保留。重复模数和共享非平凡因子是不同概念。',
          spoken: 'There are four records but only three distinct moduli.'},
        {title: 'Deduplicate; keep the mapping', copy: 'Scan each distinct modulus once. Preserve both original IDs so a recovered factor maps back to A and A-copy.',
          formula: '4 records → 3 unique moduli',
          note: '同一模数只进入树一次；记录映射没有丢失。实际接口还保留每条记录自己的 e，恢复 d 时不能借用别人的指数。',
          spoken: 'We deduplicate the arithmetic input while keeping the mapping to all original records.'},
        {title: 'Recognize full overlap', copy: 'Both factors of 15 occur elsewhere. Its batch GCD is 15, which does not yet split the modulus.',
          formula: 'gcd(15, 21 × 35) = 15',
          note: '三角结构中 3 被 15、21 共享，5 被 15、35 共享，7 被 21、35 共享。因此三个批量 GCD 都等于自己。不能将这样的结果解释为 clean。',
          spoken: 'A GCD equal to the modulus means we still need to separate its factors.'},
        {title: 'Split with pairwise fallback', copy: 'A targeted pairwise check separates a nontrivial factor. Disable fallback to compare the unresolved outcome.',
          formula: 'gcd(15, 21) = 3<br>15 = 3 × 5',
          note: '默认程序对全重叠候选项继续做两两检查。切换开关可以展示预算为 0 的情况：保留 unresolved_full_overlap，不能报告没有问题。极端情况下回退成本仍可能接近二次级。',
          spoken: 'Additional pairwise checks split full-overlap cases. If checks are disabled, the results remain unresolved.'},
        {title: 'Map verified results back', copy: 'Report each original record, including duplicates. A limited scan must still expose any unresolved moduli.',
          formula: 'distinct moduli → original records',
          note: 'A 与 A-copy 均得到相同因子。右侧为真实 Python 样本的验证结果，不是浏览器在此刻运行 2048-bit 扫描。最后强调检测仅覆盖当前集合；修复随机性并更换受影响密钥，OAEP 不能修复已泄露的私钥。',
          spoken: 'The factors map back to every original record. A clean scan only describes the inspected collection.'}
      ]
    }
  };
  const definition = definitions[page];
  let step = 0, timer = null, fallbackEnabled = true;
  let notesVisible = false;
  try { notesVisible = !embedded && sessionStorage.getItem('rsa-speaker-notes') === 'true'; } catch (_) {}
  const deck = document.getElementById('deck');
  deck.innerHTML = `
    <header class="topbar">
      <div class="brand"><span aria-hidden="true"></span>SC6104 / RSA key audit</div>
      <nav class="nav" aria-label="Presentation pages">${routes.map(route => `<a href="${route.href}" ${route.id === page ? 'aria-current="page"' : ''}>${route.label}</a>`).join('')}</nav>
      <div class="page-count">${String(currentPage + 1).padStart(2, '0')} / 03</div>
    </header>
    <div class="heading"><div class="eyebrow">${definition.eyebrow}</div><h1>${definition.title}</h1><p class="subtitle">${definition.subtitle}</p></div>
    <div class="layout">
      <section class="scene" aria-label="Animated algorithm illustration">
        <div class="scene-top"><span class="scene-label">${definition.sceneLabel}</span><span class="tag" id="scene-tag"></span></div>
        <div id="scene-content"></div>
      </section>
      <aside class="side">
        <div class="step-kicker"><span class="step-number" id="step-number">1</span><span id="step-label"></span></div>
        <div id="step-details" aria-live="polite" aria-atomic="true"><h2 id="step-title"></h2><p class="side-copy" id="step-copy"></p><div class="side-formula" id="step-formula"></div></div>
        <div class="side-proof" id="side-proof"></div>
        <code class="implementation">${definition.source}</code>
      </aside>
    </div>
    <div class="controls" aria-label="Animation controls">
      <button class="button ghost" id="restart" type="button">Restart</button>
      <button class="button" id="previous" type="button">Previous</button>
      <button class="button primary" id="next" type="button">Next step</button>
      <button class="button" id="play" type="button" aria-pressed="false">Play</button>
      <div class="progress-track" id="progress-track" role="progressbar" aria-label="Step progress" aria-valuemin="1" aria-valuemax="${definition.steps.length}"></div>
      <span class="progress-text" id="progress-text"></span>
      <div class="utility"><button class="button ghost" id="notes-button" type="button" aria-expanded="false" aria-controls="notes">讲解提示</button><button class="button ghost" id="fullscreen" type="button">Full screen</button></div>
    </div>
    <footer class="footer"><span>Small integers show the mechanism · Python validation uses 2048-bit RSA.<br>Algorithm reference: <a href="https://www.usenix.org/system/files/conference/usenixsecurity12/sec12-final228.pdf" target="_blank" rel="noopener">Heninger et al., USENIX Security 2012, §3.3</a></span><span class="keyboard"><kbd>←</kbd> / <kbd>→</kbd> steps · <kbd>Space</kbd> next · <kbd>P</kbd> play · <kbd>N</kbd> notes · <kbd>F</kbd> full screen<br><kbd>1</kbd> / <kbd>2</kbd> / <kbd>3</kbd> pages</span></footer>
    <section class="notes" id="notes" lang="zh-CN" hidden><h2>当前步骤的讲解提示</h2><p id="note-zh"></p><p class="english" id="note-en" lang="en"></p></section>`;
  const byId = id => document.getElementById(id);
  function particle(path, down = false, delay = 0) {
    if (reducedMotion.matches) return '';
    return `<circle data-transient data-flow-delay="${delay}" r="4" opacity="0" class="particle ${down ? 'down' : ''}"><animateMotion path="${path}" begin="indefinite" dur="1.05s" calcMode="spline" keyPoints="0;1" keyTimes="0;1" keySplines=".4 0 .2 1" fill="freeze"/><animate attributeName="opacity" begin="indefinite" dur="1.05s" values="0;1;1;0" keyTimes="0;.12;.85;1" fill="freeze"/></circle>`;
  }
  function attackScene() {
    const revealed = step >= 2, divided = step >= 3, recovered = step >= 4;
    const paths = step === 1 ? ['M200 0 L200 26', 'M600 0 L600 8 Q600 13 594 13 L208 13 Q200 13 200 21 L200 26']
      : step === 2 ? ['M200 26 L200 0', 'M200 26 L200 21 Q200 13 208 13 L594 13 Q600 13 600 8 L600 0'] : [];
    function key(n, q, index) {
      return `<div class="key ${revealed ? 'highlight' : ''}"><div class="key-label">Public key ${index}<span>known N</span></div><div class="key-number"><small>N<sub>${index}</sub> = </small>${n}</div><div class="factor-row"><span data-motion-delay="${200 + index * 80}" class="factor ${revealed ? 'common' : 'unknown'}">${revealed ? attack.p : '?'}</span><span>×</span><span data-motion-delay="${100 + index * 80}" class="factor ${divided ? '' : 'unknown'}">${divided ? q : '?'}</span></div><div class="key-exponent">Public exponent e = ${attack.e}</div></div>`;
    }
    function privateKey(lambda, d) {
      return `<div class="private-key" data-motion-delay="120">${recovered ? `<span>λ(N) = ${lambda}</span><strong>d = ${d}</strong><small>${attack.e}d ≡ 1 (mod ${lambda})</small>` : '<span class="muted-placeholder">Private exponent d = ? · waiting for factors</span>'}</div>`;
    }
    return `<div class="attack-scene"><div class="key-pair">${key(attack.n1, attack.q1, 1)}${key(attack.n2, attack.q2, 2)}</div>
      <svg class="attack-connector" viewBox="0 0 800 26" role="img" aria-label="Public moduli flow into GCD; the recovered factor flows back to both keys"><path d="M200 0 L200 26 M600 0 L600 8 Q600 13 594 13 L208 13 Q200 13 200 21 L200 26" stroke="${revealed ? '#d6899b' : '#b5c5e2'}" stroke-width="1.5" fill="none"/>${paths.map((path, i) => particle(path, false, i * 60)).join('')}</svg>
      <div class="attack-core" style="margin-top:0"><div class="gcd-hub"><div class="equation math">gcd(77, 91) = <b>${revealed ? attack.p : '?'}</b></div><span class="hub-caption">${revealed ? 'Nontrivial divisor of both moduli' : 'Computed from public inputs only'}</span></div>
        <div class="euclid">${step >= 1 ? M.euclid(attack.n2, attack.n1).map((row, i) => `<div class="euclid-row" data-motion-delay="${130 + i * 130}">${row.a} = ${row.quotient} × ${row.b} + ${row.remainder}</div>`).join('') : '<div class="muted-placeholder" style="font-size:14px;padding:10px">Euclid’s division steps<br>appear on the next step.</div>'}</div></div>
      <div class="private-row">${privateKey(attack.lambda1, attack.d1)}${privateKey(attack.lambda2, attack.d2)}</div>
      <div class="flow-caption">${step >= 5 ? '<strong>Validated handoff:</strong> recovered factors → reconstructed key → OAEP decryption' : 'The GCD exposes p; integer division recovers q.'}</div></div>`;
  }
  function treeNode(x, y, value, label, visible, remainder, state = '') {
    return `<g class="tree-node" opacity="${visible ? '1' : '.35'}"><rect class="cell ${visible ? state : ''}" x="${x - 76}" y="${y - 37}" width="152" height="74" rx="11" ${visible ? '' : 'stroke-dasharray="4 5"'}/><text class="node-label" x="${x}" y="${y - 17}" text-anchor="middle">${label}</text><text class="node-value" data-motion-delay="400" opacity="${visible ? '1' : '0'}" x="${x}" y="${y + 8}" text-anchor="middle">${value}</text><text class="node-rem" data-motion-delay="430" opacity="${remainder !== undefined ? '1' : '0'}" x="${x}" y="${y + 27}" text-anchor="middle">${remainder !== undefined ? `r = ${remainder}` : ''}</text></g>`;
  }
  function batchScene() {
    const lowerUp = ['M135 234 L135 223 Q135 217 144 217 L251 217 Q260 217 260 207 L260 202', 'M385 234 L385 223 Q385 217 376 217 L269 217 Q260 217 260 207 L260 202', 'M640 234 L640 202'];
    const upperUp = ['M260 128 L260 115 Q260 110 269 110 L381 110 Q390 110 390 103 L390 97', 'M640 128 L640 115 Q640 110 631 110 L399 110 Q390 110 390 103 L390 97'];
    const upperDown = ['M390 97 L390 104 Q390 110 381 110 L269 110 Q260 110 260 119 L260 128', 'M390 97 L390 104 Q390 110 399 110 L631 110 Q640 110 640 119 L640 128'];
    const lowerDown = ['M260 202 L260 208 Q260 217 251 217 L144 217 Q135 217 135 226 L135 234', 'M260 202 L260 208 Q260 217 269 217 L376 217 Q385 217 385 226 L385 234', 'M640 202 L640 234'];
    const flowPaths = step === 1 ? lowerUp : step === 2 ? upperUp : step === 4 ? upperDown : step === 5 ? lowerDown : [];
    const allEdges = [...lowerUp, ...upperUp];
    const activeColor = step >= 4 ? 'teal' : step >= 1 ? 'blue' : '';
    const squares = step === 3;
    const svg = `<svg class="tree-svg" viewBox="0 0 780 325" role="img" aria-label="Product tree with inputs 15, 21, 143; root 45045; downward remainders 45, 63, 4147"><title>Product and remainder tree</title><desc>Products move upward; remainders modulo squared products move downward.</desc>
      ${allEdges.map(path => `<path class="edge ${activeColor}" d="${path}"/>`).join('')}
      <text class="layer-label" x="13" y="63">ROOT</text><text class="layer-label" x="13" y="168">PAIR</text><text class="layer-label" x="13" y="273">Nᵢ</text>
      ${treeNode(390, 60, number(batch.product), 'P · total product', step >= 2, undefined, step >= 4 ? 'teal' : 'blue')}
      ${treeNode(260, 165, 315, squares ? 'mod 315² = 99,225' : '15 × 21', step >= 1, step >= 4 ? batch.remainderLevels[1][0] : undefined, step >= 4 ? 'teal' : 'blue')}
      ${treeNode(640, 165, 143, squares ? 'mod 143² = 20,449' : '143 · carried once', step >= 1, step >= 4 ? batch.remainderLevels[1][1] : undefined, step >= 4 ? 'teal' : 'blue')}
      ${[135, 385, 640].map((x, i) => treeNode(x, 271, number(batchValues[i]), squares ? `mod ${batchValues[i]}² = ${batchValues[i] ** 2n}` : `Input N${i + 1}`, true, step >= 5 ? batch.remainders[i] : undefined, step >= 5 ? (step >= 7 && i === 2 ? 'clean' : 'teal') : '')).join('')}
      ${flowPaths.map((path, i) => particle(path, step >= 4, i * 60)).join('')}</svg>`;
    const results = batchValues.map((n, i) => `<div data-motion-delay="${110 + i * 90}" class="tree-result ${step >= 7 && batch.gcds[i] > 1n ? 'found' : ''}">${step >= 6 ? `${batch.remainders[i]} / ${n} = ${batch.quotients[i]}` : 'Exact division pending'}${step >= 7 ? `<strong>gcd(${n}, ${batch.quotients[i]}) = ${batch.gcds[i]}</strong>` : '<strong class="muted-placeholder">gcd = ?</strong>'}</div>`).join('');
    const mobile = `<div class="tree-mobile"><div class="mobile-level">Root P<div class="mobile-values"><span class="mobile-value">${step >= 2 ? batch.product : '?'}</span></div></div><div class="mobile-level">Pair products<div class="mobile-values">${[315n, 143n].map((n, i) => `<span class="mobile-value">${step >= 1 ? n : '?'}${step >= 4 ? `<small>r = ${batch.remainderLevels[1][i]}</small>` : ''}</span>`).join('')}</div></div><div class="mobile-level">Input moduli<div class="mobile-values">${batchValues.map((n, i) => `<span class="mobile-value">${n}${step >= 5 ? `<small>r = ${batch.remainders[i]}</small>` : ''}${step >= 6 ? `<small>r / N = ${batch.quotients[i]}</small>` : ''}${step >= 7 ? `<small>gcd = ${batch.gcds[i]}</small>` : ''}</span>`).join('')}</div></div></div>`;
    return `<div class="tree-wrap">${svg}</div>${mobile}<div class="tree-result-row">${results}</div><div class="method-strip"><span>Pairwise baseline:</span><b>1,000 moduli = 499,500 GCD pairs</b><span>· comparison count, not a speed claim</span></div>`;
  }
  function caseScene() {
    const model = M.scan(records, fallbackEnabled);
    const deduped = step >= 1, overlap = step >= 2, split = step >= 3 && fallbackEnabled;
    const finished = step >= 4;
    const paths = ['M95 44 L245 44', 'M78 63 L157 139', 'M262 63 L183 139'];
    let math = 'gcd(15, 15) = 15<br>No nontrivial factor yet';
    let description = 'The same modulus occurs twice. Keep its original record IDs.';
    if (step === 1) { math = 'A, A-copy ↦ N = 15'; description = 'The arithmetic input is unique; the reporting input keeps every record.'; }
    if (step === 2) { math = 'gcd(15, 21 × 35)<br>= <strong>15</strong>'; description = 'Both primes appear elsewhere. The batch result covers the entire modulus.'; }
    if (step >= 3) {
      math = fallbackEnabled ? 'gcd(15, 21) = <strong>3</strong><br>15 = 3 × 5' : 'g = N<br><strong>Keep unresolved</strong>';
      description = fallbackEnabled ? (finished ? 'Repeat for the remaining candidates, then map factors back to every record.' : 'A nontrivial pairwise GCD separates the factors of 15.') : 'Fallback budget = 0. No factor is claimed; the CLI reports exit code 4.';
    }
    const status = `<span aria-hidden="${!overlap}" class="status-pill ${split ? 'found' : 'unresolved'} ${overlap ? '' : 'is-pending'}">${split ? 'factor_found' : 'unresolved_full_overlap'}</span>`;
    const triangle = `<svg class="triangle-svg" viewBox="0 0 340 190" role="img" aria-label="15 and 21 share 3; 15 and 35 share 5; 21 and 35 share 7"><title>Full-overlap triangle</title>
      ${paths.map((path, i) => `<path class="triangle-edge ${overlap ? ['prime3','prime5','prime7'][i] : ''}" d="${path}"/>`).join('')}
      <text class="prime-label" opacity="${overlap ? 1 : 0}" data-motion-delay="120" x="170" y="32" text-anchor="middle">shared 3</text><text class="prime-label" opacity="${overlap ? 1 : 0}" data-motion-delay="220" x="83" y="112" text-anchor="middle">5</text><text class="prime-label" opacity="${overlap ? 1 : 0}" data-motion-delay="320" x="259" y="112" text-anchor="middle">7</text>
      ${[[65,44,15],[275,44,21],[170,156,35]].map(([x,y,n]) => `<rect x="${x-37}" y="${y-23}" width="74" height="46" rx="10" fill="${overlap ? '#fff4df' : '#f2f6fd'}" stroke="${overlap ? '#dfbc85' : '#cbd7e9'}"/><text class="case-value" x="${x}" y="${y+8}" text-anchor="middle">${n}</text>`).join('')}
      ${step === 3 && fallbackEnabled ? particle(paths[0]) : ''}</svg>`;
    const resultRows = model.unique.map((n, i) => {
      const hasFactor = split && (finished || i === 0);
      const factor = model.factors.get(i);
      const rowStatus = hasFactor ? 'found' : overlap ? 'unresolved' : '';
      return `<div data-motion-delay="${100 + i * 100}" class="case-result ${rowStatus}"><strong>${hasFactor ? `${n} = ${factor} × ${n / factor}` : `N = ${n}`}</strong><span>${hasFactor ? 'factor_found' : overlap ? 'unresolved' : 'awaiting scan'}</span><span aria-hidden="${!(finished && i === 0)}" class="record-mapping ${finished && i === 0 ? '' : 'is-pending'}">A + A-copy</span></div>`;
    }).join('');
    return `<div class="case-scene"><div class="records">${records.map((record, i) => `<div class="record ${i === 3 ? 'duplicate' : ''} ${i === 3 && deduped ? 'merged' : ''}"><span class="record-id">${record.id}</span><span class="record-n">${i === 3 && deduped ? 'Mapped to A' : `N = ${record.n}`}</span></div>`).join('')}</div><div class="case-work">${triangle}<div class="case-equation"><div class="big-math math">${math}</div><div class="description">${description}</div>${status}</div></div><div class="result-list">${resultRows}</div><label class="fallback-control"><input id="fallback" type="checkbox" ${fallbackEnabled ? 'checked' : ''}>Enable pairwise fallback <span class="tag ${fallbackEnabled ? 'teal' : 'amber'}">${fallbackEnabled ? 'default: unlimited' : 'budget: 0'}</span></label></div>`;
  }
  function renderProof() {
    if (finalEvidence && page === 'attack') return `<strong>Verified 2048-bit experiment</strong>${finalEvidence.input.unique_moduli} distinct moduli · ${finalEvidence.demo.correctly_factored_moduli} keys recovered.<br>${finalEvidence.demo.verified_decryption_records} OAEP messages verified.<br>Diagram: exact small-integer arithmetic.`;
    if (finalEvidence && page === 'edges' && step >= 4) return `<div class="verification"><h3>Verified experiment</h3><dl><dt>Recovered distinct keys</dt><dd>${finalEvidence.demo.correctly_factored_moduli} / ${finalEvidence.input.unique_moduli}</dd><dt>Full overlaps resolved</dt><dd>${finalEvidence.fallback_candidates}</dd><dt>Control scans passed</dt><dd>${finalEvidence.controls.summary.scan_runs}</dd><dt>OAEP negative checks</dt><dd>${finalEvidence.controls.summary.oaep_negative_checks}</dd></dl></div><div style="margin-top:14px"><strong>Scope of a clean result</strong>Only this collection is covered.</div>`;
    if (page === 'attack') return `<strong>2048-bit Python fixture</strong>${evidence.unique_modulus_count} unique moduli · ${evidence.factored_unique_moduli} factored.<br>OAEP recovery verified.<br>On-screen: tiny moduli, e = 17.`;
    if (page === 'batch') return '<strong>Invariant: remainder = P mod V²</strong>Carry odd leaves once.<br>Require exact division before GCD.';
    if (step < 4) return '<strong>Three explicit result states</strong><code>factor_found</code><br><code>no_shared_factor</code><br><code>unresolved_full_overlap</code>';
    return `<div class="verification"><h3>Python verification · ${evidence.verified_date}</h3><dl><dt>Tests passed</dt><dd>${evidence.test_methods}</dd><dt>RSA modulus length</dt><dd>2048 bit</dd><dt>Factored unique moduli</dt><dd>${evidence.factored_unique_moduli} / ${evidence.unique_modulus_count}</dd><dt>Full overlaps resolved</dt><dd>${evidence.batch_full_overlap_count}</dd></dl></div><div style="margin-top:14px"><strong>Scope of a clean result</strong>Only this collection is covered.<br>Fix randomness; rotate affected keys.</div>`;
  }
  function renderNotes() {
    if (embedded) { byId('notes').hidden = true; return; }
    const state = definition.steps[step];
    byId('notes').hidden = !notesVisible;
    byId('notes-button').setAttribute('aria-expanded', String(notesVisible));
    byId('notes-button').classList.toggle('active', notesVisible);
    byId('note-zh').textContent = state.note;
    byId('note-en').textContent = state.spoken;
  }
  function update(animateChange = true) {
    const snapshot = animateChange ? motion.capture() : null;
    const state = definition.steps[step];
    byId('step-number').textContent = step + 1;
    byId('step-label').textContent = `STEP ${step + 1} OF ${definition.steps.length}`;
    byId('step-title').textContent = page === 'edges' && step === 3 && !fallbackEnabled ? 'Preserve the unresolved state' : state.title;
    byId('step-copy').textContent = page === 'edges' && step >= 3 && !fallbackEnabled ? 'Checks are disabled. Preserve full-overlap results explicitly, without claiming a recovered factor.' : state.copy;
    motion.patch(byId('step-formula'), page === 'edges' && step === 3 && !fallbackEnabled ? 'g<sub>i</sub> = N<sub>i</sub><br>status = unresolved' : state.formula);
    byId('step-formula').hidden = page === 'edges' && step === 4;
    motion.patch(byId('side-proof'), renderProof());
    byId('scene-tag').textContent = page === 'attack' ? 'e = 17 · teaching arithmetic' : page === 'batch' ? `${step < 4 ? 'PRODUCTS ↑' : 'REMAINDERS ↓'}` : `${step ? '3 unique moduli' : '4 public records'}`;
    byId('scene-tag').className = `tag ${page === 'batch' && step >= 4 ? 'teal' : 'blue'}`;
    motion.patch(byId('scene-content'), page === 'attack' ? attackScene() : page === 'batch' ? batchScene() : caseScene());
    byId('scene-content').querySelectorAll('[data-transient] animateMotion, [data-transient] animate').forEach(animation => {
      animation.beginElementAt(Number(animation.parentElement.dataset.flowDelay || 0) / 1000);
    });
    motion.patch(byId('progress-track'), definition.steps.map((_, i) => `<span class="progress-segment ${i <= step ? 'complete' : ''}"></span>`).join(''));
    byId('progress-track').setAttribute('aria-valuenow', String(step + 1));
    byId('progress-track').setAttribute('aria-valuetext', `${step + 1} of ${definition.steps.length}: ${state.title}`);
    byId('progress-text').textContent = `${step + 1} / ${definition.steps.length}`;
    byId('previous').disabled = step === 0;
    byId('next').disabled = step === definition.steps.length - 1;
    renderNotes();
    motion.play(snapshot);
  }
  function pause() {
    if (timer !== null) clearInterval(timer);
    timer = null;
    byId('play').textContent = 'Play';
    byId('play').setAttribute('aria-pressed', 'false');
    byId('play').classList.remove('active');
  }
  function move(delta) {
    const next = Math.max(0, Math.min(definition.steps.length - 1, step + delta));
    if (step !== next) { step = next; update(); }
    if (step === definition.steps.length - 1) pause();
  }
  function togglePlay() {
    if (timer !== null) { pause(); return; }
    if (step === definition.steps.length - 1) { step = 0; update(); }
    byId('play').textContent = 'Pause';
    byId('play').setAttribute('aria-pressed', 'true');
    byId('play').classList.add('active');
    timer = setInterval(() => move(1), 3200);
  }
  function toggleNotes() {
    if (embedded) return;
    notesVisible = !notesVisible;
    try { sessionStorage.setItem('rsa-speaker-notes', String(notesVisible)); } catch (_) {}
    renderNotes();
  }
  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
    } catch (_) { byId('fullscreen').textContent = 'Use browser full screen'; }
  }
  byId('restart').addEventListener('click', () => { pause(); step = 0; update(); });
  byId('previous').addEventListener('click', () => { pause(); move(-1); });
  byId('next').addEventListener('click', () => { pause(); move(1); });
  byId('play').addEventListener('click', togglePlay);
  byId('notes-button').addEventListener('click', toggleNotes);
  byId('fullscreen').addEventListener('click', toggleFullscreen);
  byId('scene-content').addEventListener('change', event => {
    if (event.target.id === 'fallback') { fallbackEnabled = event.target.checked; update(); }
  });
  document.addEventListener('fullscreenchange', () => { byId('fullscreen').textContent = document.fullscreenElement ? 'Exit full screen' : 'Full screen'; });
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  if (embedded) {
    window.addEventListener('message', event => {
      if (event.source !== window.parent || event.origin !== window.location.origin) return;
      if (event.data?.type === 'rsa-presentation:visibility' && event.data.active === false) pause();
    });
  }
  function navigatePage(index) {
    pause();
    if (embedded) window.parent.postMessage({type: 'rsa-presentation:select', page: index + 1}, '*');
    else window.location.href = routes[index].href;
  }
  function turnPage(delta) {
    pause();
    if (embedded) window.parent.postMessage({type: 'rsa-presentation:turn', delta}, '*');
    else if (currentPage + delta >= 0 && currentPage + delta < routes.length) navigatePage(currentPage + delta);
  }
  document.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.target.closest('input,select,textarea')) return;
    if (event.target.closest('button,a') && (event.key === ' ' || event.key === 'Enter')) return;
    if (event.key === 'ArrowRight' || event.key === ' ') { event.preventDefault(); pause(); move(1); }
    else if (event.key === 'ArrowLeft') { event.preventDefault(); pause(); move(-1); }
    else if (event.key === 'Home') { event.preventDefault(); pause(); step = 0; update(); }
    else if (event.key.toLowerCase() === 'p') togglePlay();
    else if (event.key.toLowerCase() === 'n') toggleNotes();
    else if (event.key.toLowerCase() === 'f') toggleFullscreen();
    else if (/^[123]$/.test(event.key)) { event.preventDefault(); navigatePage(Number(event.key) - 1); }
    else if (event.key === 'PageDown') { event.preventDefault(); turnPage(1); }
    else if (event.key === 'PageUp') { event.preventDefault(); turnPage(-1); }
  });
  update(false);
})();

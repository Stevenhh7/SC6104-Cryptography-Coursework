/* Small-number teaching model of the repository algorithms; no private inputs.
 * BigInt keeps every arithmetic operation exact. No network/runtime dependency.
 */
(function (root) {
  'use strict';
  function gcd(a, b) {
    while (b !== 0n) [a, b] = [b, a % b];
    return a < 0n ? -a : a;
  }
  function inverse(a, modulus) {
    let [oldR, r, oldS, s] = [a, modulus, 1n, 0n];
    while (r !== 0n) {
      const q = oldR / r;
      [oldR, r] = [r, oldR - q * r];
      [oldS, s] = [s, oldS - q * s];
    }
    if (oldR !== 1n) throw new Error('The exponent has no inverse.');
    return ((oldS % modulus) + modulus) % modulus;
  }
  function lcm(a, b) { return a / gcd(a, b) * b; }
  function euclid(a, b) {
    const rows = [];
    while (b !== 0n) {
      rows.push({a, b, quotient: a / b, remainder: a % b});
      [a, b] = [b, a % b];
    }
    return rows;
  }
  function tree(values) {
    if (!values.length) return [];
    const levels = [values.slice()];
    while (levels.at(-1).length > 1) {
      const last = levels.at(-1), next = [];
      for (let i = 0; i < last.length; i += 2)
        next.push(i + 1 < last.length ? last[i] * last[i + 1] : last[i]);
      levels.push(next);
    }
    return levels;
  }
  function batch(values) {
    const levels = tree(values);
    if (!levels.length) return {levels, remainderLevels: [], remainders: [], quotients: [], gcds: [], product: 1n};
    let remainders = [levels.at(-1)[0]];
    const remainderLevels = [remainders.slice()];
    for (let level = levels.length - 2; level >= 0; level--) {
      remainders = levels[level].map((value, i) => remainders[Math.floor(i / 2)] % (value * value));
      remainderLevels.unshift(remainders.slice());
    }
    const quotients = remainders.map((r, i) => {
      if (r % values[i] !== 0n) throw new Error('Remainder must be divisible by its modulus.');
      return r / values[i];
    });
    return {levels, remainderLevels, remainders, quotients,
      gcds: values.map((n, i) => gcd(n, quotients[i])), product: levels.at(-1)[0]};
  }
  function scan(records, fallbackEnabled = true) {
    const unique = [], indices = new Map();
    records.forEach(record => {
      const key = record.n.toString();
      if (!indices.has(key)) { indices.set(key, unique.length); unique.push(record.n); }
    });
    const model = batch(unique), factors = new Map(), fullOverlap = [], checks = [];
    model.gcds.forEach((g, i) => {
      if (g === unique[i]) fullOverlap.push(i);
      else if (g > 1n) factors.set(i, g < unique[i] / g ? g : unique[i] / g);
    });
    if (fallbackEnabled) fullOverlap.forEach(i => {
      for (let j = 0; j < unique.length; j++) {
        if (j === i) continue;
        const g = gcd(unique[i], unique[j]);
        checks.push({i, j, g});
        if (g > 1n && g < unique[i]) {
          factors.set(i, g < unique[i] / g ? g : unique[i] / g); break;
        }
      }
    });
    const results = records.map(record => {
      const i = indices.get(record.n.toString()), factor = factors.get(i);
      return {...record, index: i, factor, cofactor: factor ? record.n / factor : undefined,
        status: factor ? 'factor_found' : fullOverlap.includes(i) ? 'unresolved_full_overlap' : 'no_shared_factor'};
    });
    return {unique, model, factors, fullOverlap, checks, results};
  }
  root.RSAMath = {gcd, inverse, lcm, euclid, tree, batch, scan};
  if (typeof module !== 'undefined' && module.exports) module.exports = root.RSAMath;
})(typeof window !== 'undefined' ? window : globalThis);

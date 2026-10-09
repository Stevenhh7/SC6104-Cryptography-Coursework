'use strict';
const assert = require('node:assert/strict');
const M = require('../presentation/assets/math.js');

assert.equal(M.gcd(77n, 91n), 7n);
assert.deepEqual(M.euclid(91n, 77n).map(row => row.remainder), [14n, 7n, 0n]);
assert.equal(M.inverse(17n, M.lcm(6n, 10n)), 23n);
assert.equal(M.inverse(17n, M.lcm(6n, 12n)), 5n);
const tree = M.tree([15n, 21n, 143n]);
assert.deepEqual(tree, [[15n, 21n, 143n], [315n, 143n], [45045n]]);
const batch = M.batch([15n, 21n, 143n]);
assert.deepEqual(batch.remainders, [45n, 63n, 4147n]);
assert.deepEqual(batch.quotients, [3n, 3n, 29n]);
assert.deepEqual(batch.gcds, [3n, 3n, 1n]);
const triangle = [15n, 21n, 35n, 15n].map((n,i) => ({id: String(i), n}));
const split = M.scan(triangle);
assert.deepEqual(split.model.gcds, [15n, 21n, 35n]);
assert.deepEqual(split.results.map(row => row.status), Array(4).fill('factor_found'));
assert.equal(split.unique.length, 3);
assert.equal(split.results[0].factor, split.results[3].factor);
assert.deepEqual(M.scan(triangle, false).results.map(row => row.status), Array(4).fill('unresolved_full_overlap'));

// Direct total-product modular reduction independently checks each tree leaf.
const primes = [3n,5n,7n,11n,13n,17n,19n,23n,29n,31n];
for (let size = 1; size <= 21; size++) {
  const values = Array.from({length: size}, (_,i) => primes[i % 10] * primes[(i + 3) % 10]);
  const model = M.batch(values), total = values.reduce((a,b) => a*b, 1n);
  assert.deepEqual(model.remainders, values.map(n => total % (n*n)));
  assert.deepEqual(model.gcds, values.map(n => M.gcd(n, (total % (n*n)) / n)));
}
console.log('Presentation arithmetic verified: RSA inverse, odd trees, exact remainders, full overlap, deduplication, fallback, 21 direct-reference datasets.');

import random
import unittest
from math import gcd, prod
from rsa_lab.detection import product_tree, scan, square_remainders
from rsa_lab.models import PublicKey


def public(numbers):
    return [PublicKey(f"k-{i}", n, 3) for i, n in enumerate(numbers)]


def factors(report):
    return {int(r["n"], 16): int(r["factor"], 16) for r in report["unique_results"] if r["status"] == "factor_found"}


class DetectionTests(unittest.TestCase):
    def compare(self, numbers, expected):
        for algorithm in ("pairwise", "batch"):
            result = scan(public(numbers), algorithm)
            self.assertEqual(set(factors(result)), set(expected))
            for n, factor in factors(result).items():
                self.assertTrue(1 < factor < n and n % factor == 0)
        return scan(public(numbers))

    def test_empty(self):
        self.compare([], [])

    def test_singleton(self):
        self.compare([15], [])

    def test_normal(self):
        self.compare([15, 77, 221], [])

    def test_shared_pair(self):
        self.compare([15, 21], [15, 21])

    def test_shared_group(self):
        self.compare([15, 21, 33, 143], [15, 21, 33, 143])

    def test_duplicates_only(self):
        result = self.compare([15, 15, 77], [])
        self.assertEqual(result["summary"]["duplicate_records"], 1)
        self.assertEqual(result["summary"]["fallback_candidates"], 0)

    def test_duplicates_and_shared_factors(self):
        result = self.compare([15, 21, 15], [15, 21])
        self.assertEqual(sum(r["status"] == "factor_found" for r in result["records"]), 3)

    def test_triangle_fallback(self):
        result = self.compare([15, 21, 35], [15, 21, 35])
        self.assertEqual(result["summary"]["fallback_candidates"], 3)
        self.assertGreater(result["summary"]["fallback_gcd_calls"], 0)
        self.assertEqual(result["native_summary"]["batch_full_overlap_count"], 3)

    def test_odd_and_non_power_of_two(self):
        numbers = [15, 21, 35, 143, 323, 667, 1147]
        self.compare(numbers, [15, 21, 35])

    def test_remainder_tree_against_direct_product(self):
        for length in range(0, 18):
            numbers = [101 + 2 * i for i in range(length)]
            tree = product_tree(numbers)
            self.assertEqual(square_remainders(tree), [prod(numbers) % (n * n) for n in numbers])

    def test_pairwise_call_count_after_deduplication(self):
        result = scan(public([15, 21, 35, 15, 143]), "pairwise")
        self.assertEqual(result["summary"]["pairwise_gcd_calls"], 6)

    def test_random_topologies_against_independent_oracle(self):
        rng = random.Random(104)
        primes = [101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151]
        for _ in range(120):
            numbers = [prod(rng.sample(primes, 2)) for _ in range(rng.randrange(1, 20))]
            unique = set(numbers)
            expected = {n for n in unique if any(1 < gcd(n, other) < n for other in unique if n != other)}
            self.compare(numbers, expected)

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            scan([PublicKey("same", 15, 3), PublicKey("same", 21, 3)])

    def test_unresolved_is_preserved_for_unsupported_composites(self):
        result = scan(public([15, 45]))
        row = next(r for r in result["unique_results"] if int(r["n"], 16) == 15)
        self.assertEqual(row["status"], "unresolved")

    def test_gmpy2_backend_matches_python(self):
        try:
            import gmpy2
        except ImportError:
            self.skipTest("可选 gmpy2 未安装")
        numbers = [15, 21, 35, 15, 143, 323, 667]
        for algorithm in ("pairwise", "batch"):
            python = scan(public(numbers), algorithm, "python")
            gmp = scan(public(numbers), algorithm, "gmpy2")
            self.assertEqual(python["records"], gmp["records"])
            self.assertEqual(python["summary"], gmp["summary"])

import importlib.util
import math
import random
import unittest
from unittest.mock import patch

from rsa_audit import PublicKey, ScanTimeout, scan_keys
from rsa_audit.trees import product_tree, squared_remainders


def keys_for(moduli):
    return [PublicKey(f"key-{index}", n) for index, n in enumerate(moduli)]


class TreeTests(unittest.TestCase):
    def test_empty_and_single(self):
        self.assertEqual(product_tree([]), [])
        self.assertEqual(squared_remainders([]), [])
        self.assertEqual(product_tree([15]), [[15]])
        self.assertEqual(squared_remainders([[15]]), [15])

    def test_odd_leaf_is_carried(self):
        self.assertEqual(product_tree([3, 5, 7]), [[3, 5, 7], [15, 7], [105]])

    def test_remainders_match_independent_direct_division(self):
        rng = random.Random(6104)
        for length in (1, 2, 3, 5, 7, 8, 9, 17, 32):
            values = [rng.randrange(3, 1000, 2) for _ in range(length)]
            with self.subTest(length=length):
                tree = product_tree(values)
                total = math.prod(values)
                self.assertEqual(tree[-1], [total])
                self.assertEqual(squared_remainders(tree), [total % (n * n) for n in values])


class ScannerTests(unittest.TestCase):
    def assert_matches_oracle(self, moduli, method="batch", backend="python"):
        # The oracle uses direct pairwise comparisons on distinct moduli only.
        report = scan_keys(keys_for(moduli), method=method, backend=backend)
        unique = set(moduli)
        expected_factored = set()
        for row in report.results:
            divisors = [math.gcd(row.n, other) for other in unique if other != row.n]
            recoverable = any(1 < divisor < row.n for divisor in divisors)
            if recoverable:
                expected_factored.add(row.n)
                self.assertEqual(row.status, "factor_found")
                self.assertGreater(row.factor, 1)
                self.assertLess(row.factor, row.n)
                self.assertEqual(row.factor * row.cofactor, row.n)
            else:
                self.assertEqual(row.status, "no_shared_factor")
                self.assertIsNone(row.factor)
                self.assertIsNone(row.cofactor)
            self.assertEqual(row.duplicate_count, moduli.count(row.n) - 1)
        self.assertEqual(report.summary["factored_unique_moduli"], len(expected_factored))
        self.assertEqual(report.summary["unique_modulus_count"], len(unique))
        self.assertEqual(report.summary["duplicate_record_count"], len(moduli) - len(unique))
        self.assertEqual(report.summary["unresolved_unique_moduli"], 0)
        self.assertGreaterEqual(report.timings["total_seconds"], 0)
        return report

    def test_empty_single_clean_shared_duplicates_and_odd_sizes(self):
        scenarios = (
            [], [15], [15, 15], [15, 77, 221], [15, 21], [15, 21, 33, 39],
            [15, 21, 35], [15, 21, 35, 15, 143], [77, 143, 221, 323, 437],
        )
        for method in ("pairwise", "batch"):
            for moduli in scenarios:
                with self.subTest(method=method, moduli=moduli):
                    self.assert_matches_oracle(moduli, method)

    def test_full_overlap_triangle_is_resolved(self):
        report = self.assert_matches_oracle([15, 21, 35])
        self.assertEqual(report.summary["batch_full_overlap_count"], 3)
        self.assertEqual(report.summary["factored_unique_moduli"], 3)
        self.assertEqual(report.operations["fallback_gcd_checks"], 3)

    def test_fallback_disabled_does_not_report_clean(self):
        report = scan_keys(keys_for([15, 21, 35, 143]), max_fallback_checks=0)
        self.assertEqual([row.status for row in report.results],
                         ["unresolved_full_overlap"] * 3 + ["no_shared_factor"])
        self.assertEqual(report.operations["fallback_gcd_checks"], 0)
        self.assertTrue(report.summary["fallback_limit_reached"])

    def test_fallback_budget_is_global(self):
        report = scan_keys(keys_for([15, 21, 35]), max_fallback_checks=1)
        self.assertEqual(report.summary["factored_unique_moduli"], 1)
        self.assertEqual(report.summary["unresolved_unique_moduli"], 2)
        self.assertEqual(report.operations["fallback_gcd_checks"], 1)

    def test_duplicate_records_preserve_id_order_and_exponents(self):
        keys = [PublicKey("one", 15, 3), PublicKey("two", 21), PublicKey("copy", 15, 17)]
        report = scan_keys(iter(keys))
        self.assertEqual([row.id for row in report.results], ["one", "two", "copy"])
        self.assertEqual([row.e for row in report.results], [3, 65537, 17])
        self.assertEqual(report.duplicate_groups[0].record_ids, ("one", "copy"))
        self.assertEqual(report.summary["factored_records"], 3)
        self.assertEqual(report.summary["factored_unique_moduli"], 2)
        self.assertEqual(report.operations["batch_gcd_checks"], 2)

    def test_pairwise_count_uses_unique_moduli(self):
        report = scan_keys(keys_for([15, 21, 35, 15, 143]), method="pairwise")
        self.assertEqual(report.operations["pairwise_gcd_checks"], 6)
        self.assertEqual(report.operations["batch_gcd_checks"], 0)

    def test_duplicates_do_not_create_false_factors(self):
        report = self.assert_matches_oracle([143] * 100)
        self.assertEqual(report.summary["duplicate_record_count"], 99)
        self.assertEqual(len(report.duplicate_groups), 1)

    def test_randomized_semiprime_sets_match_independent_oracle(self):
        primes = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
        rng = random.Random(20261009)
        for case in range(60):
            moduli = [math.prod(rng.sample(primes, 2)) for _ in range(rng.randrange(0, 40))]
            rng.shuffle(moduli)
            for method in ("batch", "pairwise"):
                with self.subTest(case=case, method=method):
                    self.assert_matches_oracle(moduli, method)

    def test_non_semiprime_divisibility_is_not_marked_clean(self):
        for method in ("batch", "pairwise"):
            report = scan_keys(keys_for([9, 27]), method=method)
            self.assertEqual(report.results[0].status, "unresolved_full_overlap")
            self.assertEqual(report.results[1].status, "factor_found")

    def test_bad_inputs(self):
        bad = [PublicKey("", 15), PublicKey("  ", 15), PublicKey("x", 1),
               PublicKey("x", -15), PublicKey("x", 14), PublicKey("x", True),
               PublicKey("x", "15"), PublicKey("x", 15, 2),
               PublicKey("x", 15, 1), PublicKey("x", 15, True), {}]
        for record in bad:
            with self.subTest(record=record), self.assertRaises(ValueError):
                scan_keys([record])
        with self.assertRaisesRegex(ValueError, "duplicate record id"):
            scan_keys([PublicKey("x", 15), PublicKey("x", 21)])

    def test_invalid_options(self):
        for options in ({"method": "other"}, {"backend": "other"},
                        {"max_fallback_checks": -1}, {"max_fallback_checks": True},
                        {"timeout_seconds": 0}, {"timeout_seconds": -1},
                        {"timeout_seconds": float("nan")},
                        {"timeout_seconds": float("inf")}, {"timeout_seconds": True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                scan_keys([], **options)

    def test_deadline_raises_instead_of_returning_partial_success(self):
        with patch("rsa_audit.scanner.perf_counter", side_effect=[0, 0, 2]):
            with self.assertRaises(ScanTimeout) as caught:
                scan_keys(keys_for([15, 21]), timeout_seconds=1)
        self.assertEqual(caught.exception.stage, "preprocess")

    def test_json_integers_have_explicit_hex_prefix(self):
        data = scan_keys(keys_for([15, 21])).to_dict()
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["results"][0]["n"], "0xf")
        self.assertEqual(data["results"][0]["factor"], "0x3")
        self.assertEqual(data["results"][0]["cofactor"], "0x5")

    @unittest.skipUnless(importlib.util.find_spec("gmpy2"), "optional gmpy2 is not installed")
    def test_optional_backend_matches_python(self):
        for method in ("batch", "pairwise"):
            self.assert_matches_oracle([15, 21, 35, 15, 143], method, "gmpy2")


if __name__ == "__main__":
    unittest.main()

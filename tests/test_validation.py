import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from rsa_lab.datasets import generate_dataset, repair_public
from rsa_lab.detection import scan
from rsa_lab.models import read_public
from rsa_lab.validation import run_validation_suite


class ControlExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        demo = cls.root / "demo"
        generate_dataset(demo, count=7, bits=1024, mode="demo")
        keys = read_public(demo / "public_keys.jsonl")
        results = cls.root / "demo-results"
        repair_public(keys, scan(keys), results / "repaired")
        cls.output = cls.root / "controls-results"
        with contextlib.redirect_stdout(io.StringIO()):
            cls.report = run_validation_suite(cls.root / "controls", demo, results, cls.output, normal_count=6)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_both_algorithms_match_positive_negative_and_coverage_controls(self):
        self.assertTrue(self.report["summary"]["passed"])
        self.assertEqual(self.report["summary"]["scan_runs"], 10)
        for row in self.report["cases"]:
            self.assertEqual(row["false_positives"], 0)
            self.assertEqual(row["false_negatives"], 0)
            expected = 5 if row["case"] == "shared_prime_demo" else 0
            self.assertEqual(row["correctly_factored"], expected)
        duplicates = next(row for row in self.report["cases"] if row["case"] == "duplicates_only")
        self.assertEqual((duplicates["records"], duplicates["unique_moduli"]), (8, 6))

    def test_attack_inputs_exclude_ground_truth_and_private_parameters(self):
        for case in (self.output / "attack_inputs").iterdir():
            self.assertFalse((case / "ground_truth.json").exists())
            self.assertFalse((case / "new_private_parameters.json").exists())
            self.assertEqual({"id", "n", "e"}, set(__import__('json').loads((case / "public_keys.jsonl").read_text().splitlines()[0])))

    def test_wrong_label_and_corrupted_ciphertext_are_rejected(self):
        self.assertEqual(self.report["summary"]["oaep_negative_checks"], 2)
        self.assertTrue(all(check["observed"] == "invalid_ciphertext" for check in self.report["oaep_checks"]))

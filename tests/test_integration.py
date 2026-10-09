import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from rsa_lab.crypto import recover_messages
from rsa_lab.datasets import actual_truth, generate_dataset, repair_public
from rsa_lab.detection import scan
from rsa_lab.evaluation import evaluate
from rsa_lab.models import PublicKey, read_json, read_public, write_json, write_public


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.temp.name) / "dataset"
        generate_dataset(cls.data, count=7, bits=1024, mode="demo")
        cls.keys = read_public(cls.data / "public_keys.jsonl")
        cls.ciphertexts = read_json(cls.data / "ciphertexts.json")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_both_algorithms_and_oaep_with_truth(self):
        for algorithm in ("pairwise", "batch"):
            report = scan(self.keys, algorithm)
            recovered = recover_messages(self.keys, report, self.ciphertexts)
            result = evaluate(self.data / "public_keys.jsonl", self.data / "ground_truth.json", report, recovered)
            self.assertTrue(result["passed"])
            self.assertEqual(result["correctly_factored_moduli"], 5)
            self.assertEqual(result["verified_decryption_records"], 6)

    def test_attack_subprocess_succeeds_in_public_only_directory(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            write_public(folder / "public.jsonl", self.keys)
            write_json(folder / "cipher.json", self.ciphertexts)
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
            for args in (["scan", "--public", "public.jsonl", "--out", "scan.json"],
                         ["recover", "--public", "public.jsonl", "--scan", "scan.json", "--ciphertexts", "cipher.json", "--out", "recovery.json"]):
                process = subprocess.run([sys.executable, "-X", "utf8", "-m", "rsa_lab", *args], cwd=folder, env=env,
                                         capture_output=True, text=True, encoding="utf-8", timeout=20)
                self.assertEqual(process.returncode, 0, process.stderr)
            self.assertFalse((folder / "ground_truth.json").exists())
            self.assertEqual(read_json(folder / "recovery.json")["decrypted_records"], 6)

    def test_repair_clears_current_shared_relations(self):
        with tempfile.TemporaryDirectory() as folder:
            repaired = Path(folder) / "repaired"
            info = repair_public(self.keys, scan(self.keys), repaired)
            self.assertEqual(info["replaced_unique_moduli"], 5)
            self.assertEqual(scan(read_public(repaired / "public_keys.jsonl"))["summary"]["factor_found"], 0)

    def test_generator_checks_actual_bit_length(self):
        self.assertTrue(all(k.n.bit_length() == 1024 for k in self.keys))

    def test_duplicate_labels_do_not_create_expected_vulnerability(self):
        records = [dict(id="a", n="0xf", e="0x3", p="0x3", q="0x5", source="weak"),
                   dict(id="b", n="0xf", e="0x3", p="0x3", q="0x5", source="weak")]
        self.assertEqual(actual_truth(records), set())

    def test_ground_truth_file_hash_must_match(self):
        with tempfile.TemporaryDirectory() as folder:
            truth = read_json(self.data / "ground_truth.json")
            truth["public_sha256"] = "stale"
            target = Path(folder) / "truth.json"
            write_json(target, truth)
            with self.assertRaises(ValueError):
                evaluate(self.data / "public_keys.jsonl", target, scan(self.keys))

    def test_evaluation_detects_wrong_factor_and_plaintext(self):
        report = scan(self.keys)
        wrong = copy.deepcopy(report)
        next(r for r in wrong["unique_results"] if r["status"] == "factor_found")["factor"] = "0x2"
        self.assertFalse(evaluate(self.data / "public_keys.jsonl", self.data / "ground_truth.json", wrong)["passed"])
        recovered = recover_messages(self.keys, report, self.ciphertexts)
        next(r for r in recovered["records"] if r["status"] == "decrypted")["plaintext_b64"] = "d3Jvbmc="
        self.assertFalse(evaluate(self.data / "public_keys.jsonl", self.data / "ground_truth.json", report, recovered)["passed"])

    def test_public_schema_rejects_secret_fields(self):
        with self.assertRaises(ValueError):
            PublicKey.from_dict({"id": "a", "n": "0xf", "e": "0x3", "p": "0x3"})

    def test_public_ids_must_be_unique(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "public.jsonl"
            write_public(path, [PublicKey("same", 15, 3), PublicKey("same", 21, 3)])
            with self.assertRaises(ValueError):
                read_public(path)

    def test_force_required_to_replace_saved_data(self):
        with self.assertRaises(ValueError):
            generate_dataset(self.data, count=7, bits=1024, mode="demo")

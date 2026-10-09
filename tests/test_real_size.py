import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest

from rsa_audit import scan_keys
from rsa_audit.io import load_public_keys

FIXTURES = Path(__file__).parent / "fixtures"


class RSA2048Tests(unittest.TestCase):
    def setUp(self):
        self.keys = load_public_keys(FIXTURES / "rsa2048_public.jsonl")
        self.expected = json.loads((FIXTURES / "rsa2048_expected.json").read_text(encoding="utf-8"))

    def test_fixed_real_size_dataset(self):
        fixture = (FIXTURES / "rsa2048_public.jsonl").read_bytes()
        self.assertEqual(hashlib.sha256(fixture).hexdigest(), self.expected["fixture_sha256"])
        self.assertTrue(all(key.n.bit_length() == 2048 for key in self.keys))
        backends = ["python"]
        if importlib.util.find_spec("gmpy2"):
            backends.append("gmpy2")
        for backend in backends:
            for method in ("batch", "pairwise"):
                with self.subTest(backend=backend, method=method):
                    report = scan_keys(self.keys, method=method, backend=backend)
                    actual = {row.id for row in report.results if row.factor is not None}
                    self.assertEqual(actual, set(self.expected["factored_ids"]))
                    self.assertEqual(report.summary["record_count"], 16)
                    self.assertEqual(report.summary["unique_modulus_count"], 14)
                    self.assertEqual(report.summary["factored_unique_moduli"], 6)
                    self.assertEqual(report.summary["unresolved_unique_moduli"], 0)
                    for row in report.results:
                        if row.factor:
                            self.assertEqual(row.factor * row.cofactor, row.n)
                    if method == "batch":
                        self.assertEqual(report.summary["batch_full_overlap_count"], 4)

    @unittest.skipUnless(importlib.util.find_spec("Crypto"), "optional PyCryptodome is not installed")
    def test_recovered_factor_is_usable_for_oaep_decryption(self):
        # Integration check for B's handoff; no generator secrets are read here.
        from Crypto.Cipher import PKCS1_OAEP
        from Crypto.Hash import SHA256
        from Crypto.PublicKey import RSA

        challenge = json.loads((FIXTURES / "rsa2048_oaep_challenge.json").read_text(encoding="utf-8"))
        report = scan_keys(self.keys)
        result = next(row for row in report.results if row.id == challenge["target_id"])
        p, q = result.factor, result.cofactor
        d = pow(result.e, -1, math.lcm(p - 1, q - 1))
        recovered = RSA.construct((result.n, result.e, d, p, q), consistency_check=True)
        plaintext = PKCS1_OAEP.new(recovered, hashAlgo=SHA256).decrypt(
            bytes.fromhex(challenge["ciphertext_hex"]))
        self.assertEqual(hashlib.sha256(plaintext).hexdigest(), challenge["plaintext_sha256"])


if __name__ == "__main__":
    unittest.main()

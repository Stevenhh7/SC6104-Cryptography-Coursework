import base64
import hashlib
from pathlib import Path
import unittest
from rsa_audit import PublicKey as AuditKey, scan_keys
from rsa_audit.io import load_public_keys
from rsa_lab.crypto import recover_messages
from rsa_lab.detection import scan
from rsa_lab.models import read_json, read_public


class HandoffTests(unittest.TestCase):
    def test_recovery_of_teammate_oaep_challenge(self):
        root = Path(__file__).parent / "fixtures"
        keys = read_public(root / "rsa2048_public.jsonl")
        challenge = read_json(root / "rsa2048_oaep_challenge.json")
        cipher = {"id": challenge["target_id"], "scheme": "RSAES-OAEP", "hash": challenge["hash"],
                  "mgf": challenge["mgf"], "label_b64": base64.b64encode(bytes.fromhex(challenge["label_hex"])).decode(),
                  "ciphertext_b64": base64.b64encode(bytes.fromhex(challenge["ciphertext_hex"])).decode()}
        result = recover_messages(keys, scan(keys), [cipher])
        row = result["records"][0]
        self.assertEqual(row["status"], "decrypted")
        self.assertEqual(hashlib.sha256(base64.b64decode(row["plaintext_b64"])).hexdigest(), challenge["plaintext_sha256"])

    def test_b_dataset_is_readable_by_a_and_adapter_matches(self):
        root = Path("data/demo/public_keys.jsonl")
        if not root.exists():
            self.skipTest("尚未生成 demo")
        native = scan_keys(load_public_keys(root))
        bridged = scan(read_public(root))
        self.assertEqual(bridged["engine"], "rsa_audit.scan_keys")
        self.assertEqual(bridged["summary"]["factor_found"], native.summary["factored_unique_moduli"])

    def test_unresolved_budget_status_is_preserved(self):
        result = scan([AuditKey("a", 15, 3), AuditKey("b", 21, 3), AuditKey("c", 35, 3)], max_fallback_checks=0)
        self.assertEqual(result["summary"]["unresolved"], 3)
        self.assertTrue(all(row["status"] == "unresolved" for row in result["records"]))

import base64
import copy
import math
import unittest
from rsa_lab.crypto import encrypt_message, decrypt_message, recover_messages, recover_private_key
from rsa_lab.datasets import PrimeSource
from rsa_lab.detection import scan
from rsa_lab.models import PublicKey


class CryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = PrimeSource(1024)
        cls.p, cls.q = source.pair()
        _, cls.r = source.pair(cls.p)
        cls.keys = [PublicKey("a", cls.p * cls.q), PublicKey("b", cls.p * cls.r)]
        cls.report = scan(cls.keys)

    def test_private_exponent_uses_lambda(self):
        key = recover_private_key(self.p * self.q, 65537, self.p)
        self.assertEqual(key.d, pow(65537, -1, math.lcm(self.p - 1, self.q - 1)))
        self.assertEqual(key.p * key.q, key.n)

    def test_either_factor_is_accepted(self):
        a = recover_private_key(self.p * self.q, 65537, self.p)
        b = recover_private_key(self.p * self.q, 65537, self.q)
        self.assertEqual(a.d, b.d)

    def test_oaep_roundtrip_binary_message_and_label(self):
        message = b"\xff\x00shared factor"
        row = encrypt_message(self.keys[0], message, b"experiment-104")
        key = recover_private_key(self.keys[0].n, self.keys[0].e, self.p)
        self.assertEqual(decrypt_message(key, row), message)

    def test_recovery_plaintext_matches(self):
        cipher = encrypt_message(self.keys[0], b"hello from B")
        result = recover_messages(self.keys, self.report, [cipher])
        self.assertEqual(result["records"][0]["plaintext_utf8"], "hello from B")

    def test_binary_plaintext_has_no_fake_utf8(self):
        cipher = encrypt_message(self.keys[0], b"\xff")
        row = recover_messages(self.keys, self.report, [cipher])["records"][0]
        self.assertIsNone(row["plaintext_utf8"])
        self.assertEqual(base64.b64decode(row["plaintext_b64"]), b"\xff")

    def test_normal_key_cannot_be_recovered(self):
        cipher = encrypt_message(self.keys[0], b"test")
        report = scan(self.keys[:1])
        row = recover_messages(self.keys[:1], report, [cipher])["records"][0]
        self.assertEqual(row["status"], "not_factorable")

    def test_invalid_factor_rejected(self):
        for factor in (0, 1, self.keys[0].n, 4, True):
            with self.subTest(factor=factor), self.assertRaises(ValueError):
                recover_private_key(self.keys[0].n, 65537, factor)

    def test_composite_cofactor_and_repeated_prime_rejected(self):
        for n, factor in ((45, 3), (49, 7)):
            with self.assertRaises(ValueError):
                recover_private_key(n, 5, factor)

    def test_noninvertible_exponent_rejected(self):
        with self.assertRaises(ValueError):
            recover_private_key(7 * 13, 3, 7)

    def test_ciphertext_corruption_rejected(self):
        cipher = encrypt_message(self.keys[0], b"secret")
        encrypted = bytearray(base64.b64decode(cipher["ciphertext_b64"]))
        encrypted[-1] ^= 1
        cipher["ciphertext_b64"] = base64.b64encode(encrypted).decode()
        row = recover_messages(self.keys, self.report, [cipher])["records"][0]
        self.assertEqual(row["status"], "invalid_ciphertext")

    def test_wrong_oaep_parameters_rejected(self):
        for field, value in (("hash", "SHA-1"), ("mgf", "MGF1-SHA-1"), ("label_b64", "YQ==")):
            cipher = encrypt_message(self.keys[0], b"secret")
            cipher[field] = value
            self.assertEqual(recover_messages(self.keys, self.report, [cipher])["records"][0]["status"], "invalid_ciphertext")

    def test_detection_result_cannot_be_used_for_another_public_input(self):
        report = copy.deepcopy(self.report)
        report["records"][0]["n"] = hex(self.keys[1].n)
        with self.assertRaises(ValueError):
            recover_messages(self.keys, report, [])

    def test_duplicate_modulus_with_different_exponent(self):
        lam = math.lcm(self.p - 1, self.q - 1)
        other_e = 3
        while math.gcd(other_e, lam) != 1:
            other_e += 2
        keys = [*self.keys, PublicKey("other-exponent", self.keys[0].n, other_e)]
        cipher = encrypt_message(keys[-1], b"different e")
        recovered = recover_messages(keys, scan(keys), [cipher])
        self.assertEqual(recovered["records"][0]["plaintext_utf8"], "different e")

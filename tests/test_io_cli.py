import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rsa_audit import PublicKey, scan_keys
from rsa_audit.io import load_public_keys, write_public_keys, write_report

ROOT = Path(__file__).resolve().parents[1]


class IOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_round_trip_and_report(self):
        path = self.directory / "public.jsonl"
        keys = [PublicKey("测试", 15), PublicKey("second", 21)]
        write_public_keys(path, keys)
        self.assertEqual(load_public_keys(path), keys)
        target = self.directory / "out" / "report.json"
        write_report(target, scan_keys(keys))
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["results"][0]["id"], "测试")
        self.assertEqual(data["summary"]["factored_records"], 2)
        self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_bom_blank_lines_and_bare_hex_are_supported(self):
        path = self.directory / "public.jsonl"
        path.write_text('\n{"id":"a","n":"f","e":65537}\n\n', encoding="utf-8-sig")
        self.assertEqual(load_public_keys(path), [PublicKey("a", 15)])

    def test_private_truth_fields_and_malformed_hex_are_rejected(self):
        invalid = [
            '{"id":"a","n":"0xf","e":65537,"p":"0x3"}',
            '{"id":"a","n":15,"e":65537}',
            '{"id":"a","n":"-f","e":65537}',
            '{"id":"a","n":"0x","e":65537}',
            '{"id":"a","n":"1_5","e":65537}',
            '{"id":"a","n":"0xf","n":"0x15","e":65537}',
            '{"id":"a","n":"0xf"}', "[]", "not json",
        ]
        path = self.directory / "bad.jsonl"
        for line in invalid:
            with self.subTest(line=line):
                path.write_text("\n" + line, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "line 2"):
                    load_public_keys(path)


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "rsa_audit", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, encoding="utf-8")

    def test_stdout_is_machine_readable_json(self):
        result = self.run_cli("examples/toy_public_keys.jsonl")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["summary"]["factored_unique_moduli"], 3)
        self.assertEqual(data["summary"]["duplicate_record_count"], 1)
        self.assertIn("batch/python", result.stderr)

    def test_file_output_and_incomplete_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.json"
            result = self.run_cli("examples/toy_public_keys.jsonl", "--max-fallback-checks", 0,
                                  "--output", target)
            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertEqual(result.stdout, "")
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(data["summary"]["unresolved_unique_moduli"], 3)

    def test_input_file_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "public.jsonl"
            write_public_keys(target, [PublicKey("one", 15)])
            original = target.read_bytes()
            result = self.run_cli(target, "--output", target)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_bytes(), original)

    def test_bad_input_and_timeout_exit_codes(self):
        result = self.run_cli("does-not-exist.jsonl")
        self.assertEqual(result.returncode, 2)
        result = self.run_cli("examples/toy_public_keys.jsonl", "--timeout", "1e-12")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stderr)["error"], "timeout")
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()

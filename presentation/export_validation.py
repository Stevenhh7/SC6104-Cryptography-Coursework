"""Refresh offline slide evidence from the actual Python fixture and test log."""

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsa_audit import scan_keys
from rsa_audit.io import load_public_keys


def main():
    fixture = ROOT / "tests/fixtures/rsa2048_public.jsonl"
    expected = json.loads((fixture.parent / "rsa2048_expected.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert digest == expected["fixture_sha256"], "fixture has changed; refresh its expected results first"
    keys = load_public_keys(fixture)
    assert all(key.n.bit_length() == 2048 for key in keys)
    report = scan_keys(keys)
    assert {row.id for row in report.results if row.factor} == set(expected["factored_ids"])
    assert report.summary["unresolved_unique_moduli"] == 0
    log = (ROOT / "results/unittest.txt").read_text(encoding="utf-8")
    test_count = re.search(r"Ran (\d+) tests?", log)
    assert test_count and log.strip().endswith("OK"), "a successful unittest log is required"
    data = {
        "verified_date": "2026-10-09",
        "source_fixture": str(fixture.relative_to(ROOT)).replace("\\", "/"),
        "fixture_sha256": digest,
        "test_methods": int(test_count.group(1)),
        "modulus_bits": 2048,
        **report.summary,
    }
    target = ROOT / "presentation/assets/verified-data.js"
    target.write_text("/* Offline evidence exported from the Python fixture and successful test log. */\n"
                      + "window.RSAValidation = " + json.dumps(data, indent=2) + ";\n", encoding="utf-8")
    print(json.dumps(data))


if __name__ == "__main__":
    main()

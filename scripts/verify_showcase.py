"""Verify committed evidence and replay OAEP from archived public attack inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsa_lab.crypto import recover_messages
from rsa_lab.models import read_json, read_public, sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-index", action="store_true", help="Also compare staged Git bytes with the export hashes")
    parser.add_argument("--git", default=shutil.which("git"), help="Git executable, required with --git-index")
    args = parser.parse_args()
    archive = ROOT / "artifacts"
    manifest = read_json(archive / "EXPORT_MANIFEST.json")
    for name, expected in manifest["sha256"].items():
        path = archive / name
        if sha256_file(path) != expected:
            raise ValueError(f"Archive checksum mismatch: {name}")
        if args.git_index:
            if not args.git:
                raise ValueError("Git executable not found")
            blob = subprocess.check_output([args.git, "-C", str(ROOT), "show", ":artifacts/" + name])
            if hashlib.sha256(blob).hexdigest() != expected:
                raise ValueError(f"Staged Git checksum mismatch: {name}")
    demo = archive / "demo"
    for filename, public in (("scan_batch.json", demo / "public_keys.jsonl"),
                             ("scan_repaired.json", demo / "repaired/public_keys.jsonl")):
        if read_json(demo / filename)["public_sha256"] != sha256_file(public):
            raise ValueError(f"Scan/input mismatch: {filename}")
    input_manifest = read_json(demo / "manifest.json")
    for field, filename in (("public_sha256", "public_keys.jsonl"), ("ciphertexts_sha256", "ciphertexts.json")):
        if input_manifest[field] != sha256_file(demo / filename):
            raise ValueError(f"Demo input manifest mismatch: {filename}")
    public = read_public(demo / "public_keys.jsonl")
    if any(key.n.bit_length() != 2048 for key in public):
        raise ValueError("Archived demo must contain real 2048-bit moduli")
    recovered = recover_messages(public, read_json(demo / "scan_batch.json"), read_json(demo / "ciphertexts.json"))
    actual = {row["id"]: row["plaintext_utf8"] for row in recovered["records"] if row["status"] == "decrypted"}
    expected = {row["id"]: row["plaintext_utf8"] for row in read_json(demo / "decrypted_messages.json")}
    if len(actual) != 6 or actual != expected:
        raise ValueError("Archived OAEP replay does not match saved messages")
    controls = read_json(archive / "controls/validation.json")
    if not controls["summary"]["passed"] or not all(row["passed"] for row in controls["cases"]):
        raise ValueError("Archived controls failed")
    print(json.dumps({"archive_files_verified": len(manifest["sha256"]),
                      "staged_git_bytes_verified": args.git_index,
                      "public_only_oaep_replay_messages": len(actual),
                      "control_scans_verified": len(controls["cases"]), "passed": True}, indent=2))


if __name__ == "__main__":
    main()

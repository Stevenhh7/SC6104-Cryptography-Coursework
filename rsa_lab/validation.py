"""B: independently verified positive, negative and coverage experiments."""

import base64
import copy
from pathlib import Path
import shutil
import subprocess
import sys
from .crypto import recover_messages
from .datasets import actual_truth, generate_dataset, save_dataset
from .evaluation import evaluate
from .experiments import write_csv
from .models import read_json, read_public, sha256_file, write_json


def run_validation_suite(data_root, demo_data, demo_results, output, normal_count=100):
    data_root, demo_data, demo_results, output = map(Path, (data_root, demo_data, demo_results, output))
    output.mkdir(parents=True, exist_ok=True)
    manifest = read_json(demo_data / "manifest.json")
    bits = manifest["config"]["bits"]
    normal = data_root / "normal"
    if not (normal / "public_keys.jsonl").exists():
        generate_dataset(normal, count=normal_count, bits=bits, mode="normal")
    normal_info = read_json(normal / "manifest.json")
    if normal_info["unique_moduli"] != normal_count or normal_info["config"]["bits"] != bits:
        raise ValueError("Saved normal control does not match this experiment")
    normal_truth = read_json(normal / "ground_truth.json")["records"]
    duplicates = data_root / "duplicates_only"
    if not (duplicates / "public_keys.jsonl").exists():
        rows = copy.deepcopy(normal_truth)
        for index, original in enumerate(normal_truth[:2]):
            rows.append({**original, "id": f"duplicate-control-{index}", "source": "duplicate"})
        save_dataset(duplicates, rows, {"bits": bits, "mode": "duplicates_only", "count": normal_count})
    original_truth = read_json(demo_data / "ground_truth.json")["records"]
    weak_moduli = actual_truth(original_truth)
    weak_records = sum(int(row["n"], 16) in weak_moduli for row in original_truth)
    if not weak_moduli or int(original_truth[0]["n"], 16) not in weak_moduli:
        raise ValueError("The demo must begin with a recoverable key for the positive and coverage controls")
    isolated = data_root / "isolated_target"
    if not (isolated / "public_keys.jsonl").exists():
        save_dataset(isolated, [dict(original_truth[0])], {"bits": bits, "mode": "isolated_target", "count": 1})
    repaired = demo_results / "repaired"
    replacements = {row["id"]: row for row in read_json(repaired / "new_private_parameters.json")}
    repaired_truth = []
    for original in original_truth:
        if original["id"] in replacements:
            row = dict(replacements[original["id"]])
            row["message_b64"] = base64.b64encode(b"Fresh RSA key after repair").decode("ascii")
        else:
            row = dict(original)
        repaired_truth.append(row)
    private_truth = output / "private_truth/repaired.json"
    write_json(private_truth, {"public_sha256": sha256_file(repaired / "public_keys.jsonl"), "records": repaired_truth})
    cases = [
        ("normal", normal, normal / "ground_truth.json", 0, 0),
        ("duplicates_only", duplicates, duplicates / "ground_truth.json", 0, 0),
        ("isolated_target", isolated, isolated / "ground_truth.json", 0, 0),
        ("shared_prime_demo", demo_data, demo_data / "ground_truth.json", len(weak_moduli), weak_records),
        ("repaired", repaired, private_truth, 0, 0),
    ]
    rows, checks = [], []
    for name, source, truth, expected_moduli, expected_messages in cases:
        public_folder = output / "attack_inputs" / name
        public_folder.mkdir(parents=True, exist_ok=True)
        for filename in ("public_keys.jsonl", "ciphertexts.json"):
            shutil.copyfile(source / filename, public_folder / filename)
        keys = read_public(public_folder / "public_keys.jsonl")
        if any(key.n.bit_length() != bits for key in keys):
            raise ValueError("Control contains a modulus with the wrong actual bit length")
        for algorithm in ("batch", "pairwise"):
            scan_file = public_folder / f"scan_{algorithm}.json"
            recovery_file = public_folder / f"recovery_{algorithm}.json"
            commands = [
                ["scan", "--public", str(public_folder / "public_keys.jsonl"), "--algorithm", algorithm, "--out", str(scan_file)],
                ["recover", "--public", str(public_folder / "public_keys.jsonl"), "--scan", str(scan_file),
                 "--ciphertexts", str(public_folder / "ciphertexts.json"), "--out", str(recovery_file)],
            ]
            for command in commands:
                process = subprocess.run([sys.executable, "-X", "utf8", "-m", "rsa_lab", *command],
                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, encoding="utf-8", timeout=30)
                if process.returncode:
                    raise RuntimeError(process.stderr or process.stdout)
            scan = read_json(scan_file)
            result = evaluate(source / "public_keys.jsonl", truth, scan, read_json(recovery_file))
            passed = (result["passed"] and result["correctly_factored_moduli"] == expected_moduli
                      and result["verified_decryption_records"] == expected_messages)
            row = {"case": name, "algorithm": algorithm, "bits": bits, "records": len(keys),
                   "unique_moduli": len({key.n for key in keys}), "expected_recoverable": expected_moduli,
                   "correctly_factored": result["correctly_factored_moduli"],
                   "verified_messages": result["verified_decryption_records"],
                   "false_positives": result["false_positives"], "false_negatives": result["false_negatives"],
                   "passed": passed, "public_sha256": scan["public_sha256"]}
            rows.append(row)
            print(f"{name} / {algorithm}: factors={row['correctly_factored']}, messages={row['verified_messages']}, passed={passed}", flush=True)
    keys = read_public(demo_data / "public_keys.jsonl")
    scan = read_json(output / "attack_inputs/shared_prime_demo/scan_batch.json")
    ciphertext = read_json(demo_data / "ciphertexts.json")[0]
    for name in ("wrong_oaep_label", "corrupted_ciphertext"):
        changed = dict(ciphertext)
        if name == "wrong_oaep_label":
            changed["label_b64"] = base64.b64encode(b"different label").decode("ascii")
        else:
            payload = bytearray(base64.b64decode(changed["ciphertext_b64"]))
            payload[-1] ^= 1
            changed["ciphertext_b64"] = base64.b64encode(payload).decode("ascii")
        observed = recover_messages(keys, scan, [changed])["records"][0]["status"]
        checks.append({"case": name, "expected": "invalid_ciphertext", "observed": observed, "passed": observed == "invalid_ciphertext"})
    report = {"summary": {"bits": bits, "scan_runs": len(rows), "oaep_negative_checks": len(checks),
                          "passed": all(row["passed"] for row in rows) and all(row["passed"] for row in checks)},
              "cases": rows, "oaep_checks": checks,
              "repair_legitimate_roundtrips": read_json(repaired / "repair_summary.json")["new_key_roundtrip_records"]}
    write_csv(output / "controls.csv", rows)
    write_json(output / "validation.json", report)
    return report

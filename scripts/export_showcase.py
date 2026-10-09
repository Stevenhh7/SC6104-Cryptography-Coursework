"""Archive measured evidence and update the offline presentation, after experiments."""

from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import shutil
from statistics import median
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "artifacts"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix == ".svg":
        # Matplotlib emits CRLF and trailing spaces on Windows; archive canonical text.
        text = source.read_text(encoding="utf-8")
        target.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8", newline="\n")
    elif target.suffix in (".json", ".jsonl", ".csv", ".md", ".txt"):
        target.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
    else:
        shutil.copyfile(source, target)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive_input_hashes(folder, scan_name):
    """Git publishes LF text; retain original-run hashes and stamp archived bytes."""
    scan_path = OUT / "demo" / scan_name
    scan = read(scan_path)
    scan["source_public_sha256"] = scan["public_sha256"]
    scan["public_sha256"] = digest(folder / "public_keys.jsonl")
    write(scan_path, scan)


def export():
    verification = read(ROOT / "results/demo/verification.json")
    if not verification["passed"]:
        raise ValueError("Demo verification failed; do not publish results.")
    with (ROOT / "results/benchmark/raw_results.csv").open(encoding="utf-8-sig", newline="") as stream:
        raw = list(csv.DictReader(stream))
    if any(row["status"] not in ("ok", "timeout") or
           (row["status"] == "ok" and row["verification_passed"] != "True") for row in raw):
        raise ValueError("Benchmark contains errors or unverified completed scans.")
    with (ROOT / "results/benchmark/summary.csv").open(encoding="utf-8-sig", newline="") as stream:
        summary = list(csv.DictReader(stream))
    pairs = {int(row["unique_moduli"]): row for row in summary if row["algorithm"] == "pairwise"}
    performance = []
    for row in summary:
        if row["algorithm"] == "batch":
            size = int(row["unique_moduli"])
            performance.append({"size": size, "pairwise": float(pairs[size]["median_seconds"]) if pairs[size]["median_seconds"] else None,
                                "batch": float(row["median_seconds"])})
    recovery = read(ROOT / "results/demo/recovery.json")
    messages = [{"id": row["id"], "plaintext_utf8": row["plaintext_utf8"]}
                for row in recovery["records"] if row["status"] == "decrypted"]
    repaired = read(ROOT / "results/demo/scan_repaired.json")
    scan = read(ROOT / "results/demo/scan_batch.json")
    from rsa_lab.crypto import recover_private_key
    from rsa_lab.models import read_public
    from math import lcm
    public_keys = {key.id: key for key in read_public(ROOT / "data/demo/public_keys.jsonl")}
    selected = next(row for row in scan["records"] if row["status"] == "factor_found")
    public_key = public_keys[selected["id"]]
    private = recover_private_key(public_key.n, public_key.e, int(selected["factor"], 16))
    reconstruction = {"id": public_key.id, "bits": public_key.n.bit_length(), "e": public_key.e,
                      "p_bits": private.p.bit_length(), "q_bits": private.q.bit_length(),
                      "factor_product_verified": private.p * private.q == public_key.n,
                      "inverse_verified": private.e * private.d % lcm(private.p-1, private.q-1) == 1}
    controls = read(ROOT / "results/controls/validation.json")
    if not controls["summary"]["passed"]:
        raise ValueError("Validation controls failed; do not publish results.")
    stage_names = ("preprocess", "conversion", "product_tree", "remainder_tree", "final_gcd", "fallback", "assemble")
    largest = max(row["size"] for row in performance)
    stage_rows = [row for row in raw if int(row["unique_moduli"]) == largest and row["algorithm"] == "batch" and row["status"] == "ok"]
    stages = {name: median(float(row[name + "_seconds"]) for row in stage_rows) for name in stage_names}
    with (ROOT / "results/pool/pool_results.csv").open(encoding="utf-8-sig", newline="") as stream:
        pool_rows = list(csv.DictReader(stream))
    pool = [{"size": size, "median": median(float(row["vulnerable_fraction"]) for row in pool_rows if int(row["pool_size"]) == size)}
            for size in sorted({int(row["pool_size"]) for row in pool_rows})]
    evidence = {"performance": performance, "demo": verification, "messages": messages,
                "input": read(ROOT / "data/demo/manifest.json"),
                "repair": read(ROOT / "results/demo/repaired/repair_summary.json"),
                "repaired_found": repaired["summary"]["factor_found"], "controls": controls,
                "reconstruction": reconstruction, "stages": stages, "pool": pool,
                "fallback_candidates": scan["summary"]["fallback_candidates"],
                "fallback_checks": scan["summary"]["fallback_gcd_calls"],
                "benchmark_config": read(ROOT / "results/benchmark/benchmark_config.json")}
    for name in ("raw_results.csv", "summary.csv", "environment.json", "benchmark_config.json"):
        copy(ROOT / "results/benchmark" / name, OUT / "benchmark" / name)
    for name in ("scan_times.png", "batch_stages.png", "scan_times_presentation.png", "scan_times_presentation.svg"):
        copy(ROOT / "results/figures" / name, OUT / "figures" / name)
    copy(ROOT / "results/pool/weak_pool.png", OUT / "figures/weak_pool.png")
    copy(ROOT / "results/pool/pool_results.csv", OUT / "pool/pool_results.csv")
    for name in ("controls.csv", "validation.json"):
        copy(ROOT / "results/controls" / name, OUT / "controls" / name)
    copy(ROOT / "results/demo/shared_factors.png", OUT / "figures/shared_factors.png")
    copy(ROOT / "results/test_log.txt", OUT / "test_log.txt")
    for name in ("public_keys.jsonl", "ciphertexts.json", "manifest.json"):
        copy(ROOT / "data/demo" / name, OUT / "demo" / name)
    for name in ("verification.json", "scan_batch.json", "scan_repaired.json"):
        copy(ROOT / "results/demo" / name, OUT / "demo" / name)
    for name in ("public_keys.jsonl", "ciphertexts.json"):
        copy(ROOT / "results/demo/repaired" / name, OUT / "demo/repaired" / name)
    archive_input_hashes(OUT / "demo", "scan_batch.json")
    archive_input_hashes(OUT / "demo/repaired", "scan_repaired.json")
    archived_manifest = read(OUT / "demo/manifest.json")
    for name in ("public", "ciphertexts"):
        field = name + "_sha256"
        archived_manifest["source_" + field] = archived_manifest[field]
        filename = "public_keys.jsonl" if name == "public" else "ciphertexts.json"
        archived_manifest[field] = digest(OUT / "demo" / filename)
    archived_manifest["archive_line_endings"] = "UTF-8 LF; original-run byte hashes retained as source_*"
    write(OUT / "demo/manifest.json", archived_manifest)
    evidence["input"] = archived_manifest
    script = "window.RSA_FINAL_DATA = " + json.dumps(evidence, ensure_ascii=False, indent=2) + ";\n"
    (ROOT / "presentation/assets/final-data.js").write_text(script, encoding="utf-8", newline="\n")
    write(OUT / "demo/decrypted_messages.json", messages)
    repair_summary = dict(evidence["repair"])
    repair_summary["source_original_public_sha256"] = repair_summary["original_public_sha256"]
    repair_summary["original_public_sha256"] = archived_manifest["public_sha256"]
    write(OUT / "demo/repair_summary.json", repair_summary)
    write(OUT / "benchmark/input_manifests.json", {
        f"n-{size}": read(ROOT / f"data/bench/n-{size}/manifest.json") for size in pairs})
    report = (ROOT / "RESULTS.md").read_text(encoding="utf-8")
    report = report.replace("results/figures/", "figures/").replace("results/pool/weak_pool.png", "figures/weak_pool.png")
    report = report.replace("results/demo/scan_batch.json", "demo/scan_batch.json")
    (OUT / "RESULTS.md").write_text(report, encoding="utf-8", newline="\n")
    hashes = {str(path.relative_to(OUT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(OUT.rglob("*")) if path.is_file() and path.name != "EXPORT_MANIFEST.json"}
    write(OUT / "EXPORT_MANIFEST.json", {"exported_at_utc": datetime.now(timezone.utc).isoformat(),
          "engine": "rsa_audit.scan_keys", "completed_scans": sum(row["status"] == "ok" for row in raw),
          "timed_out_scans": sum(row["status"] == "timeout" for row in raw), "sha256": hashes})
    print(f"Exported {len(hashes)} evidence files and final-data.js.")


if __name__ == "__main__":
    export()

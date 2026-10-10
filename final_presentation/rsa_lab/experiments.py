"""B: fresh-process timings, explicit timeouts, measured (not estimated) results."""

from pathlib import Path
from statistics import median
from time import perf_counter
import csv
import ctypes
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from .crypto import recover_messages
from .datasets import generate_dataset
from .detection import scan, arithmetic
from .evaluation import evaluate
from .models import read_json, read_public, write_json


def peak_rss_bytes():
    """OS-reported peak RSS of the entire worker process, including imports."""
    if sys.platform == "win32":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return counters.PeakWorkingSetSize
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value if sys.platform == "darwin" else value * 1024
    except (ImportError, AttributeError):
        return None


def environment(backend="auto"):
    packages = {}
    for package in ("pycryptodome", "cryptography", "matplotlib", "gmpy2"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    info = {"python": sys.version, "platform": platform.platform(), "cpu": platform.processor(),
            "logical_cpus": os.cpu_count(), "packages": packages,
            "backend": arithmetic(backend)[2], "memory_measurement": "worker whole-process peak RSS; includes imports and input",
            "engine": "rsa_audit.scan_keys",
            "scan_timing": "native rsa_audit total_seconds; excludes lab adapter, file I/O, keygen, recovery and evaluation"}
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in ("total_phys", "available_phys", "total_pagefile", "available_pagefile", "total_virtual", "available_virtual", "available_extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            info["physical_memory_bytes"] = status.total_phys
    return info


def benchmark_worker(public_path, algorithm, output, backend="auto"):
    keys = read_public(public_path)
    result = scan(keys, algorithm, backend)
    result["worker_peak_rss_bytes"] = peak_rss_bytes()
    write_json(output, result)


def write_csv(path, rows, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def run_benchmarks(root, output, sizes, repeats=3, timeout=45.0, backend="auto"):
    if repeats < 1 or timeout <= 0:
        raise ValueError("repeats 和 timeout 必须为正")
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    backend = "gmpy2" if arithmetic(backend)[2] == "gmpy2/GMP" else "python"
    write_json(output / "environment.json", environment(backend))
    write_json(output / "benchmark_config.json", {"sizes": sizes, "repeats": repeats, "worker_timeout_seconds": timeout,
               "backend": backend, "timeout_scope": "whole subprocess including startup, I/O and scan; timed-out scan seconds left empty"})
    rows = []
    for size in sizes:
        dataset = root / f"n-{size}"
        manifest = read_json(dataset / "manifest.json")
        if manifest["unique_moduli"] != size:
            raise ValueError("数据集规模与实验要求不同")
        keys = read_public(dataset / "public_keys.jsonl")
        ciphertexts = read_json(dataset / "ciphertexts.json")
        for repeat in range(1, repeats + 1):
            order = ("pairwise", "batch") if repeat % 2 else ("batch", "pairwise")
            for algorithm in order:
                detail = output / "scans" / f"n-{size}-{algorithm}-{repeat}.json"
                row = {"dataset": f"n-{size}", "unique_moduli": size, "records": manifest["record_count"],
                       "bits": manifest["config"]["bits"], "actual_weak_fraction": manifest["actual_weak_fraction"],
                       "algorithm": algorithm, "backend": backend, "repeat": repeat, "status": "ok", "total_seconds": "",
                       "preprocess_seconds": "", "conversion_seconds": "", "product_tree_seconds": "", "remainder_tree_seconds": "",
                       "final_gcd_seconds": "", "fallback_seconds": "", "pairwise_seconds": "", "assemble_seconds": "",
                       "fallback_candidates": "", "fallback_gcd_calls": "", "pairwise_gcd_calls": "",
                       "peak_rss_bytes": "", "expected_recoverable": manifest["actual_vulnerable_moduli"],
                       "correctly_factored": "", "false_positives": "", "false_negatives": "",
                       "verified_decryption_moduli": "", "verification_passed": "", "worker_wall_seconds": "", "error": ""}
                command = [sys.executable, "-X", "utf8", "-m", "rsa_lab", "_bench-worker", "--public",
                           str(dataset / "public_keys.jsonl"), "--algorithm", algorithm, "--backend", backend, "--out", str(detail)]
                print(f"扫描 n={size}, {algorithm}, 第 {repeat}/{repeats} 次…", flush=True)
                start = perf_counter()
                try:
                    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
                                             cwd=Path(__file__).resolve().parents[1])
                    row["worker_wall_seconds"] = perf_counter() - start
                    if process.returncode:
                        row["status"] = "error"
                        row["error"] = process.stderr.strip() or process.stdout.strip()
                    else:
                        report = read_json(detail)
                        recovery = recover_messages(keys, report, ciphertexts)
                        verification = evaluate(dataset / "public_keys.jsonl", dataset / "ground_truth.json", report, recovery)
                        for stage, value in report["timings_seconds"].items():
                            row[stage + "_seconds"] = value
                        for name in ("fallback_candidates", "fallback_gcd_calls", "pairwise_gcd_calls"):
                            row[name] = report["summary"][name]
                        row["peak_rss_bytes"] = report["worker_peak_rss_bytes"]
                        row["correctly_factored"] = verification["correctly_factored_moduli"]
                        row["false_positives"] = verification["false_positives"]
                        row["false_negatives"] = verification["false_negatives"]
                        row["verified_decryption_moduli"] = verification["verified_decryption_moduli"]
                        row["verification_passed"] = verification["passed"]
                        write_json(detail.with_name(detail.stem + "-verification.json"), verification)
                        if not verification["passed"]:
                            row["status"] = "verification_failed"
                except subprocess.TimeoutExpired:
                    row["status"] = "timeout"
                    row["worker_wall_seconds"] = perf_counter() - start
                rows.append(row)
                write_csv(output / "raw_results.csv", rows)
                print(f"  {row['status']}; 扫描秒数={row['total_seconds']}; 正确恢复={row['correctly_factored']}", flush=True)
    summaries = []
    for size in sizes:
        for algorithm in ("pairwise", "batch"):
            group = [r for r in rows if r["unique_moduli"] == size and r["algorithm"] == algorithm]
            successes = [r for r in group if r["status"] == "ok"]
            summaries.append({"unique_moduli": size, "algorithm": algorithm, "successful_runs": len(successes),
                              "total_runs": len(group), "timeouts": sum(r["status"] == "timeout" for r in group),
                              "median_seconds": median(r["total_seconds"] for r in successes) if successes else "",
                              "min_seconds": min((r["total_seconds"] for r in successes), default=""),
                              "max_seconds": max((r["total_seconds"] for r in successes), default=""),
                              "median_peak_rss_bytes": median(r["peak_rss_bytes"] for r in successes if r["peak_rss_bytes"] is not None)
                                  if any(r["peak_rss_bytes"] is not None for r in successes) else "",
                              "all_verifications_passed": all(r["verification_passed"] for r in successes) if successes else ""})
    write_csv(output / "summary.csv", summaries)
    return summaries


def run_pool_experiment(root, output, count=60, sizes=(4, 16, 64), repeats=3, seed=104):
    if repeats < 1 or count < 2 or min(sizes, default=0) < 1:
        raise ValueError("素数池实验参数无效")
    root, output = Path(root), Path(output)
    rows = []
    for size in sizes:
        for repeat in range(1, repeats + 1):
            dataset = root / f"pool-{size}-r-{repeat}"
            if not (dataset / "public_keys.jsonl").exists():
                print(f"生成素数池实验: pool={size}, repeat={repeat}", flush=True)
                generate_dataset(dataset, count=count, bits=2048, mode="pool", pool_size=size, seed=seed + repeat)
            manifest = read_json(dataset / "manifest.json")
            config = manifest["config"]
            if config.get("mode") != "pool" or config.get("count") != count or config.get("pool_size") != size or config.get("seed") != seed + repeat:
                raise ValueError("已有素数池实验与要求不一致")
            keys = read_public(dataset / "public_keys.jsonl")
            report = scan(keys)
            recovery = recover_messages(keys, report, read_json(dataset / "ciphertexts.json"))
            verification = evaluate(dataset / "public_keys.jsonl", dataset / "ground_truth.json", report, recovery)
            rows.append({"pool_size": size, "keys": count, "repeat": repeat,
                         "vulnerable_moduli": manifest["actual_vulnerable_moduli"],
                         "vulnerable_fraction": manifest["actual_weak_fraction"],
                         "correctly_factored": verification["correctly_factored_moduli"],
                         "verified_decryption_moduli": verification["verified_decryption_moduli"],
                         "verification_passed": verification["passed"], "scan_seconds": report["timings_seconds"]["total"]})
            write_csv(output / "pool_results.csv", rows)
            print(f"  pool={size}: {rows[-1]['vulnerable_moduli']}/{count} 可恢复", flush=True)
    return rows

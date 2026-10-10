"""Command line entry points. scan/recover never open ground_truth.json."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from .models import PublicKey, read_json, read_public, sha256_file, write_json, write_public
from .detection import scan


def print_json(value):
    print(json.dumps(value, ensure_ascii=False, indent=2), flush=True)


def integers(text):
    try:
        values = [int(value) for value in text.split(",")]
        if not values or min(values) <= 0:
            raise ValueError
        return sorted(set(values))
    except ValueError:
        raise argparse.ArgumentTypeError("需要逗号分隔的正整数，例如 100,300,1000")


def cmd_generate(args):
    from .datasets import generate_dataset
    print_json(generate_dataset(args.out, count=args.count, bits=args.bits, mode=args.mode,
                               weak_fraction=args.weak_fraction, pool_size=args.pool_size, seed=args.seed, force=args.force))


def cmd_scan(args):
    report = scan(read_public(args.public), args.algorithm, args.backend)
    report["public_sha256"] = sha256_file(args.public)
    write_json(args.out, report)
    print_json({"algorithm": report["algorithm"], "backend": report["backend"], **report["summary"], "scan_seconds": report["timings_seconds"]["total"]})


def cmd_recover(args):
    from .crypto import recover_messages
    report = read_json(args.scan)
    if report.get("public_sha256") != sha256_file(args.public):
        raise ValueError("检测文件与公开输入的摘要不一致")
    recovery = recover_messages(read_public(args.public), report, read_json(args.ciphertexts), args.private_dir)
    write_json(args.out, recovery)
    decrypted = [r for r in recovery["records"] if r["status"] == "decrypted"]
    print_json({"decrypted_records": len(decrypted), "example_plaintexts": [r["plaintext_utf8"] for r in decrypted[:3]]})


def cmd_evaluate(args):
    from .evaluation import evaluate
    result = evaluate(args.public, args.truth, read_json(args.scan), read_json(args.recovery) if args.recovery else None)
    write_json(args.out, result)
    print_json(result)
    if not result["passed"]:
        raise ValueError("实验核验未通过，请检查结果文件")


def cmd_repair(args):
    from .datasets import repair_public
    report = read_json(args.scan)
    if report.get("public_sha256") != sha256_file(args.public):
        raise ValueError("检测文件与公开输入摘要不一致")
    info = repair_public(read_public(args.public), report, args.out)
    info["original_public_sha256"] = sha256_file(args.public)
    write_json(Path(args.out) / "repair_summary.json", info)
    print_json(info)


def run_cli(arguments):
    command = [sys.executable, "-X", "utf8", "-m", "rsa_lab", *map(str, arguments)]
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", cwd=Path(__file__).resolve().parents[1])
    if process.stdout:
        print(process.stdout.rstrip(), flush=True)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "子进程失败")


def cmd_demo(args):
    from .datasets import generate_dataset
    data, out = Path(args.data).resolve(), Path(args.out).resolve()
    if not (data / "public_keys.jsonl").exists():
        print("[1/6] Generate the local 2048-bit experiment dataset", flush=True)
        generate_dataset(data, count=args.count, bits=2048, mode="demo")
    else:
        print("[1/6] Load the saved 2048-bit experiment dataset", flush=True)
    if any(k.n.bit_length() != 2048 for k in read_public(data / "public_keys.jsonl")):
        raise ValueError("最终 demo 只接受实际为 2048-bit 的模数")
    public_only = out / "attack_input"
    public_only.mkdir(parents=True, exist_ok=True)
    for name in ("public_keys.jsonl", "ciphertexts.json"):
        shutil.copyfile(data / name, public_only / name)
    public = public_only / "public_keys.jsonl"
    ciphertexts = public_only / "ciphertexts.json"
    scan_file = out / "scan_batch.json"
    recovery = out / "recovery.json"
    print("[2/6] Scan public keys with batch GCD in a separate process", flush=True)
    run_cli(["scan", "--public", public, "--algorithm", "batch", "--out", scan_file])
    print("[3/6] Reconstruct private keys and decrypt OAEP using public attack inputs", flush=True)
    run_cli(["recover", "--public", public, "--scan", scan_file, "--ciphertexts", ciphertexts,
             "--out", recovery, "--private-dir", out / "recovered_private_keys"])
    print("[4/6] After the attack, verify factors and plaintext against separate ground truth", flush=True)
    run_cli(["evaluate", "--public", public, "--truth", data / "ground_truth.json", "--scan", scan_file,
             "--recovery", recovery, "--out", out / "verification.json"])
    repaired = out / "repaired"
    print("[5/6] Replace affected keys using fresh cryptographic randomness", flush=True)
    if (repaired / "public_keys.jsonl").exists():
        info = read_json(repaired / "repair_summary.json")
        if info["original_public_sha256"] != sha256_file(public):
            raise ValueError("现有修复数据来自另一份输入，请更换 --out")
        info["note"] = "Only current shared-factor relationships tested; duplicate record mappings preserved"
        print_json(info)
    else:
        run_cli(["repair", "--public", public, "--scan", scan_file, "--out", repaired])
    print("[6/6] Rescan the repaired collection and repeat the public-input attack", flush=True)
    repaired_scan = out / "scan_repaired.json"
    run_cli(["scan", "--public", repaired / "public_keys.jsonl", "--out", repaired_scan])
    run_cli(["recover", "--public", repaired / "public_keys.jsonl", "--scan", repaired_scan,
             "--ciphertexts", repaired / "ciphertexts.json", "--out", out / "recovery_repaired.json"])
    clean = read_json(repaired_scan)
    if clean["summary"]["factor_found"] or clean["summary"]["unresolved"]:
        raise ValueError("重新生成后仍有共享关系，检查修复结果")
    from .plots import relation_plot
    relation_plot(read_public(public), out / "shared_factors.png")
    print("Demo passed. No shared factor found only describes this input collection.", flush=True)


def cmd_import_pem(args):
    from Crypto.PublicKey import RSA
    keys = []
    for index, filename in enumerate(args.files):
        key = RSA.import_key(Path(filename).read_bytes()).public_key()
        keys.append(PublicKey(f"pem-{index:05d}", key.n, key.e))
    write_public(args.out, keys)
    print_json({"imported_records": len(keys), "output": str(args.out)})


def main():
    parser = argparse.ArgumentParser(description="RSA 共享素因子检测、私钥恢复与本地实验")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("generate", help="生成公开数据、密文与独立真值")
    p.add_argument("--out", required=True); p.add_argument("--count", type=int, default=100)
    p.add_argument("--bits", type=int, default=2048)
    p.add_argument("--mode", choices=("demo", "pairs", "normal", "pool"), default="demo")
    p.add_argument("--weak-fraction", type=float, default=.05); p.add_argument("--pool-size", type=int, default=16)
    p.add_argument("--seed", type=int, default=104); p.add_argument("--force", action="store_true")
    p.set_defaults(handler=cmd_generate)
    p = sub.add_parser("scan", help="只根据公钥检测")
    p.add_argument("--public", required=True); p.add_argument("--out", required=True)
    p.add_argument("--algorithm", choices=("batch", "pairwise"), default="batch"); p.set_defaults(handler=cmd_scan)
    p.add_argument("--backend", choices=("python", "gmpy2", "auto"), default="auto")
    p = sub.add_parser("recover", help="只根据公开数据恢复私钥并解密")
    p.add_argument("--public", required=True); p.add_argument("--scan", required=True)
    p.add_argument("--ciphertexts", required=True); p.add_argument("--out", required=True)
    p.add_argument("--private-dir"); p.set_defaults(handler=cmd_recover)
    p = sub.add_parser("evaluate", help="检测完成后读取真值核验")
    p.add_argument("--public", required=True); p.add_argument("--truth", required=True)
    p.add_argument("--scan", required=True); p.add_argument("--recovery"); p.add_argument("--out", required=True)
    p.set_defaults(handler=cmd_evaluate)
    p = sub.add_parser("repair", help="更换受影响密钥，不读取原始真值")
    p.add_argument("--public", required=True); p.add_argument("--scan", required=True); p.add_argument("--out", required=True)
    p.set_defaults(handler=cmd_repair)
    p = sub.add_parser("demo", help="完整公开输入攻击、独立核验与修复演示")
    p.add_argument("--data", default="data/demo"); p.add_argument("--out", default="results/demo")
    p.add_argument("--count", type=int, default=100); p.set_defaults(handler=cmd_demo)
    p = sub.add_parser("validate", help="Run positive, negative, duplicate and coverage controls")
    p.add_argument("--data-root", default="data/controls")
    p.add_argument("--demo-data", default="data/demo")
    p.add_argument("--demo-results", default="results/demo")
    p.add_argument("--out", default="results/controls")
    def validate(args):
        from .validation import run_validation_suite
        report = run_validation_suite(args.data_root, args.demo_data, args.demo_results, args.out)
        print_json(report["summary"])
        if not report["summary"]["passed"]:
            raise ValueError("Control experiment verification failed")
    p.set_defaults(handler=validate)
    p = sub.add_parser("prepare-bench", help="生成一次大集合，保存多个固定规模前缀")
    p.add_argument("--data-root", default="data/bench"); p.add_argument("--sizes", type=integers, default=[100, 300, 1000, 3000])
    p.add_argument("--bits", type=int, default=2048); p.add_argument("--weak-fraction", type=float, default=.05)
    def prepare(args):
        from .datasets import prepare_benchmarks
        prepare_benchmarks(args.data_root, args.sizes, args.bits, args.weak_fraction)
    p.set_defaults(handler=prepare)
    p = sub.add_parser("benchmark", help="全新子进程计时、超时处理与正确性核验")
    p.add_argument("--data-root", default="data/bench"); p.add_argument("--out", default="results/benchmark")
    p.add_argument("--sizes", type=integers, default=[100, 300, 1000, 3000]); p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--timeout", type=float, default=45)
    p.add_argument("--backend", choices=("python", "gmpy2", "auto"), default="auto")
    def benchmark(args):
        from .experiments import run_benchmarks
        summaries = run_benchmarks(args.data_root, args.out, args.sizes, args.repeats, args.timeout, args.backend)
        print_json(summaries)
        if any(r["successful_runs"] + r["timeouts"] != r["total_runs"] for r in summaries):
            raise ValueError("性能实验有错误或核验失败，请检查原始 CSV")
    p.set_defaults(handler=benchmark)
    p = sub.add_parser("_bench-worker", help=argparse.SUPPRESS)
    p.add_argument("--public", required=True); p.add_argument("--algorithm", choices=("batch", "pairwise"), required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--backend", choices=("python", "gmpy2", "auto"), default="auto")
    def worker(args):
        from .experiments import benchmark_worker
        benchmark_worker(args.public, args.algorithm, args.out, args.backend)
    p.set_defaults(handler=worker)
    p = sub.add_parser("plot", help="生成两张核心性能图")
    p.add_argument("--csv", default="results/benchmark/raw_results.csv"); p.add_argument("--out", default="results/figures")
    def plot(args):
        from .plots import benchmark_plots
        print_json(benchmark_plots(args.csv, args.out))
    p.set_defaults(handler=plot)
    p = sub.add_parser("pool-experiment", help="弱素数池扩展实验")
    p.add_argument("--data-root", default="data/pool"); p.add_argument("--out", default="results/pool")
    p.add_argument("--count", type=int, default=60); p.add_argument("--sizes", type=integers, default=[4, 16, 64])
    p.add_argument("--repeats", type=int, default=3); p.add_argument("--seed", type=int, default=104)
    def pool(args):
        from .experiments import run_pool_experiment
        from .plots import pool_plot
        rows = run_pool_experiment(args.data_root, args.out, args.count, args.sizes, args.repeats, args.seed)
        pool_plot(Path(args.out) / "pool_results.csv", args.out)
        if any(not row["verification_passed"] for row in rows):
            raise ValueError("素数池实验核验失败")
    p.set_defaults(handler=pool)
    p = sub.add_parser("import-pem", help="将本地 RSA PEM 转为公开 JSONL")
    p.add_argument("files", nargs="+"); p.add_argument("--out", required=True); p.set_defaults(handler=cmd_import_pem)
    p = sub.add_parser("graph", help="根据公开输入绘制共享因子关系图")
    p.add_argument("--public", required=True); p.add_argument("--out", required=True)
    def graph(args):
        from .plots import relation_plot
        print(relation_plot(read_public(args.public), args.out))
    p.set_defaults(handler=graph)
    p = sub.add_parser("report", help="Generate the measured report and English presentation script")
    def report(args):
        from .reporting import build_report
        print(build_report(Path.cwd()))
    p.set_defaults(handler=report)
    args = parser.parse_args()
    try:
        args.handler(args)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"错误: {error}\n")

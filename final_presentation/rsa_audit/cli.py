"""CLI: JSON report to stdout/file; short human summary to stderr."""

import argparse
import json
import sys
from pathlib import Path

from .io import load_public_keys, write_report
from .models import ScanTimeout
from .scanner import scan_keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect shared factors in public RSA JSONL records.")
    parser.add_argument("input", type=Path, help="JSONL with exactly id, n (hex string), e (integer)")
    parser.add_argument("--method", choices=("batch", "pairwise"), default="batch")
    parser.add_argument("--backend", choices=("python", "gmpy2"), default="python")
    parser.add_argument("--output", type=Path, help="write JSON here instead of stdout")
    parser.add_argument("--timeout", type=float, help="cooperative scan deadline in seconds")
    parser.add_argument("--max-fallback-checks", type=int, help="limit extra pairwise GCDs; default unlimited")
    args = parser.parse_args(argv)
    try:
        if args.output is not None and args.input.resolve() == args.output.resolve():
            raise ValueError("output must not overwrite the public input file")
        keys = load_public_keys(args.input)
        report = scan_keys(keys, method=args.method, backend=args.backend,
                           max_fallback_checks=args.max_fallback_checks,
                           timeout_seconds=args.timeout)
        if args.output is None:
            print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2))
        else:
            write_report(args.output, report)
        summary = report.summary
        print(
            f"{report.method}/{report.backend}: {summary['record_count']} records, "
            f"{summary['unique_modulus_count']} unique moduli, "
            f"{summary['factored_unique_moduli']} factored, "
            f"{summary['unresolved_unique_moduli']} unresolved; "
            f"{report.timings['total_seconds']:.6f}s",
            file=sys.stderr,
        )
        # Incomplete fallback is visible to scripts, even though its report is saved.
        return 4 if summary["unresolved_unique_moduli"] else 0
    except ScanTimeout as exc:
        print(json.dumps({"error": "timeout", "stage": exc.stage}), file=sys.stderr)
        return 3
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Bridge to the team's A engine. There is only one detection implementation."""

from math import gcd
from rsa_audit import PublicKey as AuditKey, scan_keys
from rsa_audit.trees import product_tree, squared_remainders as square_remainders


def arithmetic(backend):
    if backend not in ("python", "gmpy2", "auto"):
        raise ValueError("backend 必须是 python、gmpy2 或 auto")
    if backend != "python":
        try:
            import gmpy2
            return gmpy2.mpz, gmpy2.gcd, "gmpy2/GMP"
        except ImportError:
            if backend == "gmpy2":
                raise ValueError("请安装 gmpy2 或使用 --backend python")
    return int, gcd, "python-int/math.gcd"


def scan(keys, algorithm="batch", backend="python", max_fallback_checks=None):
    selected = "gmpy2" if arithmetic(backend)[2] == "gmpy2/GMP" else "python"
    native = scan_keys([AuditKey(k.id, k.n, k.e) for k in keys], method=algorithm,
                       backend=selected, max_fallback_checks=max_fallback_checks)
    records, groups = [], {}
    for row in native.results:
        members = groups.setdefault(row.n, [])
        status = "unresolved" if row.status == "unresolved_full_overlap" else row.status
        record = {"id": row.id, "n": hex(row.n), "e": hex(row.e), "bits": row.n.bit_length(),
                  "status": status, "factor": hex(row.factor) if row.factor is not None else None,
                  "cofactor": hex(row.cofactor) if row.cofactor is not None else None,
                  "duplicate_of": members[0]["id"] if members else None}
        members.append(record)
        records.append(record)
    unique = []
    for n, members in groups.items():
        row = members[0]
        unique.append({"n": hex(n), "bits": row["bits"], "status": row["status"],
                       "factor": row["factor"], "ids": [r["id"] for r in members]})
    timings = {"preprocess": native.timings["preprocess_seconds"],
               "conversion": native.timings["conversion_seconds"],
               "product_tree": native.timings["product_tree_seconds"],
               "remainder_tree": native.timings["remainder_tree_seconds"],
               "final_gcd": native.timings["gcd_seconds"], "fallback": native.timings["fallback_seconds"],
               "pairwise": native.timings["pairwise_seconds"], "assemble": native.timings["result_seconds"],
               "total": native.timings["total_seconds"]}
    summary = {"record_count": native.summary["record_count"],
               "unique_moduli": native.summary["unique_modulus_count"],
               "duplicate_records": native.summary["duplicate_record_count"],
               "duplicate_groups": native.summary["duplicate_group_count"],
               "factor_found": native.summary["factored_unique_moduli"],
               "unresolved": native.summary["unresolved_unique_moduli"],
               "pairwise_gcd_calls": native.operations["pairwise_gcd_checks"],
               "fallback_candidates": native.summary["batch_full_overlap_count"],
               "fallback_gcd_calls": native.operations["fallback_gcd_checks"]}
    return {"schema_version": 1, "algorithm": algorithm, "backend": arithmetic(selected)[2],
            "engine": "rsa_audit.scan_keys", "summary": summary, "timings_seconds": timings,
            "native_summary": native.summary, "native_operations": native.operations,
            "unique_results": unique, "records": records,
            "duplicates": [{"n": hex(g.n), "ids": list(g.record_ids)} for g in native.duplicate_groups]}

"""Own implementation of pairwise and product/remainder-tree batch GCD.

Algorithm reference: Heninger et al., USENIX Security 2012, section 3.3.
The implementation is for public RSA moduli, normally products of two distinct
primes. It finds divisors, not certificates of primality or complete security.
"""

import math
from time import perf_counter
from typing import Iterable

from .arithmetic import get_arithmetic
from .models import Detection, DuplicateGroup, PublicKey, ScanReport, ScanTimeout, Status
from .trees import product_tree, squared_remainders


def _validate_key(key: PublicKey, index: int) -> None:
    if not isinstance(key, PublicKey):
        raise ValueError(f"record {index}: expected PublicKey")
    if not isinstance(key.id, str) or not key.id.strip():
        raise ValueError(f"record {index}: id must be a nonempty string")
    if type(key.n) is not int or key.n <= 1 or key.n % 2 == 0:
        raise ValueError(f"record {index}: n must be an odd Python integer greater than 1")
    if type(key.e) is not int or key.e < 3 or key.e % 2 == 0:
        raise ValueError(f"record {index}: e must be an odd Python integer at least 3")


def scan_keys(
    keys: Iterable[PublicKey],
    *,
    method: str = "batch",
    backend: str = "python",
    max_fallback_checks: int | None = None,
    timeout_seconds: float | None = None,
) -> ScanReport:
    """Scan only public (id, n, e) records and preserve their original order.

    max_fallback_checks bounds the batch algorithm's additional pairwise GCDs.
    None means exhaustive fallback; 0 leaves full-overlap cases unresolved.
    timeout_seconds is cooperative: an individual big-integer operation cannot
    be interrupted. B should use a subprocess for a strict benchmark deadline.

    total_seconds includes record validation, deduplication, conversion,
    algorithms, fallback and result construction. Backend import/initialization,
    file I/O and JSON serialization are excluded.
    """
    if method not in ("batch", "pairwise"):
        raise ValueError("method must be 'batch' or 'pairwise'")
    if max_fallback_checks is not None and (
        type(max_fallback_checks) is not int or max_fallback_checks < 0
    ):
        raise ValueError("max_fallback_checks must be a nonnegative integer or None")
    if timeout_seconds is not None and (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be finite and positive")
    arithmetic = get_arithmetic(backend)
    start = perf_counter()
    deadline = None if timeout_seconds is None else start + timeout_seconds

    def check(stage: str) -> None:
        if deadline is not None and perf_counter() >= deadline:
            raise ScanTimeout(stage)

    stage_names = (
        "preprocess_seconds", "conversion_seconds", "pairwise_seconds",
        "product_tree_seconds", "remainder_tree_seconds", "gcd_seconds",
        "fallback_seconds", "result_seconds",
    )
    timings = dict.fromkeys(stage_names, 0.0)
    operations = {"pairwise_gcd_checks": 0, "batch_gcd_checks": 0, "fallback_gcd_checks": 0}
    phase_start = perf_counter()
    records = []
    unique_moduli: list[int] = []
    modulus_indices: dict[int, int] = {}
    ids_by_modulus: list[list[str]] = []
    seen_ids: set[str] = set()
    for index, key in enumerate(keys):
        check("preprocess")
        _validate_key(key, index)
        if key.id in seen_ids:
            raise ValueError(f"duplicate record id: {key.id!r}")
        seen_ids.add(key.id)
        records.append(key)
        if key.n not in modulus_indices:
            modulus_indices[key.n] = len(unique_moduli)
            unique_moduli.append(key.n)
            ids_by_modulus.append([])
        ids_by_modulus[modulus_indices[key.n]].append(key.id)
    timings["preprocess_seconds"] = perf_counter() - phase_start

    phase_start = perf_counter()
    numbers = []
    for n in unique_moduli:
        check("conversion")
        numbers.append(arithmetic.integer(n))
    timings["conversion_seconds"] = perf_counter() - phase_start
    factors: dict[int, int] = {}
    full_overlap: list[int] = []
    fallback_limit_reached = False

    def save_factor(index: int, divisor: int) -> None:
        n = unique_moduli[index]
        # A divisor is always checked before it is allowed into the output.
        if not 1 < divisor < n or n % divisor:
            raise ArithmeticError("algorithm returned an invalid nontrivial divisor")
        factors.setdefault(index, min(divisor, n // divisor))

    if method == "pairwise":
        phase_start = perf_counter()
        full_overlap_indices: set[int] = set()
        for i in range(len(numbers)):
            for j in range(i + 1, len(numbers)):
                check("pairwise")
                g = int(arithmetic.gcd(numbers[i], numbers[j]))
                operations["pairwise_gcd_checks"] += 1
                if g == 1:
                    continue
                for index in (i, j):
                    if g < unique_moduli[index]:
                        save_factor(index, g)
                    else:
                        # Possible for malformed/non-semiprime public inputs.
                        full_overlap_indices.add(index)
        full_overlap = sorted(full_overlap_indices)
        timings["pairwise_seconds"] = perf_counter() - phase_start
    else:
        phase_start = perf_counter()
        tree = product_tree(numbers, check)
        timings["product_tree_seconds"] = perf_counter() - phase_start
        phase_start = perf_counter()
        remainders = squared_remainders(tree, check)
        timings["remainder_tree_seconds"] = perf_counter() - phase_start
        phase_start = perf_counter()
        for index, (n, remainder) in enumerate(zip(numbers, remainders)):
            check("gcd")
            quotient, residual = divmod(remainder, n)
            if residual != 0:
                raise ArithmeticError("remainder-tree invariant violated: n must divide remainder")
            g = int(arithmetic.gcd(n, quotient))
            operations["batch_gcd_checks"] += 1
            if g == unique_moduli[index]:
                full_overlap.append(index)
            elif g > 1:
                save_factor(index, g)
        timings["gcd_seconds"] = perf_counter() - phase_start

        phase_start = perf_counter()
        for index in full_overlap:
            for other in range(len(numbers)):
                if index == other:
                    continue
                check("fallback")
                if (max_fallback_checks is not None
                        and operations["fallback_gcd_checks"] >= max_fallback_checks):
                    fallback_limit_reached = True
                    break
                g = int(arithmetic.gcd(numbers[index], numbers[other]))
                operations["fallback_gcd_checks"] += 1
                if 1 < g < unique_moduli[index]:
                    save_factor(index, g)
                    break
            if fallback_limit_reached:
                break
        timings["fallback_seconds"] = perf_counter() - phase_start

    phase_start = perf_counter()
    unresolved = set(full_overlap) - factors.keys()
    results = []
    for record in records:
        check("results")
        index = modulus_indices[record.n]
        factor = factors.get(index)
        status: Status = (
            "factor_found" if factor is not None
            else "unresolved_full_overlap" if index in unresolved
            else "no_shared_factor"
        )
        results.append(Detection(
            id=record.id, n=record.n, e=record.e, modulus_index=index,
            status=status, factor=factor,
            cofactor=record.n // factor if factor is not None else None,
            duplicate_count=len(ids_by_modulus[index]) - 1,
        ))
    duplicate_groups = []
    for index, ids in enumerate(ids_by_modulus):
        check("results")
        if len(ids) > 1:
            duplicate_groups.append(DuplicateGroup(index, unique_moduli[index], tuple(ids)))
    summary = {
        "record_count": len(records),
        "unique_modulus_count": len(numbers),
        "duplicate_record_count": len(records) - len(numbers),
        "duplicate_group_count": len(duplicate_groups),
        "factored_unique_moduli": len(factors),
        "factored_records": sum(len(ids_by_modulus[index]) for index in factors),
        "no_shared_factor_unique_moduli": len(numbers) - len(factors) - len(unresolved),
        "unresolved_unique_moduli": len(unresolved),
        "batch_full_overlap_count": len(full_overlap) if method == "batch" else 0,
        "fallback_limit_reached": fallback_limit_reached,
    }
    report_results = tuple(results)
    report_groups = tuple(duplicate_groups)
    check("results")
    timings["result_seconds"] = perf_counter() - phase_start
    timings["total_seconds"] = perf_counter() - start
    return ScanReport(method, backend, report_results, report_groups, summary, timings, operations)

"""B: independent checks AFTER the scanner/recovery process has finished."""

from .models import from_hex, read_json, read_public, sha256_file


def evaluate(public_path, ground_truth_path, detection, recovery=None):
    keys = read_public(public_path)
    truth = read_json(ground_truth_path)
    if truth["public_sha256"] != sha256_file(public_path):
        raise ValueError("真值摘要与公钥文件不匹配")
    by_id = {r["id"]: r for r in truth["records"]}
    if set(by_id) != {k.id for k in keys} or len(by_id) != len(truth["records"]):
        raise ValueError("真值记录与公钥不匹配")
    for key in keys:
        row = by_id[key.id]
        if from_hex(row["n"]) != key.n or from_hex(row["e"]) != key.e:
            raise ValueError("真值公钥参数不匹配")
    actual = {}
    owners = {}
    for row in by_id.values():
        n, p, q = (from_hex(row[name]) for name in ("n", "p", "q"))
        if p * q != n or p == q:
            raise ValueError("真值不是两个不同因子的正确分解")
        actual[n] = {p, q}
        for factor in (p, q):
            owners.setdefault(factor, set()).add(n)
    # 从实际因子关系推导预期，不信任 normal/weak 标签。
    expected = {n for n, factors in actual.items() if any(len(owners[p]) > 1 for p in factors)}
    results = detection["unique_results"]
    if {from_hex(r["n"]) for r in results} != set(actual) or len(results) != len(actual):
        raise ValueError("检测结果不同模数集合不匹配")
    found = {from_hex(r["n"]) for r in results if r["status"] == "factor_found"}
    correct = {from_hex(r["n"]) for r in results if r["status"] == "factor_found"
               and from_hex(r["factor"]) in actual[from_hex(r["n"]) ]}
    verified_ids = []
    invalid_decryptions = []
    if recovery is not None:
        seen = set()
        for row in recovery["records"]:
            if row["id"] not in by_id or row["id"] in seen:
                raise ValueError("恢复记录 id 无效或重复")
            seen.add(row["id"])
            if row["status"] == "decrypted":
                if row["plaintext_b64"] == by_id[row["id"]]["message_b64"]:
                    verified_ids.append(row["id"])
                else:
                    invalid_decryptions.append(row["id"])
    decrypted_moduli = {from_hex(by_id[key_id]["n"]) for key_id in verified_ids}
    return {"expected_recoverable_moduli": len(expected), "correctly_factored_moduli": len(correct & expected),
            "false_positives": len(found - expected), "false_negatives": len(expected - correct),
            "invalid_factors": len(found - correct), "verified_decryption_records": len(verified_ids),
            "verified_decryption_moduli": len(decrypted_moduli), "invalid_decryptions": invalid_decryptions,
            "duplicate_records": len(keys) - len(actual),
            "passed": found == expected and correct == expected and not invalid_decryptions
                      and (recovery is None or decrypted_moduli == expected)}

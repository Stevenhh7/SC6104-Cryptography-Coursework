"""B: controlled shared-prime models and separate, verified ground truth."""

from collections import defaultdict
from pathlib import Path
from time import perf_counter
import base64
import math
import random
from cryptography.hazmat.primitives.asymmetric import rsa
from .crypto import decrypt_message, encrypt_message, recover_private_key
from .models import PublicKey, from_hex, read_json, read_public, sha256_file, write_json, write_public


class PrimeSource:
    """Use OpenSSL's CSPRNG and primality routines, not a Python seeded RNG."""

    def __init__(self, bits=2048):
        if bits < 1024 or bits % 2:
            raise ValueError("bits 必须是 >= 1024 的偶数；最终演示采用 2048")
        self.bits = bits
        self.pending = []
        self.used = set()

    def next(self):
        while True:
            if not self.pending:
                key = rsa.generate_private_key(public_exponent=65537, key_size=self.bits)
                numbers = key.private_numbers()
                self.pending.extend((numbers.p, numbers.q))
            p = self.pending.pop()
            if p not in self.used and p.bit_length() == self.bits // 2:
                self.used.add(p)
                return p

    def pair(self, p=None):
        if p is None:
            p = self.next()
        while True:
            q = self.next()
            if p != q and (p * q).bit_length() == self.bits:
                return p, q


def secret_record(key_id, p, q, source, e=65537):
    n = p * q
    if p == q or math.gcd(e, math.lcm(p - 1, q - 1)) != 1:
        raise ValueError("生成了无效的 RSA 参数")
    return {"id": key_id, "n": hex(n), "e": hex(e), "p": hex(p), "q": hex(q), "source": source}


def create_records(count=100, bits=2048, mode="demo", weak_fraction=0.05, pool_size=16, seed=104):
    if count < 0 or not 0 <= weak_fraction <= 1:
        raise ValueError("count 必须非负，weak_fraction 必须在 [0,1]")
    if mode not in ("demo", "pairs", "normal", "pool"):
        raise ValueError("不支持的数据模型")
    if mode == "demo" and count < 5:
        raise ValueError("demo 至少需要 5 个不同模数")
    primes = PrimeSource(bits)
    records = []

    def add(p, q, source):
        records.append(secret_record(f"key-{len(records):05d}", p, q, source))

    if mode == "demo":
        # 一对共享因子 + 三角结构，后者必然触发 batch 的 g_i=n_i 回退。
        p, q = primes.pair()
        add(p, q, "shared_pair")
        add(*primes.pair(p), "shared_pair")
        a, b = primes.pair()
        c = primes.next()
        while (a * c).bit_length() != bits or (b * c).bit_length() != bits:
            c = primes.next()
        add(a, b, "triangle")
        add(a, c, "triangle")
        add(b, c, "triangle")
        while len(records) < count:
            add(*primes.pair(), "normal")
    elif mode == "pool":
        if pool_size < 1:
            raise ValueError("pool_size 必须为正")
        pool = [primes.next() for _ in range(pool_size)]
        layout_rng = random.Random(seed)  # 仅控制选哪个池槽位，不生成素数。
        for _ in range(count):
            add(*primes.pair(pool[layout_rng.randrange(pool_size)]), "weak_pool")
    else:
        # 每 interval 个模数放一对共享因子，前缀也保持接近目标比例。
        interval = max(2, round(2 / weak_fraction)) if weak_fraction else count + 1
        while len(records) < count:
            if mode == "pairs" and weak_fraction and len(records) % interval == 0 and len(records) + 1 < count:
                p, q = primes.pair()
                add(p, q, "shared_pair")
                add(*primes.pair(p), "shared_pair")
            else:
                add(*primes.pair(), "normal")
    if mode == "demo":
        for index in (0, count - 1):
            records.append({**records[index], "id": f"duplicate-{index:05d}", "source": "duplicate"})
    return records


def actual_truth(records):
    unique = {}
    for row in records:
        n, p, q = (from_hex(row[name]) for name in ("n", "p", "q"))
        if p * q != n or p == q:
            raise ValueError("真值因子无效")
        pair = tuple(sorted((p, q)))
        if n in unique and unique[n] != pair:
            raise ValueError("同一个模数的真值不一致")
        unique[n] = pair
    owners = defaultdict(set)
    for n, pair in unique.items():
        for p in pair:
            owners[p].add(n)
    vulnerable = {n for n, pair in unique.items() if any(len(owners[p]) > 1 for p in pair)}
    for row in records:
        row["expected_shared_factor"] = from_hex(row["n"]) in vulnerable
    return vulnerable


def save_dataset(path, records, config, generation_seconds=0.0, force=False):
    path = Path(path)
    if (path / "public_keys.jsonl").exists() and not force:
        raise ValueError("数据集已存在；要覆盖请显式使用 --force")
    path.mkdir(parents=True, exist_ok=True)
    vulnerable = actual_truth(records)
    keys = [PublicKey(r["id"], from_hex(r["n"]), from_hex(r["e"])) for r in records]
    public_path = path / "public_keys.jsonl"
    write_public(public_path, keys)
    ciphertexts = []
    # 所有记录都保存密文，正常组也能用于验证“没有私钥时不能解密”的输出。
    for row, key in zip(records, keys):
        message = ("RSA shared prime lab | " + key.id).encode("utf-8")
        row["message_b64"] = base64.b64encode(message).decode("ascii")
        ciphertexts.append(encrypt_message(key, message))
    write_json(path / "ciphertexts.json", ciphertexts)
    write_json(path / "ground_truth.json", {"schema_version": 1, "public_sha256": sha256_file(public_path), "records": records})
    distinct = len({k.n for k in keys})
    manifest = {"schema_version": 1, "config": config, "record_count": len(keys), "unique_moduli": distinct,
                "actual_vulnerable_moduli": len(vulnerable),
                "actual_weak_fraction": len(vulnerable) / distinct if distinct else 0,
                "generation_seconds": generation_seconds, "public_sha256": sha256_file(public_path),
                "ciphertexts_sha256": sha256_file(path / "ciphertexts.json"),
                "randomness": "OpenSSL CSPRNG; seed controls pool choices only; replay saved data"}
    write_json(path / "manifest.json", manifest)
    return manifest


def generate_dataset(path, **options):
    force = options.pop("force", False)
    if (Path(path) / "public_keys.jsonl").exists() and not force:
        raise ValueError("数据集已存在；要覆盖请显式使用 --force")
    start = perf_counter()
    records = create_records(**options)
    return save_dataset(path, records, options, perf_counter() - start, force)


def prepare_benchmarks(root, sizes, bits=2048, fraction=0.05):
    root = Path(root)
    if not sizes or min(sizes) < 1:
        raise ValueError("性能实验规模必须为正")
    largest = max(sizes)
    corpus = root / "corpus"
    if not (corpus / "public_keys.jsonl").exists():
        print(f"生成 {largest} 个 {bits}-bit 不同模数，生成耗时单独记录…", flush=True)
        generate_dataset(corpus, count=largest, bits=bits, mode="pairs", weak_fraction=fraction)
    manifest = read_json(corpus / "manifest.json")
    if manifest["config"]["bits"] != bits or manifest["unique_moduli"] < largest or manifest["config"]["weak_fraction"] != fraction:
        raise ValueError("已有 corpus 与要求不一致，请使用另一个 data-root")
    rows = read_json(corpus / "ground_truth.json")["records"]
    for size in sorted(set(sizes)):
        destination = root / f"n-{size}"
        if not (destination / "public_keys.jsonl").exists():
            config = {"count": size, "bits": bits, "mode": "pairs", "weak_fraction": fraction,
                      "source_corpus": "../corpus", "source_generation_seconds": manifest["generation_seconds"]}
            subset = [dict(row) for row in rows[:size]]
            save_dataset(destination, subset, config)
        print(f"实验数据已准备: n={size}", flush=True)


def repair_public(keys, detection, output):
    """Replace affected moduli; no original secrets or ground truth are read."""
    output = Path(output)
    if (output / "public_keys.jsonl").exists():
        raise ValueError("修复输出目录已有数据，请指定新的输出目录")
    rows = {r["id"]: r for r in detection["records"]}
    if len(rows) != len(detection["records"]) or set(rows) != {k.id for k in keys}:
        raise ValueError("修复检测结果与输入不一致")
    affected = set()
    exponents = defaultdict(set)
    for key in keys:
        row = rows[key.id]
        if from_hex(row["n"]) != key.n or from_hex(row["e"]) != key.e:
            raise ValueError("修复检测结果与公钥不一致")
        exponents[key.n].add(key.e)
        if row["status"] in ("factor_found", "unresolved"):
            affected.add(key.n)
    existing = {k.n for k in keys}
    replacements = {}
    new_secrets = []
    for n in sorted(affected):
        primes = PrimeSource(n.bit_length())
        while True:
            p, q = primes.pair()
            new_n = p * q
            if new_n not in existing and all(math.gcd(e, math.lcm(p - 1, q - 1)) == 1 for e in exponents[n]):
                replacements[n] = (p, q)
                existing.add(new_n)
                break
    repaired = []
    ciphertexts = []
    for key in keys:
        if key.n in replacements:
            p, q = replacements[key.n]
            fresh = PublicKey(key.id, p * q, key.e)
            secret = secret_record(key.id, p, q, "regenerated", key.e)
            secret["old_n"] = hex(key.n)
            new_secrets.append(secret)
            message = b"Fresh RSA key after repair"
            cipher = encrypt_message(fresh, message)
            private = recover_private_key(fresh.n, fresh.e, p)
            if decrypt_message(private, cipher) != message:
                raise ArithmeticError("新密钥 OAEP 加解密验证失败")
            ciphertexts.append(cipher)
            repaired.append(fresh)
        else:
            repaired.append(key)
    write_public(output / "public_keys.jsonl", repaired)
    write_json(output / "ciphertexts.json", ciphertexts)
    write_json(output / "new_private_parameters.json", new_secrets)
    info = {"replaced_unique_moduli": len(replacements), "affected_records": len(new_secrets),
            "new_key_roundtrip_records": len(ciphertexts),
            "note": "Only current shared-factor relationships tested; duplicate record mappings preserved"}
    write_json(output / "repair_summary.json", info)
    return info

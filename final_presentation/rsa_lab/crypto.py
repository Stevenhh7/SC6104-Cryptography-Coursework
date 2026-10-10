"""B: reconstruct an RSA private key from a discovered proper prime factor."""

import base64
from math import gcd, lcm
from pathlib import Path
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Util.number import isPrime
from .models import from_hex


def recover_private_key(n, e, factor):
    if type(factor) is not int or not 1 < factor < n or n % factor:
        raise ValueError("因子必须是 n 的非平凡整除因子")
    p = factor
    q = n // p
    if p == q or not isPrime(p) or not isPrime(q):
        raise ValueError("本项目要求 n 是两个不同素数的乘积")

    # B 核心步骤：两个素数已知，就能求模逆恢复私钥指数。
    lambda_n = lcm(p - 1, q - 1)
    if gcd(e, lambda_n) != 1:
        raise ValueError("公钥指数与 lambda(n) 不互素，无法恢复有效 RSA 私钥")
    d = pow(e, -1, lambda_n)
    key = RSA.construct((n, e, d, p, q), consistency_check=True)
    if key.n != p * q or (e * d) % lambda_n != 1:
        raise ArithmeticError("恢复的密钥没有通过一致性检查")
    return key


def oaep_cipher(key, label=b""):
    # 显式固定摘要与 MGF1 的摘要，避免两端默认参数不同。
    return PKCS1_OAEP.new(key, hashAlgo=SHA256,
                         mgfunc=lambda seed, size: PKCS1_OAEP.MGF1(seed, size, SHA256), label=label)


def encrypt_message(public, message, label=b""):
    key = RSA.construct((public.n, public.e))
    ciphertext = oaep_cipher(key, label).encrypt(message)
    return {"id": public.id, "scheme": "RSAES-OAEP", "hash": "SHA-256",
            "mgf": "MGF1-SHA-256", "label_b64": base64.b64encode(label).decode("ascii"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii")}


def decrypt_message(private, row):
    if (row.get("scheme"), row.get("hash"), row.get("mgf")) != ("RSAES-OAEP", "SHA-256", "MGF1-SHA-256"):
        raise ValueError("只支持 RSAES-OAEP / SHA-256 / MGF1-SHA-256")
    label = base64.b64decode(row["label_b64"], validate=True)
    ciphertext = base64.b64decode(row["ciphertext_b64"], validate=True)
    if len(ciphertext) != private.size_in_bytes():
        raise ValueError("密文长度与模数长度不一致")
    return oaep_cipher(private, label).decrypt(ciphertext)


def recover_messages(keys, detection, ciphertexts, private_dir=None):
    """Only public keys, detection output and ciphertexts enter this function."""
    by_id = {k.id: k for k in keys}
    detected = {row["id"]: row for row in detection["records"]}
    if len(detected) != len(detection["records"]) or set(detected) != set(by_id):
        raise ValueError("检测结果记录与公开输入不一致")
    for key in keys:
        row = detected[key.id]
        if from_hex(row["n"]) != key.n or from_hex(row["e"]) != key.e:
            raise ValueError("检测结果的模数或指数与公开输入不一致")
    if private_dir is not None:
        Path(private_dir).mkdir(parents=True, exist_ok=True)
    output = []
    cache = {}
    cipher_ids = set()
    for cipher in ciphertexts:
        key_id = cipher.get("id")
        if key_id in cipher_ids:
            raise ValueError("每条公钥记录只能对应一条实验密文")
        cipher_ids.add(key_id)
        row = {"id": key_id}
        if key_id not in by_id:
            output.append({**row, "status": "unknown_key"})
            continue
        if detected[key_id]["status"] != "factor_found":
            output.append({**row, "status": "not_factorable"})
            continue
        public = by_id[key_id]
        try:
            cache_key = (public.n, public.e)
            if cache_key not in cache:
                cache[cache_key] = recover_private_key(public.n, public.e, from_hex(detected[key_id]["factor"]))
            private = cache[cache_key]
        except (ValueError, TypeError, KeyError) as error:
            output.append({**row, "status": "invalid_factor", "error": str(error)})
            continue
        try:
            plaintext = decrypt_message(private, cipher)
        except (ValueError, TypeError, KeyError) as error:
            output.append({**row, "status": "invalid_ciphertext", "error": str(error)})
            continue
        try:
            text = plaintext.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        if private_dir is not None:
            # 用序号命名，不能把外部 id 直接拼成文件路径。
            filename = f"recovered-{len(output):05d}.pem"
            (Path(private_dir) / filename).write_bytes(private.export_key(format="PEM"))
            row["private_pem"] = filename
        output.append({**row, "status": "decrypted", "plaintext_utf8": text,
                       "plaintext_b64": base64.b64encode(plaintext).decode("ascii")})
    return {"schema_version": 1, "decrypted_records": sum(r["status"] == "decrypted" for r in output),
            "records": output}

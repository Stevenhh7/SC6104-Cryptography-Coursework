"""Public input schema. No private-key or ground-truth imports here."""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re


def from_hex(value):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", value):
        raise ValueError("大整数必须是带 0x 前缀的十六进制字符串")
    return int(value, 16)


def exponent(value):
    return value if type(value) is int else from_hex(value)


@dataclass(frozen=True)
class PublicKey:
    id: str
    n: int
    e: int = 65537

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("公钥 id 不能为空")
        if type(self.n) is not int or self.n <= 1 or self.n % 2 == 0:
            raise ValueError("RSA 模数必须是大于 1 的奇整数")
        if type(self.e) is not int or self.e < 3 or self.e % 2 == 0:
            raise ValueError("公钥指数必须是 >= 3 的奇整数")

    def to_dict(self):
        return {"id": self.id, "n": hex(self.n), "e": self.e}

    @classmethod
    def from_dict(cls, row):
        if set(row) != {"id", "n", "e"}:
            raise ValueError("公开输入每行只能包含 id、n、e，不能包含秘密参数")
        return cls(row["id"], from_hex(row["n"]), exponent(row["e"]))


def read_public(path):
    keys = []
    seen_ids = set()
    with Path(path).open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                key = PublicKey.from_dict(json.loads(line))
                if key.id in seen_ids:
                    raise ValueError("公钥 id 重复: " + key.id)
                keys.append(key)
                seen_ids.add(key.id)
            except (ValueError, TypeError, KeyError) as error:
                raise ValueError(f"公开输入第 {line_number} 行: {error}") from error
    return keys


def write_public(path, keys):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(k.to_dict()) + "\n" for k in keys), encoding="utf-8", newline="\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

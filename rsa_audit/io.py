"""Strict public-only JSONL reader and atomic report writer."""

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

from .models import PublicKey, ScanReport


def _modulus(value: object) -> int:
    if type(value) is not str:
        raise ValueError("n must be a hexadecimal string (prefer the 0x prefix)")
    digits = value[2:] if value.startswith(("0x", "0X")) else value
    if not digits or any(ch not in "0123456789abcdefABCDEF" for ch in digits):
        raise ValueError("n must be a hexadecimal string (prefer the 0x prefix)")
    return int(digits, 16)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def load_public_keys(path: str | Path) -> list[PublicKey]:
    """Read {id, n, e} records; reject truth/private fields rather than use them."""
    records = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line, object_pairs_hook=_unique_object)
                if not isinstance(raw, dict) or set(raw) != {"id", "n", "e"}:
                    raise ValueError("each line must contain exactly the public fields id, n, e")
                records.append(PublicKey(id=raw["id"], n=_modulus(raw["n"]), e=raw["e"]))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"line {line_number}: {exc}") from exc
    return records


def _atomic_text(path: str | Path, content: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=destination.parent,
            prefix=f".{destination.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_report(path: str | Path, report: ScanReport) -> None:
    _atomic_text(path, json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n")


def write_public_keys(path: str | Path, keys: Iterable[PublicKey]) -> None:
    """A convenience exporter for B's generator; excludes all private fields."""
    text = "".join(json.dumps({"id": key.id, "n": hex(key.n), "e": key.e},
                              ensure_ascii=False) + "\n" for key in keys)
    _atomic_text(path, text)

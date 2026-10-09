"""Public inputs and JSON-serializable scan results. No private-key fields."""

from dataclasses import asdict, dataclass
from typing import Any, Literal

Status = Literal["factor_found", "no_shared_factor", "unresolved_full_overlap"]


class ScanTimeout(TimeoutError):
    """A cooperative scan deadline expired; there is no complete result."""

    def __init__(self, stage: str):
        self.stage = stage
        super().__init__(f"scan deadline exceeded during {stage}")


@dataclass(frozen=True)
class PublicKey:
    id: str
    n: int
    e: int = 65537


@dataclass(frozen=True)
class Detection:
    id: str
    n: int
    e: int
    modulus_index: int
    status: Status
    factor: int | None
    cofactor: int | None
    duplicate_count: int

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for name in ("n", "factor", "cofactor"):
            value = result[name]
            result[name] = hex(value) if value is not None else None
        return result


@dataclass(frozen=True)
class DuplicateGroup:
    modulus_index: int
    n: int
    record_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "modulus_index": self.modulus_index,
            "n": hex(self.n),
            "record_ids": list(self.record_ids),
        }


@dataclass(frozen=True)
class ScanReport:
    method: str
    backend: str
    results: tuple[Detection, ...]
    duplicate_groups: tuple[DuplicateGroup, ...]
    summary: dict[str, int | bool]
    timings: dict[str, float]
    operations: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "method": self.method,
            "backend": self.backend,
            "summary": dict(self.summary),
            "timings": dict(self.timings),
            "operations": dict(self.operations),
            "duplicate_groups": [group.to_dict() for group in self.duplicate_groups],
            "results": [row.to_dict() for row in self.results],
        }

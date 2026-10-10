"""Select one arithmetic backend for every stage of either algorithm."""

from dataclasses import dataclass
from math import gcd
from typing import Any, Callable


@dataclass(frozen=True)
class Arithmetic:
    name: str
    integer: Callable[[int], Any]
    gcd: Callable[[Any, Any], Any]


def get_arithmetic(name: str) -> Arithmetic:
    if name == "python":
        return Arithmetic("python", int, gcd)
    if name == "gmpy2":
        try:
            import gmpy2
        except ImportError as exc:
            raise ValueError(
                "gmpy2 is not installed; use backend='python' or install the fast extra"
            ) from exc
        return Arithmetic("gmpy2", gmpy2.mpz, gmpy2.gcd)
    raise ValueError("backend must be 'python' or 'gmpy2'")

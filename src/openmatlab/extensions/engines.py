"""SemVer range checks for ``engines.openmatlab`` (contract subset)."""

from __future__ import annotations

import re
from typing import List, Tuple

_OP_RE = re.compile(r"^(>=|<=|>|<|==|=)?\s*(\d+(?:\.\d+){0,2})$")


class EngineRangeError(ValueError):
    """Manifest engine range is invalid or incompatible with the host."""


def _parse_version(ver_s: str) -> Tuple[int, ...]:
    parts = ver_s.split(".")
    try:
        nums = tuple(int(p) for p in parts)
    except ValueError as exc:
        raise EngineRangeError(f"invalid version {ver_s!r}") from exc
    # Normalize to 3-tuple for comparison
    if len(nums) < 3:
        nums = nums + (0,) * (3 - len(nums))
    return nums[:3]


def _parse_clause(clause: str) -> Tuple[str, Tuple[int, ...]]:
    raw = clause.strip()
    if not raw:
        raise EngineRangeError("empty engine range clause")
    m = _OP_RE.match(raw)
    if not m:
        raise EngineRangeError(f"unsupported engine range clause: {clause!r}")
    op, ver_s = m.group(1) or "=", m.group(2)
    if op == "==":
        op = "="
    return op, _parse_version(ver_s)


def parse_range(spec: str) -> List[Tuple[str, Tuple[int, ...]]]:
    """Parse space-separated AND range (``>=0.1.0 <0.2.0``)."""
    if not isinstance(spec, str) or not spec.strip():
        raise EngineRangeError("engines.openmatlab must be a non-empty string")
    return [_parse_clause(p) for p in spec.split()]


def satisfies(spec: str, host_version: str) -> bool:
    """Return True if ``host_version`` satisfies the npm-style subset range."""
    try:
        host = _parse_version(host_version)
    except EngineRangeError:
        raise
    for op, ver in parse_range(spec):
        if op == ">=" and not (host >= ver):
            return False
        if op == "<=" and not (host <= ver):
            return False
        if op == ">" and not (host > ver):
            return False
        if op == "<" and not (host < ver):
            return False
        if op == "=" and not (host == ver):
            return False
    return True


def check_compatible(spec: str, host_version: str) -> None:
    """Raise ``EngineRangeError`` if incompatible."""
    if not satisfies(spec, host_version):
        raise EngineRangeError(
            f"plugin requires openmatlab {spec!r}; host api_version is {host_version}"
        )

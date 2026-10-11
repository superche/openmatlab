"""NumPy-backed ArrayBackend placeholder — not wired at architecture stage."""

from __future__ import annotations

from typing import Any, Sequence, Tuple

from openmatlab.runtime.value import Array


class NumPyArrayBackend:
    """Stub: import numpy only when implemented; methods raise for now."""

    def zeros(self, shape: Tuple[int, ...]) -> Array:
        raise NotImplementedError("NumPyArrayBackend.zeros: architecture stub")

    def ones(self, shape: Tuple[int, ...]) -> Array:
        raise NotImplementedError("NumPyArrayBackend.ones: architecture stub")

    def eye(self, n: int) -> Array:
        raise NotImplementedError("NumPyArrayBackend.eye: architecture stub")

    def from_nested(self, rows: Sequence[Sequence[float]]) -> Array:
        raise NotImplementedError("NumPyArrayBackend.from_nested: architecture stub")

    def matmul(self, a: Array, b: Array) -> Array:
        raise NotImplementedError("NumPyArrayBackend.matmul: architecture stub")

    def elem_mul(self, a: Array, b: Array) -> Array:
        raise NotImplementedError("NumPyArrayBackend.elem_mul: architecture stub")

    def elem_div(self, a: Array, b: Array) -> Array:
        raise NotImplementedError("NumPyArrayBackend.elem_div: architecture stub")

    def add(self, a: Array, b: Array) -> Array:
        raise NotImplementedError("NumPyArrayBackend.add: architecture stub")

    def sub(self, a: Array, b: Array) -> Array:
        raise NotImplementedError("NumPyArrayBackend.sub: architecture stub")

    def transpose(self, a: Array, *, conjugate: bool = True) -> Array:
        raise NotImplementedError("NumPyArrayBackend.transpose: architecture stub")

    def raw(self, a: Array) -> Any:
        raise NotImplementedError("NumPyArrayBackend.raw: architecture stub")

"""Array-first value model.

MATLAB-like semantics treat numerics as arrays; a scalar is a 1×1 array.
Do NOT reintroduce dict[str, float] as the primary eval result type.

Concrete arrays live in openmatlab.numerics (e.g. NDArrayValue) so runtime
stays free of a hard NumPy dependency (KISS / low coupling).
"""

from __future__ import annotations

from typing import Any, Protocol, Tuple, runtime_checkable


class _CachedProtocolMeta(type(Protocol)):
    """Protocol metaclass whose isinstance() remembers *positive* answers per concrete type (#797).

    A type is cached only when every protocol member is found on the type itself and the type
    has no ``__getattr__``/``__getattribute__`` override, so the cached answer is exactly what
    the structural check would return. Everything else takes the normal (slow) check."""

    def __instancecheck__(cls, instance):
        t = type(instance)
        cache = _POS.get(cls)
        if cache is not None and t in cache:
            return True
        ok = super().__instancecheck__(instance)
        if ok and cache is not None and "__getattr__" not in dir(t) and t.__getattribute__ is object.__getattribute__ \
                and all(hasattr(t, m) for m in _MEMBERS[cls]):
            cache.add(t)
        return ok


_MEMBERS: dict = {}
_POS: dict = {}  # kept off the class: Protocol would count class attributes as members


def _cached(proto):
    members = set()
    for base in proto.__mro__:
        if base in (object, Protocol) or base.__name__ == "Generic":
            continue
        members |= {k for k in vars(base) if not k.startswith("_")}
    _MEMBERS[proto] = frozenset(members)
    _POS[proto] = set()
    return proto


@_cached
@runtime_checkable
class Value(Protocol, metaclass=_CachedProtocolMeta):
    """Opaque runtime value (arrays, future char/logical/cell/handle)."""

    def matlab_class(self) -> str:
        """Public-doc style class name, e.g. 'double', 'char'."""
        ...


@_cached
@runtime_checkable
class Array(Value, Protocol, metaclass=_CachedProtocolMeta):
    """Numeric (or logical) N-D array — the default MATLAB-like value."""

    @property
    def shape(self) -> Tuple[int, ...]:
        ...

    @property
    def ndim(self) -> int:
        ...

    def is_scalar(self) -> bool:
        """True iff numel == 1 (scalar-as-1x1)."""
        ...

    def numel(self) -> int:
        ...

    def backend_buffer(self) -> Any:
        """Escape hatch to ArrayBackend storage (e.g. numpy.ndarray)."""
        ...

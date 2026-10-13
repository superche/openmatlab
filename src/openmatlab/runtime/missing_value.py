"""MATLAB ``missing`` (#504): a 1x1 value of class ``missing`` that converts by context.
It becomes NaN among numbers and <missing> among strings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MissingValue:
    is_missing_value = True
    shape = (1, 1)
    ndim = 2

    def matlab_class(self) -> str:
        return "missing"

    def numel(self) -> int:
        return 1

    def is_scalar(self) -> bool:
        return True


def is_missing(v) -> bool:
    return bool(getattr(v, "is_missing_value", False))


def as_nan():
    import numpy as np

    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.array([[np.nan]]))


def as_string():
    import numpy as np

    from openmatlab.runtime.string_array import StringArray

    return StringArray(np.array([[None]], dtype=object))


def resolve(values, *, stringy: bool):
    """Replace missing values in a concatenation: <missing> next to strings, otherwise NaN."""
    return [(as_string() if stringy else as_nan()) if is_missing(v) else v for v in values]

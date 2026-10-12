"""Concrete Array value backed by numpy.ndarray (optional dependency)."""

from __future__ import annotations

from typing import Any, Tuple

import numpy as np


class NDArrayValue:
    """LSP-friendly Array: exposes Protocol surface over an ndarray buffer."""

    __slots__ = ("_data",)

    def __init__(self, data: np.ndarray) -> None:
        if not isinstance(data, np.ndarray):
            raise TypeError("NDArrayValue requires numpy.ndarray")
        # MATLAB drops trailing singleton dims beyond the 2nd (size(zeros(2,3,1))=[2 3]).
        if data.ndim > 2 and data.shape[-1] == 1:
            shape = list(data.shape)
            while len(shape) > 2 and shape[-1] == 1:
                shape.pop()
            data = data.reshape(shape)
        self._data = data

    def matlab_class(self) -> str:
        if self._data.dtype == np.bool_ or np.issubdtype(self._data.dtype, np.bool_):
            return "logical"
        if np.issubdtype(self._data.dtype, np.integer):
            from openmatlab.numerics.intclass import class_name

            return class_name(self._data.dtype) or "double"
        return "double"

    @property
    def shape(self) -> Tuple[int, ...]:
        return tuple(int(x) for x in self._data.shape)

    @property
    def ndim(self) -> int:
        return int(self._data.ndim)

    def numel(self) -> int:
        return int(self._data.size)

    def is_scalar(self) -> bool:
        return self.numel() == 1

    def backend_buffer(self) -> np.ndarray:
        return self._data

    def __repr__(self) -> str:
        return f"NDArrayValue(shape={self.shape})"

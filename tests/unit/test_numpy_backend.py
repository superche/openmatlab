"""Unit tests for NDArrayValue + NumPyArrayBackend (Issue #2)."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from openmatlab.numerics import NDArrayValue, NumericsError, NumPyArrayBackend
from openmatlab.runtime.value import Array

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def be() -> NumPyArrayBackend:
    return NumPyArrayBackend()


def test_ndarray_value_satisfies_array_protocol(be: NumPyArrayBackend):
    a = be.zeros((2, 3))
    assert isinstance(a, Array)
    assert isinstance(a, NDArrayValue)
    assert a.shape == (2, 3)
    assert a.ndim == 2
    assert a.numel() == 6
    assert a.matlab_class() == "double"
    assert a.is_scalar() is False


def test_scalar_is_1x1(be: NumPyArrayBackend):
    s = be.from_scalar(3.5)
    assert s.shape == (1, 1)
    assert s.is_scalar() is True
    assert s.numel() == 1
    assert float(s.backend_buffer()[0, 0]) == 3.5


def test_ones_eye_from_nested(be: NumPyArrayBackend):
    assert be.ones((2, 2)).shape == (2, 2)
    eye = be.eye(3)
    assert eye.shape == (3, 3)
    import numpy as np

    assert np.allclose(eye.backend_buffer(), np.eye(3))
    m = be.from_nested([[1.0, 2.0], [3.0, 4.0]])
    assert m.shape == (2, 2)
    assert float(m.backend_buffer()[1, 0]) == 3.0


def test_ragged_from_nested_raises(be: NumPyArrayBackend):
    with pytest.raises(NumericsError):
        be.from_nested([[1.0, 2.0], [3.0]])


def test_matmul_and_elem_mul(be: NumPyArrayBackend):
    a = be.from_nested([[1.0, 2.0], [3.0, 4.0]])
    b = be.from_nested([[1.0, 0.0], [0.0, 1.0]])
    c = be.matmul(a, b)
    import numpy as np

    assert np.allclose(c.backend_buffer(), a.backend_buffer())
    e = be.elem_mul(a, a)
    assert float(e.backend_buffer()[0, 1]) == 4.0


def test_add_sub_transpose(be: NumPyArrayBackend):
    a = be.from_nested([[1.0, 2.0]])
    b = be.from_nested([[3.0, 4.0]])
    s = be.add(a, b)
    assert float(s.backend_buffer()[0, 0]) == 4.0
    d = be.sub(b, a)
    assert float(d.backend_buffer()[0, 1]) == 2.0
    t = be.transpose(a, conjugate=False)
    assert t.shape == (2, 1)


def test_matmul_shape_error(be: NumPyArrayBackend):
    a = be.ones((2, 3))
    b = be.ones((2, 3))
    with pytest.raises(NumericsError):
        be.matmul(a, b)


def test_session_can_hold_backend():
    from openmatlab.runtime.session import Session

    s = Session(numerics=NumPyArrayBackend())
    assert s.numerics is not None
    z = s.numerics.zeros((1, 1))
    assert z.is_scalar()

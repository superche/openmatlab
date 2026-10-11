"""Gherkin smoke for Array + NumPy backend (Issue #2)."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.numerics import NumPyArrayBackend

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]

scenarios("../../features/array_numpy.feature")


@given("a NumPy array backend", target_fixture="backend")
def numpy_backend():
    return NumPyArrayBackend()


@when(parsers.parse("I create a scalar array from {value:f}"), target_fixture="array")
def create_scalar(backend: NumPyArrayBackend, value: float):
    return backend.from_scalar(value)


@then("the array is scalar")
def array_is_scalar(array):
    assert array.is_scalar()


@then(parsers.parse("the array shape is {r:d} by {c:d}"))
def array_shape(array, r: int, c: int):
    assert array.shape == (r, c)


@when("I matmul identity with [[1, 2], [3, 4]]", target_fixture="array")
def matmul_identity(backend: NumPyArrayBackend):
    a = backend.from_nested([[1.0, 2.0], [3.0, 4.0]])
    eye = backend.eye(2)
    return backend.matmul(a, eye)


@then("the result equals [[1, 2], [3, 4]]")
def result_matrix(array):
    import numpy as np

    assert np.allclose(array.backend_buffer(), [[1.0, 2.0], [3.0, 4.0]])

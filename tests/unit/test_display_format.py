"""MATLAB/Octave format-short array display, not NumPy repr (Issue #411)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.display import format_array

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.mark.parametrize(
    "data, text",
    [
        ([[1.0, 2.0], [3.0, 40.0]], "    1    2\n    3   40"),
        ([[1.5, -2.0]], "    1.5000   -2.0000"),
        ([[0.5]], "0.5000"),
        ([[7.0]], "7"),
        ([[-3.0]], "-3"),
        (np.array([[True, False]]), "   1   0"),
        ([[1.0, np.nan, -np.inf]], "      1    NaN   -Inf"),
        ([[1e-5, 1.0]], "   1.0000e-05   1.0000e+00"),
        ([[1.0], [2.0]], "   1\n   2"),
    ],
)
def test_format_short(data, text):
    assert format_array(np.asarray(data)) == text


def test_empty_shows_dimensions():
    assert format_array(np.zeros((0, 3))) == "[](0x3)"


def test_never_numpy_repr():
    out = format_array(np.array([[1.0, 2.0], [3.0, 4.0]]))
    assert "[" not in out and "." not in out

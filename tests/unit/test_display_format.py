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
        ([[1e-5, 1.0]], "   0.0000   1.0000"),  # MATLAB: scale 1.0e+00 omitted (#417)
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


def test_common_scale_factor():
    assert format_array(np.array([[1000.5, 2000.0]])) == "   1.0e+03 *\n\n   1.0005   2.0000"
    assert format_array(np.array([[1e-5, 3e-5]])) == "   1.0e-05 *\n\n   1.0000   3.0000"
    assert format_array(np.array([[123456.7]])) == "1.2346e+05"  # scalars stay %.4e


def test_column_paging():
    out = format_array(np.arange(1.0, 21.0).reshape(1, 20), terminal_width=40)
    # width 5 per column -> 8 per block
    assert out.startswith("  Columns 1 through 8\n\n")
    assert "  Columns 9 through 16\n\n" in out
    assert out.endswith("  Columns 17 through 20\n\n   17   18   19   20")
    single = format_array(np.arange(10.0, 100.0, 10.0).reshape(1, 9), terminal_width=40)
    assert single.endswith("  Column 9\n\n   90")

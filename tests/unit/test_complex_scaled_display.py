"""Scaled / large-magnitude complex display (#453)."""

import pytest

from openmatlab.host.display import format_array

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]
np = pytest.importorskip("numpy")


@pytest.mark.parametrize("val,want", [
    (1e5 + 1j, "1.0000e+05 + 1.0000e+00i"),
    (1.5e10j, "0.0000e+00 + 1.5000e+10i"),
    (1e-5 + 1j, "1.0000e-05 + 1.0000e+00i"),
    (-1e6 - 2e6j, "-1.0000e+06 - 2.0000e+06i"),
    (3 + 4j, "3 + 4i"),
    (1.5 - 2j, "1.5000 - 2.0000i"),
])
def test_scalar(val, want):
    assert format_array(np.array([[val]])) == want


def test_matrix_common_scale_factor():
    assert format_array(np.array([[1e5 + 1j, 2]])) == (
        "   1.0e+05 *\n\n   1.0000 + 0.0000i   0.0000 + 0.0000i"
    )
    assert format_array(np.array([[1500.5 + 1j, 2]])) == (
        "   1.0e+03 *\n\n   1.5005 + 0.0010i   0.0020 + 0.0000i"
    )
    assert format_array(np.array([[1 + 2j, 3.5]])) == "   1.0000 + 2.0000i   3.5000 + 0.0000i"

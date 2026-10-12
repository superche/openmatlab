"""s^A, fractional A^p and expm (Issue #228)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _x(expr):
    s = Session.create_default()
    ReplSession(s).run_line(f"x = {expr};")
    return np.asarray(s.workspace.get("x").backend_buffer())


def test_expm_known_values():
    # expm([1 2;3 4]) — standard reference value (MATLAB doc / any linear-algebra text)
    np.testing.assert_allclose(
        _x("expm([1 2; 3 4])"), [[51.9690, 74.7366], [112.1048, 164.0738]], atol=1e-4
    )
    np.testing.assert_allclose(_x("expm([0 1; 0 0])"), [[1, 1], [0, 1]], atol=1e-12)
    np.testing.assert_allclose(_x("expm(zeros(2))"), np.eye(2), atol=1e-15)


def test_scalar_power_of_matrix_is_expm():
    np.testing.assert_allclose(_x("2^[1 0; 0 2]"), [[2, 0], [0, 4]], atol=1e-12)
    np.testing.assert_allclose(_x("2^[1 2; 3 4]"), _x("expm(log(2) * [1 2; 3 4])"), rtol=1e-12)


def test_fractional_matrix_power():
    np.testing.assert_allclose(_x("[4 0; 0 9]^0.5"), [[2, 0], [0, 3]], atol=1e-12)
    r = _x("[2 1; 1 2]^0.5")
    np.testing.assert_allclose(r @ r, [[2, 1], [1, 2]], atol=1e-12)


def test_complex_results_are_deferred_to_71():
    for expr in ("(-2)^[1 0; 0 1]", "[-1 0; 0 1]^0.5"):
        with pytest.raises(Exception, match="#71"):
            _x(expr)


def test_scalar_times_matrix_any_shape():
    """Found while testing #228: 1x1 * MxN must scale, not fail on matmul dims."""
    np.testing.assert_allclose(_x("3 * [1 2; 3 4]"), [[3, 6], [9, 12]])
    np.testing.assert_allclose(_x("[1; 2] * 2"), [[2], [4]])

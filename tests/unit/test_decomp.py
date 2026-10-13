"""Epic #538: dense decompositions."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


def test_eig_values_vectors_symmetric_order():
    s = _run("A = [4 1; 2 3]; [V, D] = eig(A); r = norm(A*V - V*D); es = eig([2 1; 1 2]); c = eig([0 -1; 1 0]);")
    assert _v(s, "r").item() < 1e-10
    assert _v(s, "es").reshape(-1).tolist() == pytest.approx([1, 3])
    assert sorted(_v(s, "c").imag.reshape(-1).tolist()) == pytest.approx([-1, 1])


def test_eig_left_vectors_and_vector_flag():
    s = _run("A = [4 1; 2 3]; [V, D, W] = eig(A); r = norm(W'*A - D*W'); [V2, d] = eig(A, 'vector');")
    assert _v(s, "r").item() < 1e-10 and _v(s, "d").shape == (2, 1)


def test_eig_rejects_integer_and_nan():
    with pytest.raises(Exception, match="double or single"):
        _run("e = eig(int8(1));")
    with pytest.raises(Exception, match="NaN or Inf"):
        _run("e = eig([1 NaN; 0 1]);")


def test_svd_full_econ():
    s = _run("s = svd([3 0; 0 4]); [U, S, V] = svd(magic(3)); r = norm(U*S*V' - magic(3)); [U2, S2] = svd(ones(3, 2), 'econ');")
    assert _v(s, "s").reshape(-1).tolist() == pytest.approx([4, 3]) and _v(s, "r").item() < 1e-10
    assert _v(s, "U2").shape == (3, 2) and _v(s, "S2").shape == (2, 2)


def test_lu_forms():
    s = _run("A = [1 2; 3 4]; [L, U, P] = lu(A); r = norm(P*A - L*U); [L2, U2] = lu([1 2; 3 4; 5 6]); r2 = norm(L2*U2 - [1 2; 3 4; 5 6]); [a, b, p] = lu(A, 'vector');")
    assert _v(s, "r").item() < 1e-12 and _v(s, "r2").item() < 1e-12
    assert _v(s, "p").tolist() == [[2, 1]]


def test_qr_full_econ_pivot():
    s = _run("A = [1 2; 3 4; 5 6]; [Q, R] = qr(A); a = size(Q); [Q2, R2] = qr(A, 'econ'); b = size(Q2); [Q3, R3, E] = qr(A); r = norm(A*E - Q3*R3);")
    assert _v(s, "a").tolist() == [[3, 3]] and _v(s, "b").tolist() == [[3, 2]] and _v(s, "r").item() < 1e-12


def test_chol_upper_lower_and_failure():
    s = _run("R = chol([4 2; 2 3]); L = chol([4 2; 2 3], 'lower'); [R2, p] = chol([1 2; 2 1]);")
    assert np.allclose(_v(s, "R"), [[2, 1], [0, 2 ** 0.5]])
    assert np.allclose(_v(s, "L"), _v(s, "R").T) and _v(s, "p").item() == 2
    with pytest.raises(Exception, match="positive definite"):
        _run("R = chol([1 2; 2 1]);")


def test_null_orth_trace_cross_dot():
    s = _run("N = null([1 1; 1 1]); O = orth([1 1; 1 1]); t = trace(magic(3)); c = cross([1 0 0], [0 1 0]); d = dot([1i 2], [1 1]);")
    assert _v(s, "N").shape == (2, 1) and _v(s, "O").shape == (2, 1) and _v(s, "t").item() == 15
    assert _v(s, "c").tolist() == [[0, 0, 1]] and complex(_v(s, "d").item()) == 2 - 1j
    with pytest.raises(Exception, match="length 3"):
        _run("c = cross([1 2], [3 4]);")
    with pytest.raises(Exception, match="square"):
        _run("t = trace(ones(2, 3));")


def test_sqrtm():
    s = _run("X = sqrtm([4 0; 0 9]); Y = sqrtm([2 1; 1 2]); r = norm(Y*Y - [2 1; 1 2]);")
    assert np.allclose(_v(s, "X"), [[2, 0], [0, 3]]) and _v(s, "r").item() < 1e-12

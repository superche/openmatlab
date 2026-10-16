"""#766: special functions and helpers (reference values from DLMF / Abramowitz-Stegun tables)."""
import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = pytest.mark.unit


def ev(code, var="r"):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(var).backend_buffer())


@pytest.mark.parametrize("code,want", [
    ("r = gamma([5 0.5]);", [24.0, np.sqrt(np.pi)]),
    ("r = gammaln(10);", [np.log(362880.0)]),
    ("r = beta(2,3);", [1 / 12]),
    ("r = psi(1);", [-0.5772156649015329]),
    ("r = erf(0.5);", [0.5204998778130465]),
    ("r = erfc(2);", [0.004677734981047266]),
    ("r = erfinv(erf(0.3));", [0.3]),
    ("r = besselj(0, 1);", [0.7651976865579666]),
    ("r = besselj(0.5, 2);", [np.sqrt(1 / np.pi) * np.sin(2)]),
    ("r = bessely(1, 3);", [0.3246744247918000]),
    ("r = besseli(0, 1);", [1.2660658777520082]),
    ("r = besselk(0.5, 1);", [np.sqrt(np.pi / 2) * np.exp(-1)]),
    ("r = besselj(2, -1.5);", [0.2320876721]),
    ("r = airy(1);", [0.1352924163128814]),
    ("r = airy(2, 0);", [0.6149266274460007]),
    ("r = abs(besselh(0, 1));", [np.hypot(0.7651976865579666, 0.08825696421567696)]),
])
def test_values(code, want):
    assert np.allclose(ev(code).reshape(-1), want, rtol=1e-10, atol=1e-10)


def test_ellipj_limits():
    s = Session.create_default()
    ReplSession(s).run_line("[sn, cn, dn] = ellipj(0.7, 0.4); r = sn.^2 + cn.^2; q = dn.^2 + 0.4*sn.^2;")
    assert np.isclose(float(s.workspace.get("r").backend_buffer().reshape(-1)[0]), 1.0)
    assert np.isclose(float(np.asarray(s.workspace.get("q").backend_buffer()).reshape(-1)[0]), 1.0)


def test_helpers():
    assert ev("r = perms([1 2 3]);").tolist() == [[3, 2, 1], [3, 1, 2], [2, 3, 1], [2, 1, 3], [1, 3, 2], [1, 2, 3]]
    assert ev("r = bitget(5, 1:3);").tolist() == [[1, 0, 1]]
    assert ev("r = toeplitz([1 2 3]);").tolist() == [[1, 2, 3], [2, 1, 2], [3, 2, 1]]
    assert ev("r = size(peaks(5));").tolist() == [[5, 5]]
    s = Session.create_default()
    ReplSession(s).run_line("r = dec2base(10, 8, 4);")
    assert s.workspace.get("r").text == "0012"


def test_colon_takes_rhs_extent_on_empty_dimension():
    assert ev("m = logical([1 1 0 1]'); r(m,:) = [1;2;3];").reshape(-1).tolist() == [1, 2, 0, 3]
    assert ev("r = zeros(1,0); r(1,:) = 1:4;").tolist() == [[1, 2, 3, 4]]
    assert ev("r = []; r(:,1) = [1;2;3];").shape == (3, 1)


def test_cellfun_legacy_isclass_and_size():
    assert ev("r = cellfun('isclass', {1, 'a', {2}}, 'char');").tolist() == [[False, True, False]]
    assert ev("r = cellfun('size', {ones(2,3), 1}, 2);").tolist() == [[3, 1]]

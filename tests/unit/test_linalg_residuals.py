"""#498: norm/cond/rcond/magic, strncmp/strncmpi, warning identifiers, [a,b] = f without parens."""

import subprocess
import sys

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime import warnings as mw
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture(autouse=True)
def _reset():
    mw.set_enabled(True)
    mw.set_last("")
    yield
    mw.set_enabled(True)
    mw.set_last("")


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_magic_matches_matlab():
    ws = _ws("a = magic(3); b = magic(4); c = magic(6); d = magic(10); s = sum(d); t = sum(d, 2)';")
    assert _v(ws, "a").tolist() == [[8, 1, 6], [3, 5, 7], [4, 9, 2]]
    assert _v(ws, "b").tolist() == [[16, 2, 3, 13], [5, 11, 10, 8], [9, 7, 6, 12], [4, 14, 15, 1]]
    assert _v(ws, "c")[0].tolist() == [35, 1, 6, 26, 19, 24]
    assert _v(ws, "d")[0].tolist() == [92, 99, 1, 8, 15, 67, 74, 51, 58, 40]
    assert set(_v(ws, "s").ravel()) == {505} and set(_v(ws, "t").ravel()) == {505}


def test_norm_cond_rcond():
    ws = _ws("n = [norm([3 4]) norm([3 4], 1) norm([3 4], Inf) norm([3 4], -Inf) norm([1 2; 3 4], 1)"
             " norm([1 2; 3 4], Inf) norm([1 2; 3 4], 'fro')]; m2 = norm([1 2; 3 4]);"
             " c = [cond([1 2; 3 4], 1) rcond([1 2; 3 4])]; c2 = cond([1 2; 3 4]); ci = cond([1 2; 2 4]);")
    np.testing.assert_allclose(_v(ws, "n"), [[5, 7, 4, 3, 6, 7, np.sqrt(30)]])
    np.testing.assert_allclose(_v(ws, "m2"), np.linalg.norm([[1, 2], [3, 4]], 2))
    np.testing.assert_allclose(_v(ws, "c"), [[21, 1 / 21]])
    np.testing.assert_allclose(_v(ws, "c2"), np.linalg.cond([[1, 2], [3, 4]]))
    assert _v(ws, "ci").item() > 1e15  # singular: huge or Inf, as in MATLAB (roundoff-dependent)


def test_strncmp():
    ws = _ws("t = [strncmp('abc', 'abd', 2) strncmp('abc', 'abc', 10) strncmp('abc', 'abcd', 10)"
             " strncmpi('ABc', 'abD', 2) strncmp('a', 'b', 0) strncmp(1, 1, 1)];"
             " u = strncmp({'Mars', 'Mxx'}, 'Ma', 2);")
    assert _v(ws, "t").tolist() == [[True, True, False, True, True, False]]
    assert _v(ws, "u").tolist() == [[True, False]]


def test_warning_identifiers():
    ws = _ws("warning('my:id', 'v=%d', 2); [m, i] = lastwarn; warning('off', 'my:id'); warning('my:id', 'quiet');"
             " q = warning('query', 'my:id'); [m2, i2] = lastwarn; warning('on', 'my:id'); q2 = warning('query', 'my:id');"
             " warning('off', 'MATLAB:singularMatrix'); x = [1 2; 2 4] \\ [1; 2]; [m3, i3] = lastwarn;")
    assert ws.get("m").text == "v=2" and ws.get("i").text == "my:id"
    assert ws.get("q").text == "off" and ws.get("m2").text == "quiet" and ws.get("q2").text == "on"
    assert ws.get("i3").text == "MATLAB:singularMatrix"


def test_off_identifier_suppresses_print():
    out = subprocess.run([sys.executable, "-m", "openmatlab", "-e",
                          "warning('off', 'MATLAB:singularMatrix'); x = [1 2; 2 4] \\ [1; 2]; warning('my:a', 'shown')"],
                         capture_output=True, text=True, check=True)
    assert "singular" not in out.stderr and "Warning: shown" in out.stderr
    assert "ans" not in out.stdout  # a call with no outputs displays nothing

"""#766 burn-down: missing base-MATLAB functions found by the corpus."""

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


def _t(s, n):
    return s.workspace.get(n).text


def test_text_functions():
    s = _run("[t, r] = strtok('  hello world'); sp = isspace('a b'); f = findstr('abcbc', 'bc'); "
             "m = strmatch('ap', {'apple','banana','apricot'}); e = strmatch('apple', {'apple ','apples'}, 'exact'); "
             "b = base2dec('ff', 16); b2 = base2dec({'10','11'}, 2); v = validatestring('app', {'apple','pear'}); "
             "z = vectorize('x*y^2'); j = strjust(['a  ';'bb '], 'right'); [t2, r2] = strtok('a,b', ',');")
    assert _t(s, "t") == "hello" and _t(s, "r") == " world"
    assert _v(s, "sp").tolist() == [[False, True, False]] and _v(s, "f").tolist() == [[2, 4]]
    assert _v(s, "m").tolist() == [[1], [3]] and _v(s, "e").tolist() == [[1]]
    assert _v(s, "b").item() == 255 and _v(s, "b2").tolist() == [[2], [3]]
    assert _t(s, "v") == "apple" and _t(s, "z") == "x.*y.^2" and s.workspace.get("j").rows == ("  a", " bb")
    assert _t(s, "t2") == "a" and _t(s, "r2") == ",b"


def test_matrix_functions():
    s = _run("r = rref([1 2; 2 4]); p = pascal(3); h = hankel(1:3); hd = hadamard(2); q = polyvalm([1 0 1], 2*eye(2)); "
             "g = gradient([1 4 9 16]); [gx, gy] = gradient(magic(3)); c = conv2([1 2; 3 4], [1 1]); "
             "cs = conv2(magic(3), ones(2), 'same'); f2 = filter2([1 1], [1 2 3]); vd = vander([1 2 3]); "
             "hb = hilb(2); ih = invhilb(2) * hilb(2); w = wilkinson(3); cp = compan([1 -3 2]); "
             "re = repelem([1 2], [2 3]); rc = repelem('ab', 2); d = del2([1 4 9 16 25]);")
    assert _v(s, "r").tolist() == [[1, 2], [0, 0]] and _v(s, "p").tolist() == [[1, 1, 1], [1, 2, 3], [1, 3, 6]]
    assert _v(s, "h").tolist() == [[1, 2, 3], [2, 3, 0], [3, 0, 0]] and _v(s, "hd").tolist() == [[1, 1], [1, -1]]
    assert _v(s, "q").tolist() == [[5, 0], [0, 5]] and _v(s, "g").tolist() == [[3, 4, 6, 7]]
    assert _v(s, "gx").tolist()[0] == [-7, -1, 5] and _v(s, "c").tolist() == [[1, 3, 2], [3, 7, 4]]
    assert _v(s, "cs").tolist() == [[17, 19, 13], [21, 23, 9], [13, 11, 2]] and _v(s, "f2").tolist() == [[3, 5, 3]]
    assert _v(s, "vd").tolist() == [[1, 1, 1], [4, 2, 1], [9, 3, 1]] and np.allclose(_v(s, "ih"), np.eye(2))
    assert _v(s, "w").tolist() == [[1, 1, 0], [1, 0, 1], [0, 1, 1]] and _v(s, "cp").tolist() == [[3, -2], [1, 0]]
    assert _v(s, "re").tolist() == [[1, 1, 2, 2, 2]] and _t(s, "rc") == "aabb" and np.allclose(_v(s, "d"), 0.5)


def test_rat_legendre_and_elementary():
    s = _run("a = rat(pi); [n, d] = rat(0.75); l = legendre(2, 0.5); e = erfcx(30); x = reallog(exp(2)); "
             "y = realsqrt(9); z = realpow(2, 3); t = [secd(60) cotd(45) acotd(1) coth(1)];")
    assert _t(s, "a") == "3 + 1/(7 + 1/16)" and (_v(s, "n").item(), _v(s, "d").item()) == (3, 4)
    assert np.allclose(_v(s, "l").ravel(), [-0.125, -1.299038105676658, 2.25])
    assert abs(_v(s, "e").item() - 0.018795888861416751) < 1e-12
    assert _v(s, "x").item() == pytest.approx(2) and _v(s, "y").item() == 3 and _v(s, "z").item() == 8
    assert np.allclose(_v(s, "t"), [2, 1, 45, 1 / np.tanh(1)])


@pytest.mark.parametrize("bad,msg", [
    ("reallog(-1)", "complex result"), ("realsqrt(-1)", "complex result"), ("realpow(-8, 1/3)", "complex result"),
    ("hadamard(6)", "power of 2"), ("base2dec('19', 8)", "invalid for base"), ("validatestring('z', {'a','b'})", "did not match"),
    ("validatestring('a', {'ab','ac'})", "more than one"), ("repelem([1 2], [1 2 3])", "length must match"),
    ("polyvalm([1 2], [1 2 3])", "square"), ("legendre(-1, 0)", "nonnegative"),
])
def test_errors(bad, msg):
    with pytest.raises(Exception, match=msg):
        _run(bad)

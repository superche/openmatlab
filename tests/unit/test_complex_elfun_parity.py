"""Complex elfun parity: trig/hyperbolic/inverse on complex input and MATLAB branch cuts (#454)."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


CASES = [  # (expr, MATLAB value)
    ("sin(1i)", 1.1752011936438014j),
    ("cos(1i)", 1.5430806348152437),
    ("exp(1i*pi)", -1 + 1.2246467991473532e-16j),
    ("abs(3+4i)", 5.0),
    ("tan(1+1i)", 0.2717525853195117 + 1.0839233273386946j),
    ("sinh(1i)", 0.8414709848078965j),
    ("cosh(1+1i)", 0.8337300251311491 + 0.9888977057628651j),
    ("tanh(1i)", 1.5574077246549023j),
    ("asin(2)", 1.5707963267948966 - 1.3169578969248166j),
    ("asin(-2)", -1.5707963267948966 + 1.3169578969248166j),
    ("acos(2)", 1.3169578969248166j),
    ("acos(-2)", 3.141592653589793 - 1.3169578969248166j),
    ("atan(1)", 0.7853981633974483),
    ("asinh(1i)", 1.5707963267948966j),
    ("acosh(0.5)", 1.0471975511965976j),
    ("acosh(-2)", 1.3169578969248166 + 3.141592653589793j),
    ("atanh(2)", 0.5493061443340549 + 1.5707963267948966j),
    ("atanh(-2)", -0.5493061443340549 + 1.5707963267948966j),
    ("log10(-100)", 2 + 1.3643763538418414j),
    ("log(-1)", 3.141592653589793j),
    ("sqrt(-4)", 2j),
]


@pytest.mark.parametrize("expr,want", CASES)
def test_complex_elfun_values(expr, want):
    assert _v(_ws("r = " + expr + ";"), "r").item() == pytest.approx(want, abs=1e-12)


def test_in_domain_stays_real_and_elementwise():
    ws = _ws("a = asin([0.5 1]); b = acosh(2); c = atanh(0.5); d = asin([0.5 2]);")
    for n in "abc":
        assert not np.iscomplexobj(_v(ws, n)), n
    assert _v(ws, "d")[0, 0] == pytest.approx(0.5235987755982989)
    assert _v(ws, "d")[0, 1] == pytest.approx(1.5707963267948966 - 1.3169578969248166j)

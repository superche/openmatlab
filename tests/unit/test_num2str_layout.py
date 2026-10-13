"""#505: num2str non-integer matrix layout (MATLAB %w.dg rule) and pinned sprintf tie rounding."""

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _r(code):
    s = Session.create_default()
    ReplSession(s).run_line(f"x__ = {code};")
    return s.workspace.get("x__")


@pytest.mark.parametrize("code,rows", [
    ("num2str([pi 2*pi])", ("3.1416      6.2832",)),
    ("num2str([1.5 22.25; 3 4])", ("1.5        22.25", "  3            4")),
    ("num2str(-[1.5 2])", ("-1.5           -2",)),
    ("num2str(pi*[1 2], 3)", ("3.14      6.28",)),
    ("num2str([1 NaN 2.5])", ("1         NaN         2.5",)),
    ("num2str([1000.5 2])", ("1000.5" + " " * 14 + "2",)),  # d = 8, w = 15
])
def test_num2str_float_matrix(code, rows):
    assert _r(code).rows == rows


def test_integer_matrices_unchanged():
    assert _r("num2str([1 2 3])").text == "1  2  3"
    assert _r("num2str([1 10; 2 3])").rows == (" 1  10", " 2   3")


def test_sprintf_ties_are_pinned_to_c_rounding():
    # Decision (#505): ties use C printf round-half-even on the exact binary value (glibc,
    # the same as MATLAB on Linux). 2.25 and 0.125 are exact ties; 2.675 is just below its tie.
    assert _r("sprintf('%.1f', 2.25)").text == "2.2"
    assert _r("sprintf('%.2f', 0.125)").text == "0.12"
    assert _r("sprintf('%.1f', 0.35)").text == "0.3"  # 0.35 is stored slightly below 0.35
    assert _r("sprintf('%.2f', 2.675)").text == "2.67"

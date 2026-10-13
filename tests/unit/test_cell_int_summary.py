"""Cell display summarizes non-scalar integer arrays as [RxC class] (#464)."""


import pytest

from openmatlab.host.display import _format_value
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _show(code, name="c"):
    s = Session.create_default()
    ReplSession(s).run_line(code + ";")
    return _format_value(s.workspace.get(name))


def test_cell_int_arrays_are_summarized():
    out = _show("c = {int8([1 2]), int16(5), uint8([]), int32(ones(2,2,2)), [1 2]}")
    lines = out.splitlines()
    assert lines[0] == "{1×5 cell}"
    assert lines[1] == "  (1,1) = [1×2 int8]"
    assert lines[2] == "  (1,2) = 5"          # scalar ints still print the value
    assert lines[3] == "  (1,3) = [0×0 uint8]"
    assert lines[4] == "  (1,4) = [2×2×2 int32]"
    assert lines[5] == "  (1,5) =    1   2"   # doubles unchanged


def test_nd_int_summary_names_class():
    import numpy as np
    from openmatlab.host.display import format_array

    assert format_array(np.ones((2, 2, 2), dtype=np.uint16)) == "[2×2×2 uint16]"
    assert format_array(np.ones((2, 2, 2))) == "[2×2×2 double]"

"""single precision class (#461)."""

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


@pytest.mark.parametrize("code,cls", [
    ("single(1.5)", "single"), ("single(2) * 2", "single"), ("[1 2] + single(1)", "single"),
    ("single(1) + int8(1)", "int8"), ("sqrt(single(2))", "single"), ("sum(single([1 2]))", "single"),
    ("mean(single([1 2]))", "single"), ("max(single([1 2]))", "single"),
    ("zeros(2, 'single')", "single"), ("ones(1, 2, 'like', single(1))", "single"),
    ("eps('single')", "single"), ("realmax('single')", "single"), ("single(1) > 0", "logical"),
    ("[single(1) 2]", "single"), ("[int8(1) single(2)]", "int8"), ("single(2) ^ 2", "single"),
    ("-single(1)", "single"), ("single([1 2])'", "single"), ("single([1 2]) * [1; 2]", "single"),
    ("single(1 + 2i)", "single"), ("double(single(1))", "double"), ("cast(3, 'single')", "single"),
    ("NaN(1, 'single')", "single"),
])
def test_single_class_rules(code, cls):
    assert _ws("r = " + code + ";").get("r").matlab_class() == cls


def test_single_values_and_precision():
    assert _v(_ws("r = single(1) / 3;"), "r").item() == np.float32(1) / np.float32(3)
    assert _v(_ws("r = eps('single');"), "r").item() == float(np.finfo(np.float32).eps)
    assert _v(_ws("r = realmax('single');"), "r").item() == float(np.finfo(np.float32).max)
    assert _v(_ws("r = double(single(0.1));"), "r").item() == float(np.float32(0.1))
    assert _v(_ws("r = single(1e39);"), "r").item() == float("inf")


def test_single_index_assign_and_loop():
    ws = _ws("x = single(1:4); a = class(x(2)); b = class(x(x > 2)); y = [1 2]; y(2) = single(5); c = class(y);"
             " for k = single([1 2]), end; d = class(k);")
    for n in "abcd":
        assert ws.get(n).text == "single", n
    assert _ws("r = isfloat(single(1)) && isa(single(1), 'float') && isnumeric(single(1));").get("r")


def test_single_class_arg_errors():
    with pytest.raises(Exception, match="class must be"):
        _ws("eps('int8')")

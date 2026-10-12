"""Exact int64/uint64 arithmetic (#463); idivide and bit ops (#462)."""

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


def _r(code):
    ws = _ws("r = " + code + ";")
    return ws.get("r").matlab_class(), _v(ws, "r").reshape(-1).tolist()


@pytest.mark.parametrize("code,cls,want", [
    ("intmax('int64') - int64(1)", "int64", [2 ** 63 - 2]),
    ("intmax('int64') - 1", "int64", [2 ** 63 - 2]),
    ("intmax('int64') + 1", "int64", [2 ** 63 - 1]),
    ("intmin('int64') - 1", "int64", [-2 ** 63]),
    ("intmax('uint64') - uint64(1)", "uint64", [2 ** 64 - 2]),
    ("int64(2)^62 * int64(2)", "int64", [2 ** 63 - 1]),
    ("(intmax('int64') - 6) / int64(2)", "int64", [2 ** 62 - 3]),  # 4611686018427387900.5 rounds away
    ("int64(-7) / 2", "int64", [-4]),
    ("int64(1) / 0", "int64", [2 ** 63 - 1]),
    ("int64(10) .* [1 2 3]", "int64", [10, 20, 30]),
    ("int64(5) * 0.5", "int64", [3]),
    ("int8(100) + 100", "int8", [127]),
])
def test_exact_wide_int_arithmetic(code, cls, want):
    assert _r(code) == (cls, want)


@pytest.mark.parametrize("code,cls,want", [
    ("idivide(int32(7), int32(2))", "int32", [3]),
    ("idivide(int32(-7), int32(2), 'floor')", "int32", [-4]),
    ("idivide(int32(7), 2, 'round')", "int32", [4]),
    ("idivide(int8([5 -5]), int8(2), 'ceil')", "int8", [3, -2]),
    ("idivide(int16(1), int16(0))", "int16", [32767]),
    ("bitand(12, 10)", "double", [8]),
    ("bitor(uint8(12), uint8(3))", "uint8", [15]),
    ("bitxor(int8(5), int8(3))", "int8", [6]),
    ("bitand(uint16(3), 5)", "uint16", [1]),
    ("bitshift(uint8(255), 1)", "uint8", [254]),
    ("bitshift(16, -2)", "double", [4]),
    ("bitshift(int8(-8), -1)", "int8", [-4]),
    ("bitshift(intmax('int8'), 1)", "int8", [-2]),
    ("bitshift(1, [1 2 3])", "double", [2, 4, 8]),
])
def test_idivide_and_bitops(code, cls, want):
    assert _r(code) == (cls, want)


@pytest.mark.parametrize("code,msg", [
    ("idivide(7, 2)", "At least one input must be an integer"),
    ("bitand(-1, 3)", "Double inputs must have integer values"),
    ("bitand(int8(1), int16(1))", "Integers can only be combined"),
    ("idivide(int8(1), int8(1), 'up')", "opt must be"),
])
def test_errors(code, msg):
    with pytest.raises(Exception, match=msg):
        _ws(code)

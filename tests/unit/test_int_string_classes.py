"""Integer classes, string class, char indexing (Epic #457: #72 #78 #183)."""

from __future__ import annotations

import io

import numpy as np
import pytest

from openmatlab.host.display import ConsoleDisplay, format_array
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.char_value import CharValue, StringValue
from openmatlab.runtime.evaluator import Evaluator
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def _cls(ws, n):
    return ws.get(n).matlab_class()


# ---------------- integers (#72) ----------------

@pytest.mark.parametrize("cls", ["int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64"])
def test_cast_class_name(cls):
    ws = _ws(f"x = {cls}(3.6); c = class(x);")
    assert _cls(ws, "x") == cls and ws.get("c").text == cls and _v(ws, "x").item() == 4


def test_cast_rounds_half_away_and_saturates():
    ws = _ws("a = int8([2.5 -2.5 200 -200 NaN]); b = uint8(-3); c = int32(Inf);")
    assert _v(ws, "a").tolist() == [[3, -3, 127, -128, 0]]
    assert _v(ws, "b").item() == 0 and _v(ws, "c").item() == 2**31 - 1


def test_intmax_intmin():
    ws = _ws("a = intmax('int32'); b = intmin('int8'); c = intmax('uint64'); d = intmax; e = class(intmin('uint16'));")
    assert _v(ws, "a").item() == 2**31 - 1 and _v(ws, "b").item() == -128
    assert int(_v(ws, "c").item()) == 2**64 - 1 and _v(ws, "d").item() == 2**31 - 1
    assert ws.get("e").text == "uint16"


def test_arithmetic_with_doubles_keeps_class():
    ws = _ws("a = uint8(250) + 10; b = int16(7) / 2; c = int32(5) * 2.6; d = uint8(3) - 5; e = int8([1 2]) .* [1.5 2];")
    assert _v(ws, "a").item() == 255 and _cls(ws, "a") == "uint8"
    assert _v(ws, "b").item() == 4 and _v(ws, "c").item() == 13 and _v(ws, "d").item() == 0
    assert _v(ws, "e").tolist() == [[2, 4]] and _cls(ws, "e") == "int8"


def test_division_by_zero_saturates():
    ws = _ws("a = int32(7)/0; b = -int32(7)/0; c = int32(0)/0;")
    assert [_v(ws, n).item() for n in "abc"] == [2**31 - 1, -(2**31), 0]


def test_mixed_integer_classes_error():
    with pytest.raises(Exception, match="Integers can only be combined"):
        _ws("x = int8(1) + int16(1);")


def test_integer_matrix_multiply_error_but_scalar_ok():
    with pytest.raises(Exception, match="MTIMES"):
        _ws("x = int8([1 2]) * int8([1; 2]);")
    assert _v(_ws("x = int8(3) * int8([1 2]);"), "x").tolist() == [[3, 6]]


def test_power_saturates():
    ws = _ws("x = int8(2) .^ 10; y = uint8(3)^2;")
    assert _v(ws, "x").item() == 127 and _v(ws, "y").item() == 9


def test_index_assign_concat_preserve_class():
    ws = _ws(
        "v = int32([1 2 3]); v(2) = 7.6; a = v(v > 2); "
        "w = [1.5 2]; w(1) = int8(3); g = int8(5); g(3) = 1; "
        "c = [int8(1) 2.7]; d = [1 int16(300); int8(1) 2];"
    )
    assert _v(ws, "v").tolist() == [[1, 8, 3]] and _cls(ws, "a") == "int32"
    assert _cls(ws, "w") == "int8" and _v(ws, "w").tolist() == [[3, 2]]
    assert _v(ws, "g").tolist() == [[5, 0, 1]]
    assert _cls(ws, "c") == "int8" and _v(ws, "c").tolist() == [[1, 3]]
    assert _cls(ws, "d") == "int16" and _v(ws, "d").tolist() == [[1, 300], [1, 2]]


def test_reductions_native_class_mean_double():
    ws = _ws("x = int8([100 100 -3]); s = sum(x); m = max(x); u = unique(uint8([3 1 3])); mu = mean(int8([1 2]));")
    assert _v(ws, "s").item() == 127 and _cls(ws, "s") == "int8"
    assert _cls(ws, "m") == "int8" and _cls(ws, "u") == "uint8"
    assert _cls(ws, "mu") == "double" and _v(ws, "mu").item() == 1.5


def test_class_predicates():
    ws = _ws("a = isinteger(int8(1)); b = isinteger(1); c = isfloat(int8(1)); d = isnumeric(uint8(1)); "
             "e = isa(int8(1), 'integer'); f = isa(1, 'float'); g = isa(int16(1), 'numeric'); h = isa(1, 'int8');")
    assert [bool(_v(ws, n).item()) for n in "abcdefgh"] == [True, False, False, True, True, True, True, False]


def test_cast_and_double_and_uint8_of_char():
    ws = _ws("x = cast(3.7, 'uint16'); d = double(int8(5)) / 2; u = uint8('a'); c = char(uint8([72 105]));")
    assert _cls(ws, "x") == "uint16" and _v(ws, "x").item() == 4
    assert _v(ws, "d").item() == 2.5 and _v(ws, "u").item() == 97 and ws.get("c").text == "Hi"


def test_int_colon_and_for_loop_class():
    ws = _ws("r = int8(1):int8(3); for k = int8(1):int8(2), end; c = class(k);")
    assert _cls(ws, "r") == "int8" and ws.get("c").text == "int8"


def test_int_display():
    assert format_array(np.array([[1, 2, 300]], dtype=np.int32)) == "    1    2  300"


# ---------------- class / 'like' args (#183) ----------------

def test_constructors_class_names():
    ws = _ws("a = zeros(2, 'int32'); b = ones(1, 3, 'uint8'); c = eye(2, 'int16'); d = zeros([2 2], 'double');")
    assert _cls(ws, "a") == "int32" and _v(ws, "a").shape == (2, 2)
    assert _cls(ws, "b") == "uint8" and _cls(ws, "c") == "int16" and _cls(ws, "d") == "double"


def test_constructors_like():
    ws = _ws("A = int8([1 2]); a = ones(1, 2, 'like', A); b = zeros('like', A); c = zeros(1, 2, 'like', 1i); "
             "t = true(2, 'like', false); n = nan(1, 2, 'like', 1);")
    assert _cls(ws, "a") == "int8" and _cls(ws, "b") == "int8"
    assert np.iscomplexobj(_v(ws, "c")) and _cls(ws, "t") == "logical" and np.isnan(_v(ws, "n")).all()


def test_constructor_bad_class_errors():
    with pytest.raises(Exception, match="not supported"):
        _ws("x = zeros(2, 'logical');")
    with pytest.raises(Exception, match="not supported"):
        _ws("x = nan(2, 'int8');")


# ---------------- string class (#78) ----------------

def test_string_scalar_basics():
    ws = _ws('s = "abc"; c = class(s); z = size(s); n = numel(s); e = isempty(""); k = ischar(s); j = isstring(s);')
    assert isinstance(ws.get("s"), StringValue) and ws.get("c").text == "string"
    assert _v(ws, "z").tolist() == [[1, 1]] and _v(ws, "n").item() == 1
    assert not _v(ws, "e").item() and not _v(ws, "k").item() and _v(ws, "j").item()


def test_string_plus_and_compare():
    ws = _ws('a = "ab" + "cd"; b = "n=" + 5; c = "a" == "a"; d = "abc" < "abd"; e = \'abc\' == "abc";')
    assert ws.get("a").text == "abcd" and ws.get("b").text == "n=5"
    assert _v(ws, "c").item() and _v(ws, "d").item() and _v(ws, "e").item()


def test_string_conversions():
    ws = _ws('l = strlength("hello"); c = char("hi"); s = string(42); t = string(\'x\'); d = double("3.5"); q = double("x");')
    assert _v(ws, "l").item() == 5 and type(ws.get("c")) is CharValue and ws.get("c").text == "hi"
    assert ws.get("s").text == "42" and isinstance(ws.get("t"), StringValue)
    assert _v(ws, "d").item() == 3.5 and np.isnan(_v(ws, "q").item())


def test_string_unsupported_ops_and_arrays():
    with pytest.raises(Exception, match="not supported for operands of type 'string'"):
        _ws('x = "a" * 2;')
    with pytest.raises(Exception, match="string arrays"):
        _ws('x = ["a" "b"];')


def test_string_still_works_as_text_argument():
    ws = _ws('switch "b", case "a", r = 1; case "b", r = 2; end; w = which("zeros");')
    assert _v(ws, "r").item() == 2 and "zeros" in ws.get("w").text


def test_string_display():
    s = Session.create_default()
    out = io.StringIO()
    ev = Evaluator(workspace=s.workspace, functions=s.functions, numerics=s.numerics,
                   display=ConsoleDisplay(s.workspace, out))
    ev.eval_source('s = "abc"')
    assert out.getvalue() == 's =\n\n"abc"\n\n'


# ---------------- char indexing ----------------

def test_char_index_read():
    ws = _ws("s = 'hello'; a = s(1); b = s(2:3); e = s(end); r = s(end:-1:1); m = ['ab'; 'cd']; x = m(2,:); y = m(:,1)';")
    assert [ws.get(n).text for n in "aberxy"] == ["h", "el", "o", "olleh", "cd", "ac"]


def test_char_assign_and_delete():
    ws = _ws("s = 'hello'; s(1) = 'J'; t = 'abc'; t(2) = []; u = 'ab'; u(4) = 'd';")
    assert ws.get("s").text == "Jello" and ws.get("t").text == "ac"
    assert ws.get("u").text == "ab\x00d"  # MATLAB pads with char(0)


def test_char_plus_char_is_numeric():
    assert _v(_ws("x = 'a' + 'b';"), "x").item() == 195


def test_numeric_errors_surface_as_eval_errors():
    """Found in acceptance: `-e 'int8(1)+int16(1)'` printed a Python traceback."""
    from openmatlab.runtime.evaluator import EvalError

    with pytest.raises(EvalError, match="Integers can only be combined"):
        _ws("x = int8(1) + int16(1);")

"""Complex numbers (Epic #449: #71, #229; unblocks #228 complex results)."""

from __future__ import annotations

import io

import numpy as np
import pytest

from openmatlab.host.display import ConsoleDisplay, format_array
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError, Evaluator
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


@pytest.mark.parametrize("src, want", [("3+4i", 3 + 4j), ("2j", 2j), ("1i", 1j), ("4I", 4j), ("2.5e1i", 25j), ("1 + i", 1 + 1j)])
def test_imaginary_literals(src, want):
    assert _v(_ws(f"z = {src};"), "z").item() == want


def test_literal_suffix_needs_word_boundary():
    # `3if` is not 3i followed by f; bound variable i does not affect 2i
    ws = _ws("i = 5; z = 2i; w = i;")
    assert _v(ws, "z").item() == 2j and _v(ws, "w").item() == 5


def test_arithmetic_and_narrowing():
    ws = _ws("a = (1+2i)*(3-4i); b = (1+2i)/(3-4i); c = 1i*1i; r = isreal(c); d = [1+1i 2; 3 4]*[1; 1i];")
    assert _v(ws, "a").item() == (1 + 2j) * (3 - 4j)
    assert np.isclose(_v(ws, "b").item(), (1 + 2j) / (3 - 4j))
    assert _v(ws, "c").dtype == np.float64 and _v(ws, "c").item() == -1 and _v(ws, "r").all()
    assert _v(ws, "d").tolist() == [[1 + 3j], [3 + 4j]]


def test_transposes():
    ws = _ws("z = [1+2i 3-1i]; a = z'; b = z.';")
    assert _v(ws, "a").tolist() == [[1 - 2j], [3 + 1j]]
    assert _v(ws, "b").tolist() == [[1 + 2j], [3 - 1j]]


def test_elfun_enter_complex_domain():
    ws = _ws("a = sqrt(-4); b = log(-1); c = sqrt([4 -9]); d = exp(1i*pi);")
    assert np.isclose(_v(ws, "a").item(), 2j)
    assert np.isclose(_v(ws, "b").item(), np.pi * 1j)
    assert np.allclose(_v(ws, "c"), [[2, 3j]])
    assert np.isclose(_v(ws, "d").item(), -1)


def test_part_functions():
    ws = _ws("z = 3-4i; r = real(z); m = imag(z); a = abs(z); c = conj(z); g = angle(1i); k = class(z);")
    assert [_v(ws, n).item() for n in "rmacg"] == [3, -4, 5, 3 + 4j, np.pi / 2]
    assert ws.get("k").text == "double"


def test_complex_builtin_keeps_zero_imag():
    ws = _ws("z = complex(1, 0); r = isreal(z); w = z + 0; q = isreal(w); v = complex([1 2], [3 4]);")
    assert not _v(ws, "r").any() and _v(ws, "q").all()
    assert _v(ws, "v").tolist() == [[1 + 3j, 2 + 4j]]


def test_powers_complex_results():
    ws = _ws("a = (-8)^(1/3); b = [-1 4].^0.5; c = 2^1i; d = 1i^2;")
    assert np.isclose(_v(ws, "a").item(), 1 + np.sqrt(3) * 1j)
    assert np.allclose(_v(ws, "b"), [[1j, 2]])
    assert np.isclose(_v(ws, "c").item(), 2 ** 1j)
    assert _v(ws, "d").item() == -1


def test_matrix_power_complex_228_229():
    ws = _ws("A = [1 2; 3 4]^0.5; B = A*A; C = [1i 0; 0 2]^2; D = (-2)^[0 1; 1 0];")
    assert np.allclose(_v(ws, "B"), [[1, 2], [3, 4]])
    assert np.iscomplexobj(_v(ws, "A"))
    assert np.allclose(_v(ws, "C"), [[-1, 0], [0, 4]])
    assert np.allclose(_v(ws, "D"), [[-1.25, -0.75], [-0.75, -1.25]])


def test_index_assign_concat():
    ws = _ws("z = [1 2 3]; z(2) = 1i; x = z(2); y = [1+2i 3]; z(2) = 0; r = isreal(z);")
    assert _v(ws, "x").item() == 1j and _v(ws, "y").tolist() == [[1 + 2j, 3]]
    assert _v(ws, "r").all()  # all-zero imaginary narrows back to real


def test_comparisons_and_truthiness():
    ws = _ws("a = (1+2i) == (1+2i); b = (1+2i) ~= (1-2i); c = (1+5i) < 2; t = 0; if 1i, t = 1; end")
    assert _v(ws, "a").all() and _v(ws, "b").all() and _v(ws, "c").all() and _v(ws, "t").item() == 1


def test_reductions_and_extrema():
    ws = _ws("s = sum([1i 2 3i]); p = prod([1i 1i]); m = max([1 -3i 2]); [n, k] = min([2 -1i 3]); c = cumsum([1i 1]);")
    assert _v(ws, "s").item() == 2 + 4j and _v(ws, "p").item() == -1
    assert _v(ws, "m").item() == -3j  # by magnitude (MATLAB)
    assert _v(ws, "n").item() == -1j and _v(ws, "k").item() == 2
    assert _v(ws, "c").tolist() == [[1j, 1 + 1j]]


def test_sort_and_find_complex():
    ws = _ws("s = sort([3 1i -2]); f = find([0 1i 0]); r = sort([2 1+1i], 'ComparisonMethod', 'real');")
    assert _v(ws, "s").tolist() == [[1j, -2, 3]] and _v(ws, "f").tolist() == [[2]]
    assert _v(ws, "r").tolist() == [[1 + 1j, 2]]


def test_mod_complex_errors():
    with pytest.raises(EvalError, match="Complex arguments are not supported"):
        _ws("x = mod(1i, 2);")


@pytest.mark.parametrize("data, text", [
    (np.array([[3 + 4j]]), "3 + 4i"),
    (np.array([[1.5 - 2j]]), "1.5000 - 2.0000i"),
    (np.array([[1 + 2j, 3]]), "   1 + 2i   3 + 0i"),
    (np.array([[1.5 - 2j], [3]]), "   1.5000 - 2.0000i\n   3.0000 + 0.0000i"),
])
def test_display_format(data, text):
    assert format_array(data) == text


def test_console_display():
    s = Session.create_default()
    out = io.StringIO()
    ev = Evaluator(workspace=s.workspace, functions=s.functions, numerics=s.numerics,
                   display=ConsoleDisplay(s.workspace, out))
    ev.eval_source("z = sqrt(-4)")
    assert out.getvalue() == "z =\n\n0 + 2i\n\n"

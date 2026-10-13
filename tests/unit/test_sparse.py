"""Sparse matrices (Epic #487, #451): construction, queries, propagation rules, S^p, display."""

import numpy as np
import pytest

from openmatlab.host.display import _format_value
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def _sp(ws, n):
    return bool(getattr(ws.get(n), "issparse", False))


def test_construction_forms():
    ws = _ws("a = sparse([1 0; 0 2]); b = sparse(2, 3); c = sparse([1 1 2], [1 1 3], [2 3 4]);"
             " d = sparse([1 2], [1 2], 5, 3, 3); e = speye(3); f = spones(sparse([0 3; 4 0]));"
             " g = sparse([1 1], [1 1], [true true]);")
    for n in "abcdefg":
        assert _sp(ws, n), n
    assert _v(ws, "b").shape == (2, 3) and not _v(ws, "b").any()
    assert _v(ws, "c").tolist() == [[5, 0, 0], [0, 0, 4]]  # duplicates add
    assert _v(ws, "d").tolist() == [[5, 0, 0], [0, 5, 0], [0, 0, 0]]  # scalar v expands
    assert _v(ws, "e").tolist() == np.eye(3).tolist() and _v(ws, "f").tolist() == [[0, 1], [1, 0]]
    assert ws.get("g").matlab_class() == "logical" and _v(ws, "g").tolist() == [[True]]


def test_queries():
    ws = _ws("S = sparse([1 0; 0 2]); i = issparse(S); j = issparse([1 0]); n = nnz(S); z = nonzeros(S);"
             " m = nzmax(S); F = full(S); k = issparse(F); c = class(S); s = size(S); q = isequal(S, [1 0; 0 2]);"
             " f = find(S);")
    assert _v(ws, "i").item() and not _v(ws, "j").item() and _v(ws, "n").item() == 2 and _v(ws, "m").item() == 2
    assert _v(ws, "z").tolist() == [[1], [2]] and not _v(ws, "k").item() and ws.get("c").text == "double"
    assert _v(ws, "s").tolist() == [[2, 2]] and _v(ws, "q").item() and _v(ws, "f").tolist() == [[1], [4]]


@pytest.mark.parametrize("expr,sparse", [
    ("S + S", True), ("S - S", True), ("S * S", True), ("S * 2", True), ("2 * S", True),
    ("S .* [1 2; 3 4]", True), ("[1 2; 3 4] .* S", True), ("S ./ 2", True), ("S .^ 2", True),
    ("S'", True), ("-S", True), ("S(1, :)", True), ("[S S]", True), ("[S; [1 1]]", True), ("S > 0", True),
    ("abs(S)", True), ("sqrt(S)", True), ("sum(S)", True), ("max(S)", True), ("round(S)", True),
    ("S ^ 2", True), ("S + 1", False), ("S * [1; 1]", False), ("[1 1] * S", False), ("exp(S)", False),
    ("full(S)", False), ("2 ./ S", False), ("S .^ 0", False),
])
def test_sparsity_propagation(expr, sparse):
    ws = _ws("S = sparse([1 0; 0 2]); r = " + expr + ";")
    assert _sp(ws, "r") is sparse, expr


def test_values_unchanged_by_sparsity():
    ws = _ws("S = sparse([1 0; 0 2]); a = S ^ 3; b = S + 1; c = S * [1; 1]; S(1, 2) = 5; d = S; e = issparse(S);")
    assert _v(ws, "a").tolist() == [[1, 0], [0, 8]] and _v(ws, "b").tolist() == [[2, 1], [1, 3]]
    assert _v(ws, "c").tolist() == [[1], [2]] and _v(ws, "d").tolist() == [[1, 5], [0, 2]] and _v(ws, "e").item()


def test_display():
    ws = _ws("S = sparse([1 0; 0 2.5]); Z = sparse(2, 3); L = sparse([true false true]); B = sparse([0 1 1e6]);")
    assert _format_value(ws.get("S")) == "   (1,1)    1.0000\n   (2,2)    2.5000"
    assert _format_value(ws.get("Z")) == "   All zero sparse: 2×3"
    assert _format_value(ws.get("L")) == "   (1,1)    1\n   (1,3)    1"
    assert _format_value(ws.get("B")) == "   (1,2)          1\n   (1,3)    1000000"


def test_errors():
    with pytest.raises(EvalError, match="for input arguments of type 'int8'"):
        _ws("x = sparse(int8(1));")
    with pytest.raises(EvalError, match="Vectors must be the same lengths"):
        _ws("x = sparse([1 2], [1 2 3], 1);")
    with pytest.raises(EvalError, match="Index into matrix must be positive"):
        _ws("x = sparse(0, 1, 1);")
    with pytest.raises(EvalError, match="Index exceeds matrix dimensions"):
        _ws("x = sparse(3, 1, 1, 2, 2);")
    with pytest.raises(EvalError, match="N-dimensional"):
        _ws("x = sparse(ones(2,2,2));")

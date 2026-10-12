"""N-D arrays (Epic #440: #74 #182 #330 #173 #259 #322) — MATLAB semantics."""

from __future__ import annotations

import io

import numpy as np
import pytest

from openmatlab.host.display import ConsoleDisplay
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


R = "A = reshape(1:8, 2, 2, 2);"


# --- constructors / shape queries (#182, #330) ---

@pytest.mark.parametrize("code", ["zeros(2,3,4)", "zeros([2 3 4])", "ones(2,3,4)", "nan(2,3,4)", "Inf([2 3 4])"])
def test_nd_constructors(code):
    ws = _ws(f"A = {code}; s = size(A); n = ndims(A);")
    assert _v(ws, "s").tolist() == [[2, 3, 4]] and _v(ws, "n").tolist() == [[3]]


def test_logical_nd_constructors():
    ws = _ws("t = true(2,2,3); f = false([1 2 2]); c = class(t); s = size(f);")
    assert _v(ws, "t").dtype == bool and _v(ws, "t").shape == (2, 2, 3) and _v(ws, "t").all()
    assert ws.get("c").text == "logical" and _v(ws, "s").tolist() == [[1, 2, 2]]


def test_trailing_singletons_dropped():
    ws = _ws("s = size(zeros(2,3,1)); n = ndims(ones(2,3,1,1)); k = size(zeros(2,3), 3);")
    assert _v(ws, "s").tolist() == [[2, 3]]
    assert _v(ws, "n").tolist() == [[2]] and _v(ws, "k").tolist() == [[1]]


def test_numel_length_isempty():
    ws = _ws("A = zeros(2,3,4); n = numel(A); l = length(A); e = isempty(zeros(2,0,3));")
    assert _v(ws, "n").tolist() == [[24]] and _v(ws, "l").tolist() == [[4]] and _v(ws, "e").all()


# --- indexing + end (#74, #173) ---

def test_three_subscript_read():
    ws = _ws(R + " x = A(2,1,2); p = A(:,:,2); k = A(7);")
    assert _v(ws, "x").tolist() == [[6]]
    assert _v(ws, "p").tolist() == [[5, 7], [6, 8]]
    assert _v(ws, "k").tolist() == [[7]]


def test_end_per_dimension():
    ws = _ws(R + " a = A(end,end,end); b = A(1,end); c = A(end); d = A(1,1,end);")
    assert [_v(ws, n).item() for n in "abcd"] == [8, 7, 8, 5]  # A(1,end) folds trailing dims


def test_fewer_subscripts_fold_trailing_dims():
    ws = _ws(R + " r = A(2,:);")
    assert _v(ws, "r").tolist() == [[2, 4, 6, 8]]


def test_slice_keeps_nd_shape_and_squeeze():
    ws = _ws(R + " B = A(:,1,:); s = size(B); q = size(squeeze(A(1,1,:)));")
    assert _v(ws, "s").tolist() == [[2, 1, 2]] and _v(ws, "q").tolist() == [[2, 1]]


def test_index_out_of_range_errors():
    with pytest.raises(Exception, match="exceeds"):
        _ws(R + " x = A(1,1,3);")


# --- assign + grow (#259) ---

def test_assign_page_and_scalar():
    ws = _ws(R + " A(:,:,2) = [10 20; 30 40]; A(1,1,1) = -1; p = A(:,:,2); x = A(1);")
    assert _v(ws, "p").tolist() == [[10, 20], [30, 40]] and _v(ws, "x").tolist() == [[-1]]


def test_grow_from_empty_and_from_2d():
    ws = _ws("A = []; A(2,2,2) = 1; s = size(A); B = ones(2); B(:,:,3) = 5; t = size(B); z = B(1,1,2);")
    assert _v(ws, "s").tolist() == [[2, 2, 2]] and _v(ws, "A").sum() == 1
    assert _v(ws, "t").tolist() == [[2, 2, 3]] and _v(ws, "z").tolist() == [[0]]


def test_assign_size_mismatch_message():
    with pytest.raises(EvalError, match="left side is 2-by-2-by-1 and the size of the right side is 1-by-3"):
        _ws(R + " A(:,:,2) = [1 2 3];")


def test_ambiguous_grow_errors():
    with pytest.raises(EvalError, match="ambiguous dimension"):
        _ws(R + " A(1,5) = 1;")


def test_delete_page():
    ws = _ws(R + " A(:,:,1) = []; s = size(A); B = reshape(1:8,2,2,2); B(:,1,:) = []; t = size(B);")
    assert _v(ws, "s").tolist() == [[2, 2]] and _v(ws, "A").tolist() == [[5, 7], [6, 8]]
    assert _v(ws, "t").tolist() == [[2, 1, 2]]


# --- logical indexing (#322) ---

def test_nd_logical_mask_read_write():
    ws = _ws(R + " x = A(A > 5); A(A > 6) = 0; y = A(:)';")
    assert _v(ws, "x").tolist() == [[6], [7], [8]]
    assert _v(ws, "y").tolist() == [[1, 2, 3, 4, 5, 6, 0, 0]]


# --- elementwise + reductions ---

def test_elementwise_and_scalar_ops():
    ws = _ws(R + " B = 2*A + A.*A; s = size(B); x = B(2,2,2);")
    assert _v(ws, "s").tolist() == [[2, 2, 2]] and _v(ws, "x").tolist() == [[80]]


def test_reductions_along_dim3_and_default():
    ws = _ws(R + " s3 = sum(A,3); m = max(A,[],3); mu = mean(A,3); s1 = sum(A); a = any(A>7,3);")
    assert _v(ws, "s3").tolist() == [[6, 10], [8, 12]]
    assert _v(ws, "m").tolist() == [[5, 7], [6, 8]]
    assert _v(ws, "mu").tolist() == [[3, 5], [4, 6]]
    assert _v(ws, "s1").shape == (1, 2, 2) and _v(ws, "s1").reshape(-1, order="F").tolist() == [3, 7, 11, 15]
    assert _v(ws, "a").tolist() == [[False, False], [False, True]]


def test_reshape_cat():
    ws = _ws(R + " B = reshape(A, 4, []); s = size(B); C = cat(3, [1 2], [3 4]); t = size(C); D = cat(1, [1 2], [3 4]);")
    assert _v(ws, "s").tolist() == [[4, 2]] and _v(ws, "B")[:, 1].tolist() == [5, 6, 7, 8]
    assert _v(ws, "t").tolist() == [[1, 2, 2]] and _v(ws, "D").tolist() == [[1, 2], [3, 4]]
    with pytest.raises(Exception, match="Number of elements must not change"):
        _ws(R + " B = reshape(A, 3, 3);")


def test_nd_matmul_and_transpose_error():
    with pytest.raises(Exception, match="Transpose on ND array"):
        _ws(R + " B = A';")
    with pytest.raises(Exception, match="Arguments must be 2-D"):
        _ws(R + " B = A*A;")


# --- display ---

def test_display_pages():
    s = Session.create_default()
    out = io.StringIO()
    from openmatlab.runtime.evaluator import Evaluator

    ev = Evaluator(workspace=s.workspace, functions=s.functions, numerics=s.numerics,
                   display=ConsoleDisplay(s.workspace, out))
    ev.eval_source("A = reshape(1:8, 2, 2, 2)")
    assert out.getvalue() == (
        "A(:,:,1) =\n\n   1   3\n   2   4\n\n"
        "A(:,:,2) =\n\n   5   7\n   6   8\n\n"
    )


def test_linear_grow_on_nd_is_ambiguous():
    with pytest.raises(EvalError, match="ambiguous dimension"):
        _ws(R + " A(9) = 1;")
    ws = _ws(R + " A(3) = 70; x = A(1,2,1); A(:,3) = []; s = size(A);")
    assert _v(ws, "x").tolist() == [[70]] and _v(ws, "s").tolist() == [[2, 3]]

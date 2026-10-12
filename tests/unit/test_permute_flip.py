"""permute/ipermute (#442); flip/fliplr/flipud/circshift and dim>=3 sort/cumsum (#445)."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]
R = "A = reshape(1:8, 2, 2, 2);"


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_permute_moves_dims():
    ws = _ws(R + " B = permute(A, [3 1 2]); s = size(B); x = B(2,1,1); P = permute(A, [2 1 3]); p = P(:,:,2);")
    assert _v(ws, "s").tolist() == [[2, 2, 2]] and _v(ws, "x").item() == 5
    assert _v(ws, "p").tolist() == [[5, 6], [7, 8]]


def test_permute_adds_trailing_dims_and_ipermute_roundtrips():
    ws = _ws(R + " r = permute([1 2 3], [2 1]); s = size(permute([1 2 3], [3 1 2])); B = ipermute(permute(A, [3 1 2]), [3 1 2]);")
    assert _v(ws, "r").tolist() == [[1], [2], [3]] and _v(ws, "s").tolist() == [[1, 1, 3]]
    assert np.array_equal(_v(ws, "B"), np.arange(1, 9).reshape(2, 2, 2, order="F"))


def test_permute_bad_order():
    with pytest.raises(EvalError, match="permutation"):
        _ws("B = permute([1 2], [1 1]);")


def test_flip_family():
    ws = _ws("f = flip([1 2 3]); g = flip([1; 2]); u = fliplr([1 2; 3 4]); d = flipud([1 2; 3 4]);" + R + " F = flip(A, 3); x = F(1,1,1);")
    assert _v(ws, "f").tolist() == [[3, 2, 1]] and _v(ws, "g").tolist() == [[2], [1]]
    assert _v(ws, "u").tolist() == [[2, 1], [4, 3]] and _v(ws, "d").tolist() == [[3, 4], [1, 2]]
    assert _v(ws, "x").item() == 5


def test_circshift():
    ws = _ws("c = circshift([1 2 3 4], 1); d = circshift([1 2; 3 4], 1); e = circshift([1 2; 3 4], 1, 2); "
             "f = circshift([1 2; 3 4], [1 1]); n = circshift([1 2 3], -1);" + R + " C = circshift(A, 1, 3); x = C(1,1,1);")
    assert _v(ws, "c").tolist() == [[4, 1, 2, 3]] and _v(ws, "d").tolist() == [[3, 4], [1, 2]]
    assert _v(ws, "e").tolist() == [[2, 1], [4, 3]] and _v(ws, "f").tolist() == [[4, 3], [2, 1]]
    assert _v(ws, "n").tolist() == [[2, 3, 1]] and _v(ws, "x").item() == 5


def test_sort_and_cumsum_along_dim3():
    ws = _ws(R + " S = sort(A, 3, 'descend'); x = S(1,1,1); Q = cumsum(A, 3); y = Q(1,1,2);")
    assert _v(ws, "x").item() == 5 and _v(ws, "y").item() == 6

"""Epic #535: array builders, sets and sorting."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


def test_repmat_numeric_char_nd():
    s = _run("a = repmat([1 2], 2, 2); b = repmat('ab', 1, 2); c = size(repmat(1, [2 3 4]));")
    assert _v(s, "a").tolist() == [[1, 2, 1, 2], [1, 2, 1, 2]]
    assert s.workspace.get("b").text == "abab"
    assert _v(s, "c").tolist() == [[2, 3, 4]]


def test_meshgrid_ndgrid_logspace():
    s = _run("[X, Y] = meshgrid(1:3, 1:2); [P, Q] = ndgrid(1:2, 1:3); L = logspace(0, 2, 3);")
    assert _v(s, "X").tolist() == [[1, 2, 3], [1, 2, 3]]
    assert _v(s, "P").tolist() == [[1, 1, 1], [2, 2, 2]]
    assert _v(s, "L").tolist() == [[1, 10, 100]]


def test_cell2mat_num2cell_iscellstr():
    s = _run("m = cell2mat({[1 2], 3; [4 5], 6}); t = iscellstr({'a', 1}); n = numel(num2cell([1 2 3]));")
    assert _v(s, "m").tolist() == [[1, 2, 3], [4, 5, 6]]
    assert not _v(s, "t").item() and _v(s, "n").item() == 3


def test_cell2mat_mixed_types_errors():
    with pytest.raises(Exception, match="same data type"):
        _run("m = cell2mat({'a', 1});")


def test_set_ops_numeric_with_indices():
    s = _run("[c, ia, ib] = intersect([5 1 3], [3 5 7]); u = union([3 1], [2 1]); x = setxor([1 2 3], [3 4]); d = setdiff([5;1;3], 1);")
    assert _v(s, "c").tolist() == [[3, 5]]
    assert _v(s, "ia").reshape(-1).tolist() == [3, 1]
    assert _v(s, "ib").reshape(-1).tolist() == [1, 2]
    assert _v(s, "u").tolist() == [[1, 2, 3]]
    assert _v(s, "x").tolist() == [[1, 2, 4]]
    assert _v(s, "d").reshape(-1).tolist() == [3, 5] and _v(s, "d").shape == (2, 1)


def test_set_ops_keep_integer_class_and_nan_distinct():
    s = _run("i = intersect(int8([1 2]), [2 3]); k = class(i); u = union([NaN 1], NaN);")
    assert s.workspace.get("k").text == "int8"
    assert np.isnan(_v(s, "u")).sum() == 2


def test_ismember_cellstr_and_char():
    s = _run("[tf, loc] = ismember({'a', 'q'}, {'q', 'a', 'a'}); b = ismember('b', {'a', 'b'}); [t2, l2] = ismember([1 5 2], [2 1 1 9]);")
    assert _v(s, "loc").tolist() == [[2, 1]]
    assert _v(s, "b").item()
    assert _v(s, "l2").tolist() == [[2, 0, 1]]


def test_unique_cellstr_stable_last():
    s = _run("[c, i, j] = unique({'z', 'y', 'z'}); n = numel(c); s = unique([3 1 2 3], 'stable'); [~, il] = unique([1 1 2], 'last');")
    assert _v(s, "j").reshape(-1).tolist() == [2, 1, 2]
    assert _v(s, "s").tolist() == [[3, 1, 2]]
    assert _v(s, "il").reshape(-1).tolist() == [2, 3]


def test_sortrows_specs():
    s = _run("a = sortrows([1 2; 1 1; 0 5], -2); [b, i] = sortrows([2 1; 1 3; 2 0]); c = sortrows([1 NaN; 1 2; 0 5], -2);")
    assert _v(s, "a").tolist() == [[0, 5], [1, 2], [1, 1]]
    assert _v(s, "i").reshape(-1).tolist() == [2, 3, 1]
    assert np.isnan(_v(s, "c")[0, 1])


def test_sortrows_bad_column_errors():
    with pytest.raises(Exception, match="Column sorting vector"):
        _run("a = sortrows([1 2], 3);")


def test_sub2ind_ind2sub_round_trip_and_range():
    s = _run("k = sub2ind([3 4], [1 3], [2 4]); [r, c] = ind2sub([3 4], k);")
    assert _v(s, "k").tolist() == [[4, 12]]
    assert _v(s, "r").tolist() == [[1, 3]] and _v(s, "c").tolist() == [[2, 4]]
    with pytest.raises(Exception, match="Out of range"):
        _run("k = sub2ind([2 2], 3, 1);")


def test_isequaln_treats_nan_equal():
    s = _run("a = isequaln([1 NaN], [1 NaN]); b = isequal([1 NaN], [1 NaN]);")
    assert _v(s, "a").item() and not _v(s, "b").item()


def test_tilde_output_placeholder_discards():
    s = _run("[~, i] = max([1 3]); [a, ~] = size(ones(2, 5)); x = [~1, 0];")
    assert _v(s, "i").item() == 2 and _v(s, "a").item() == 2
    assert "~" not in s.workspace.names()
    assert _v(s, "x").tolist() == [[0, 0]]

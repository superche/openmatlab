"""Matrix concatenation of non-scalars, char, cell and logical (Issue #422)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _x(code: str):
    s = Session.create_default()
    ReplSession(s).run_line(code + ";")
    return s.workspace.get("x")


def _arr(code: str):
    return np.asarray(_x(code).backend_buffer())


def test_horzcat_and_vertcat_arrays():
    assert _arr("x = [[1 2] 3]").tolist() == [[1, 2, 3]]
    assert _arr("a = [1 2]; x = [a; a]").tolist() == [[1, 2], [1, 2]]
    assert _arr("x = [[1; 2] [3; 4]]").tolist() == [[1, 3], [2, 4]]
    assert _arr("a = [1 2]; x = [a' a']").tolist() == [[1, 1], [2, 2]]


def test_empty_is_ignored():
    assert _arr("x = [[] 1 2]").tolist() == [[1, 2]]
    assert _arr("x = [1 2; []]").tolist() == [[1, 2]]
    assert _arr("x = []").shape == (0, 0)


def test_inconsistent_dimensions_error():
    with pytest.raises(EvalError, match="not consistent"):
        _x("x = [1 2; 3]")
    with pytest.raises(EvalError, match="not consistent"):
        _x("x = [[1; 2] 3]")


def test_all_logical_literal_stays_logical():
    assert _arr("x = [true false]").dtype == np.bool_
    assert _arr("x = [true 2]").dtype == np.float64


def test_char_concat():
    assert _x("x = ['ab' 'cd']") == CharValue("abcd")
    assert _x("x = ['ab', 'cd']") == CharValue("abcd")
    assert _x("x = ['a' 66]") == CharValue("aB")


def test_cell_concat():
    x = _x("c = {1}; x = [c {2}]")
    assert isinstance(x, CellValue) and x.shape == (1, 2)
    assert _x("c = {1}; x = [c; {2}]").shape == (2, 1)
    assert _x("c = {1}; x = [c 2]").shape == (1, 2)


def test_whitespace_paren_starts_new_element():
    assert _arr("a = [5 6]; x = [a (1)]").tolist() == [[5, 6, 1]]
    assert _arr("a = [5 6]; x = [a(1) 2]").tolist() == [[5, 2]]


def test_csl_expansion_with_nonscalars():
    assert _arr("c = {[1 2], 3}; x = [c{:}]").tolist() == [[1, 2, 3]]

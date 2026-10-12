"""sort for char arrays and cellstr (Issue #198)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace.get


def _texts(c: CellValue):
    r, k = c.shape
    return [c.get(i, j).text for j in range(k) for i in range(r)], c.shape


def test_sort_char_by_code():
    get = _ws("s = sort('hello'); [t, i] = sort('cab'); d = sort('hello', 'descend');")
    assert isinstance(get("s"), CharValue) and get("s").text == "ehllo"
    assert get("t").text == "abc"
    assert np.asarray(get("i").backend_buffer()).tolist() == [[2, 3, 1]]
    assert get("d").text == "ollhe"


def test_sort_cellstr_ascii_order_keeps_orientation():
    get = _ws("c = sort({'pear', 'apple', 'Banana'}); [r, i] = sort({'b'; 'a'; 'c'});")
    assert _texts(get("c")) == (["Banana", "apple", "pear"], (1, 3))  # uppercase first (ASCII)
    assert _texts(get("r")) == (["a", "b", "c"], (3, 1))
    assert np.asarray(get("i").backend_buffer()).reshape(-1).tolist() == [2, 1, 3]


def test_sort_cellstr_descend_is_stable():
    get = _ws("[c, i] = sort({'b', 'a', 'b'}, 'descend');")
    assert _texts(get("c"))[0] == ["b", "b", "a"]
    assert np.asarray(get("i").backend_buffer()).reshape(-1).tolist() == [1, 3, 2]


def test_sort_mixed_cell_errors():
    with pytest.raises(Exception, match="only char vectors"):
        _ws("c = sort({1, 'a'});")

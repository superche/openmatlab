"""[a -b] element separation inside matrix literals — bug found during #46."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _g(code: str) -> np.ndarray:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get("y").backend_buffer())


def test_space_minus_starts_element():
    assert np.array_equal(_g("y = [1.5 -1.5];"), [[1.5, -1.5]])
    assert np.array_equal(_g("y = [1 +2];"), [[1, 2]])


def test_binary_forms_still_subtract():
    assert np.array_equal(_g("y = [3 - 1];"), [[2]])
    assert np.array_equal(_g("y = [3-1];"), [[2]])


def test_parens_inside_brackets_stay_binary():
    assert np.array_equal(_g("y = [(3 -1) 4];"), [[2, 4]])


def test_after_name_and_in_rows():
    assert np.array_equal(_g("a = 5; y = [a -1; 2 -3];"), [[5, -1], [2, -3]])


def test_outside_brackets_unchanged():
    assert np.array_equal(_g("y = 3 -1;"), [[2]])

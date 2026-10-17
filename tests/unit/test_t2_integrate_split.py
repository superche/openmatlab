"""trapz / cumtrapz argument forms and strsplit name-value prefixes (C-E5 #765 T2): own examples."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession

pytestmark = [pytest.mark.unit]


def ev(code, name="r"):
    s = ReplSession()
    s.run_line(code)
    return s.session.workspace.get(name)


def num(code):
    return np.asarray(ev(code).backend_buffer())


@pytest.mark.parametrize("code,want", [
    ("r = trapz(2, [1 3 5]);", [[12.0]]),
    ("r = trapz([0 1 3], [2 2 2]');", [[6.0]]),
    ("r = trapz([1 2; 3 4], 2);", [[1.5], [3.5]]),
    ("r = trapz([0 1; 0 2], [1 1; 3 3], 2);", [[1.0], [6.0]]),
    ("r = trapz(ones(2, 1), 2);", [[0.0], [0.0]]),
    ("r = trapz(reshape(1:4, 1, 1, 4), 3);", [[7.5]]),
    ("r = cumtrapz(0.5, [1 3 5]);", [[0, 1, 3]]),
    ("r = cumtrapz([0 2], [1 1; 2 2], 1);", [[0, 0], [3, 3]]),
])
def test_trapz_forms(code, want):
    np.testing.assert_allclose(num(code), want)


def test_strsplit_name_value_prefixes():
    c = ev("r = strsplit('a1b22c', '\\d', 'DelimiterType', 'R');")
    assert [c.get(0, j).text for j in range(c.shape[1])] == ["a", "b", "c"]
    c = ev("r = strsplit('a,,b', ',', 'collapse', false);")
    assert [c.get(0, j).text for j in range(c.shape[1])] == ["a", "", "b"]

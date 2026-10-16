"""#870: cell2mat ignores 1x0 / 0x1 empty pieces like [a, b] does."""

import numpy as np

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session


def _val(code, name):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_column_empty_in_a_row():
    assert _val("x = cell2mat({zeros(0,1), 5});", "x").tolist() == [[5.0]]


def test_row_empty_in_a_column():
    assert _val("x = cell2mat({zeros(1,0); 5});", "x").tolist() == [[5.0]]


def test_all_empty_keeps_shape():
    assert _val("x = cell2mat({zeros(0,3); zeros(0,3)});", "x").shape == (0, 3)

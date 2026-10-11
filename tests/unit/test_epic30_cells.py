"""Epic #30 cell paren slices/grow (Issues #110 #290 #260 #258)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_paren_slice_and_grow_and_multi_assign():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2, 3}; d = c(1:2);")
    assert s.workspace.get("d").shape == (2, 1)
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2}; c(4) = {9};")
    assert s.workspace.get("c").shape == (1, 4)
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2, 3}; c(1:2) = {8, 9};")
    assert float(np.asarray(s.workspace.get("c").get(0, 0).backend_buffer()).reshape(-1)[0]) == 8
    s = Session.create_default()
    ReplSession(s).run_line("A = zeros(2); A(5) = 1;")
    assert np.asarray(s.workspace.get("A").backend_buffer()).shape == (5, 1)

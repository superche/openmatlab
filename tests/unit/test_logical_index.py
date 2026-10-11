"""Logical indexing read + assign (Issue #234)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str, name: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace.get(name)


def test_relational_is_logical():
    L = _run("v = [1 2]; L = v > 1;", "L")
    assert L.matlab_class() == "logical"
    assert list(np.asarray(L.backend_buffer()).reshape(-1)) == [False, True]


def test_read_and_assign():
    s = Session.create_default()
    ReplSession(s).run_line("v = [5 -1 3 -2]; p = v(v > 0); v(v < 0) = 0;")
    assert np.asarray(s.workspace.get("p").backend_buffer()).tolist() == [[5.0, 3.0]]
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [[5.0, 0.0, 3.0, 0.0]]


def test_c07_script():
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c07_logical_indexing.m");')
    assert np.asarray(s.workspace.get("p").backend_buffer()).tolist() == [[5.0, 3.0]]
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [[5.0, 0.0, 3.0, 0.0]]

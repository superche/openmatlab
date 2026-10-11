"""unique / issorted builtins (Issue #266)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_unique_row_c09():
    s = Session.create_default()
    ReplSession(s).run_line("u = unique([3 1 3 2]);")
    assert np.asarray(s.workspace.get("u").backend_buffer()).tolist() == [
        [1.0, 2.0, 3.0]
    ]
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c09_unique_issorted.m");')
    assert float(np.asarray(s.workspace.get("t").backend_buffer()).reshape(-1)[0]) == 1


def test_unique_column():
    s = Session.create_default()
    ReplSession(s).run_line("u = unique([3; 1; 3; 2]);")
    assert np.asarray(s.workspace.get("u").backend_buffer()).tolist() == [
        [1.0],
        [2.0],
        [3.0],
    ]


def test_issorted_false():
    s = Session.create_default()
    ReplSession(s).run_line("t = issorted([1 3 2]);")
    assert float(np.asarray(s.workspace.get("t").backend_buffer()).reshape(-1)[0]) == 0
    assert s.workspace.get("t").matlab_class() == "logical"


def test_issorted_empty():
    s = Session.create_default()
    ReplSession(s).run_line("t = issorted([]);")
    assert float(np.asarray(s.workspace.get("t").backend_buffer()).reshape(-1)[0]) == 1

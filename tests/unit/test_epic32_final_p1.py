"""Epic #32 final p1: script, char arith, i/j, CSL (#142 #83 #218 #80)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_final_p1_batch():
    s = Session.create_default()
    ReplSession(s).run_line("y = 1 + i; x = 'A' + 1; c = {1, 2, 3}; v = [c{:}];")
    assert np.isclose(complex(s.workspace.get("y").backend_buffer().reshape(-1)[0]), 1 + 1j)
    assert np.asarray(s.workspace.get("x").backend_buffer()).tolist() == [[66.0]]
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [[1.0, 2.0, 3.0]]
    td = tempfile.mkdtemp()
    Path(td, "hi.m").write_text("z = 42;\n")
    s = Session.create_default()
    ReplSession(s).run_line(f'addpath("{td}"); hi;')
    assert float(np.asarray(s.workspace.get("z").backend_buffer()).reshape(-1)[0]) == 42

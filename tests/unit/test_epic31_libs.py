"""Epic #31 libs batch (#269 #271 #69 #279)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_unique_indices_issorted_omitnan_cellfun_uo():
    s = Session.create_default()
    ReplSession(s).run_line("[u, ia, ic] = unique([3 1 3 2]);")
    assert np.asarray(s.workspace.get("u").backend_buffer()).tolist() == [[1.0, 2.0, 3.0]]
    s = Session.create_default()
    ReplSession(s).run_line("t = issorted([3 2 1], 'descend');")
    assert float(np.asarray(s.workspace.get("t").backend_buffer()).reshape(-1)[0]) == 1
    s = Session.create_default()
    ReplSession(s).run_line("m = max([1 NaN 3], 'includenan'); s = sum([1 2; 3 4], 'all');")
    assert np.isnan(float(np.asarray(s.workspace.get("m").backend_buffer()).reshape(-1)[0]))
    assert float(np.asarray(s.workspace.get("s").backend_buffer()).reshape(-1)[0]) == 10
    s = Session.create_default()
    ReplSession(s).run_line("c = {[1 2], [3]}; r = cellfun(@sum, c, 'UniformOutput', false);")
    assert s.workspace.get("r").matlab_class() == "cell" and s.workspace.get("r").shape == (1, 2)

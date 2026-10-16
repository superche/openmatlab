"""G-E4 #771: Axes ALim / ALimMode are documented properties (stored, defaults)."""

import numpy as np

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session


def test_axes_alim_default_and_set():
    s = Session.create_default()
    ReplSession(s).run_line("ax = axes; a0 = get(ax, 'ALim'); m = get(ax, 'ALimMode'); set(ax, 'ALim', [0 2]); a1 = ax.ALim;")
    assert np.asarray(s.workspace.get("a0").backend_buffer()).tolist() == [[0.0, 1.0]]
    assert np.asarray(s.workspace.get("a1").backend_buffer()).tolist() == [[0.0, 2.0]]
    assert s.workspace.get("m").text == "auto"

"""NaN/Inf scalar display (surfaced while refreshing EPIC-004)."""

from __future__ import annotations

import pytest

from openmatlab.host.display import _format_value
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_nan_and_inf_format():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("a = nan(); b = 1/0; c = -1/0;")
    assert _format_value(s.workspace.get("a")) == "NaN"
    assert _format_value(s.workspace.get("b")) == "Inf"
    assert _format_value(s.workspace.get("c")) == "-Inf"

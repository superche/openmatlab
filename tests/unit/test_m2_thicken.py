"""Thicker M2 conformance scripts (Issue #297)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

from conformance.m2_expected import assert_close, coerce_expected

pytestmark = [pytest.mark.unit, pytest.mark.conformance, pytest.mark.needs_numpy]

SCRIPTS = Path(__file__).resolve().parents[1] / "conformance" / "scripts"


@pytest.mark.parametrize(
    "script",
    [
        "c04_numeric_builtins",
        "c06_delete_elements",
        "c08_grow_on_assign",
        "c10_cellfun",
    ],
)
def test_thickened_script(script: str):
    expected = json.loads((SCRIPTS / f"{script}.expected.json").read_text())
    s = Session.create_default()
    ReplSession(s).run_line(f'run("{SCRIPTS / (script + ".m")}");')
    for name, want in expected.items():
        got = np.asarray(s.workspace.get(name).backend_buffer(), dtype=float)
        want_a = np.asarray(coerce_expected(want), dtype=float)
        assert_close(got, want_a, label=f"{script}.{name}")


def test_coerce_specials():
    assert coerce_expected("Inf") == np.inf
    assert coerce_expected("-Inf") == -np.inf
    assert np.isnan(coerce_expected("NaN"))

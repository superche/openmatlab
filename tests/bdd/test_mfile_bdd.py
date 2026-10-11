from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]

scenarios("../../features/mfile_functions.feature")


@pytest.fixture
def ctx(tmp_path: Path):
    return {"session": Session.create_default(), "tmp": tmp_path}


@given(parsers.parse('a session with path fixture "{name}"'))
def session_with_fixture(ctx, name: str):
    tmp: Path = ctx["tmp"]
    if name == "add2":
        (tmp / "add2.m").write_text(
            "function y = add2(a, b)\ny = a + b;\nend\n"
        )
    ctx["session"].path.addpath(tmp)


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals {value:d}'))
def var_equals(ctx, name, value):
    v = ctx["session"].workspace.get(name)
    assert float(v.backend_buffer().reshape(-1)[0]) == float(value)

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]

scenarios("../../features/run_script.feature")


@pytest.fixture
def ctx(tmp_path: Path):
    return {"session": Session.create_default(), "tmp": tmp_path, "file": None}


@given("a session with script file on disk")
def make(ctx):
    f = ctx["tmp"] / "k.m"
    f.write_text("k = 9;\n")
    ctx["file"] = f


@when("I run that script via language run")
def do_run(ctx):
    ReplSession(ctx["session"]).run_line(f'run("{ctx["file"]}")')


@then(parsers.parse('variable "{name}" equals {value:d}'))
def var_eq(ctx, name, value):
    v = ctx["session"].workspace.get(name)
    assert float(v.backend_buffer().reshape(-1)[0]) == float(value)

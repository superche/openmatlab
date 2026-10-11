from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/return_stmt.feature")


@pytest.fixture
def ctx(tmp_path: Path):
    (tmp_path / "early.m").write_text(
        "function y = early(x)\ny = x + 1;\nreturn;\ny = 999;\nend\n"
    )
    s = Session.create_default()
    ReplSession(s).run_line(f'addpath("{tmp_path}");')
    return {"session": s}


@given("a fresh session with early.m on path")
def fresh(ctx):
    pass


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals {value:d}'))
def var_eq(ctx, name, value):
    v = ctx["session"].workspace.get(name)
    assert float(v.backend_buffer().reshape(-1)[0]) == float(value)

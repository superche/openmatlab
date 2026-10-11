from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]

scenarios("../../features/multi_assign.feature")


@pytest.fixture
def ctx(tmp_path: Path):
    return {"session": Session.create_default(), "tmp": tmp_path}


@given("a temp toolbox with swap.m")
def toolbox(ctx):
    (ctx["tmp"] / "swap.m").write_text(
        "function [a, b] = swap(x, y)\na = y;\nb = x;\nend\n"
    )


@when("I addpath that toolbox")
def do_addpath(ctx):
    ReplSession(ctx["session"]).run_line(f'addpath("{ctx["tmp"]}")')


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals {value:d}'))
def var_eq(ctx, name, value):
    v = ctx["session"].workspace.get(name)
    assert float(v.backend_buffer().reshape(-1)[0]) == float(value)

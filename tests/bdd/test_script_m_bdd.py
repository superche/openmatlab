from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.runtime.evaluator import Evaluator
from openmatlab.runtime.functions import Script, eval_script, load_mfile
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]

scenarios("../../features/script_m.feature")


@pytest.fixture
def ctx(tmp_path: Path):
    return {"session": Session.create_default(), "tmp": tmp_path, "script": None}


@given("a session and script file setting a and b")
def make_script(ctx):
    f = ctx["tmp"] / "init.m"
    f.write_text("a = 10;\nb = a + 5;\n")
    ctx["script"] = load_mfile(f)


@when("I evaluate that script")
def do_eval(ctx):
    s = ctx["session"]
    s.functions.bind_runtime(s.numerics, s.plots)
    ev = Evaluator(
        workspace=s.workspace,
        functions=s.functions,
        numerics=s.numerics,
        plots=s.plots,
    )
    assert isinstance(ctx["script"], Script)
    eval_script(ctx["script"], ev)


@then(parsers.parse('variable "{name}" equals {value:d}'))
def var_eq(ctx, name, value):
    v = ctx["session"].workspace.get(name)
    assert float(v.backend_buffer().reshape(-1)[0]) == float(value)

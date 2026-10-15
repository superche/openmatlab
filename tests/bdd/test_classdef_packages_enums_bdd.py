from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/classdef_packages_enums.feature")


@pytest.fixture
def ctx(tmp_path):
    s = Session.create_default()
    ReplSession(s).run_line(f"addpath('{tmp_path.as_posix()}');")
    return {"session": s, "dir": tmp_path}


@given(parsers.parse('a class file "{name}" with'), target_fixture="ctx")
def class_file(ctx, name, docstring):
    p = ctx["dir"] / f"{name}.m"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(docstring)
    return ctx


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(x.strip()) for x in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert list(got) == expected

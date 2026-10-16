from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.bdd, pytest.mark.unit]
scenarios("../../features/workbench_output_routing.feature")


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse('a workbench with a script "{name}" containing "{code}"'))
def wb(ctx, tmp_path, name, code):
    (tmp_path / name).write_text(code.replace("\\n", "\\n") + "\n")
    ctx["tmp"] = tmp_path
    ctx["wb"] = Workbench.create(cwd=tmp_path)


@when(parsers.parse('I run "{name}" from the editor'))
def run(ctx, name):
    ctx["wb"].run_file(ctx["tmp"] / name)


@then(parsers.parse('the Command Window shows "{text}"'))
def shows(ctx, text):
    assert text in ctx["wb"].command_window.text()

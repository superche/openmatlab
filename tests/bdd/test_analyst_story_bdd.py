"""Gherkin for the analyst field-assay story (issue #1034)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/analyst_story.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh analyst-story session")
def fresh(ctx):
    pass


@when("I run the analyst story")
def run_story(ctx):
    story = (repo_root() / "demos" / "analyst" / "story_assays.m").as_posix()
    ReplSession(ctx["session"]).run_line(
        f"run('{story}'); v = [S.GroupCount' S.mean_moisture_pct' S.mean_temp_c'];"
    )


@then(parsers.parse('"{name}" is close to [{vals}]'))
def close_to(ctx, name, vals):
    expected = np.array([float(x.strip()) for x in vals.split(",")], float)
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer(), float).reshape(-1)
    assert got.shape == expected.shape
    assert np.allclose(got, expected, equal_nan=True)

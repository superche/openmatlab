"""BDD smoke for architecture seams (pytest-bdd)."""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, then, when

from openmatlab.qa.feature_map import load_feature_map
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit]

scenarios("../../features/architecture_seams.feature")


@given("a default OpenMATLAB session", target_fixture="session")
def default_session():
    return Session.create_default()


@then("the session has a workspace")
def session_has_workspace(session: Session):
    assert session.workspace.depth() >= 1


@then("the session function resolver uses the toolbox path")
def session_resolver_path(session: Session):
    assert session.functions.path is session.path


@when("the feature map is loaded", target_fixture="feature_map")
def feature_map_loaded():
    return load_feature_map()


@then("it contains a runtime session feature")
def has_runtime_session(feature_map):
    ids = {f.id for f in feature_map.features}
    assert "runtime.session" in ids


@then("all feature ids are unique")
def unique_ids(feature_map):
    ids = [f.id for f in feature_map.features]
    assert len(ids) == len(set(ids))

"""BDD smoke for QA catalog (pytest-bdd)."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, then, when

from openmatlab.qa.catalog import load_test_catalog

pytestmark = [pytest.mark.bdd, pytest.mark.unit]

scenarios("../../features/qa_process.feature")


@when("the test catalog is loaded", target_fixture="catalog")
def catalog_loaded():
    return load_test_catalog()


@then("there is at least one active unit test case")
def active_unit_cases(catalog):
    active = catalog.filter(kind="unit", status="active")
    assert len(active) >= 1

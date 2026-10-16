"""Tables and data types (docs/milestones/M10-tables.md) conformance suite."""

from __future__ import annotations

import pytest

from ._ms_harness import check_manifest, params, run_and_check
from .m10_manifest import CRITERIA

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.mark.parametrize("cid,script", params(CRITERIA))
def test_m10_criterion(cid: str, script: str):
    run_and_check(cid, script, plugin=False)


def test_m10_manifest_scripts_exist():
    check_manifest(CRITERIA)

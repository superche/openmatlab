"""Domain toolboxes (docs/milestones/M3-domain-toolboxes.md) conformance suite."""

from __future__ import annotations

import pytest

from ._ms_harness import check_manifest, params, run_and_check
from .m3_manifest import CRITERIA, PLUGIN_SCRIPTS

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.mark.parametrize("cid,script", params(CRITERIA))
def test_m3_criterion(cid: str, script: str):
    run_and_check(cid, script, plugin=script in PLUGIN_SCRIPTS)


def test_m3_manifest_scripts_exist():
    check_manifest(CRITERIA)

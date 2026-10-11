"""Conformance suite placeholder — fill when parser + Array exist."""

import pytest

pytestmark = pytest.mark.conformance


def test_conformance_suite_ready_for_goldens():
    """Documents that golden/ and fixtures/ exist for future cases."""
    from pathlib import Path

    root = Path(__file__).resolve().parent
    assert (root / "golden").is_dir()

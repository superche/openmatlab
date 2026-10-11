"""Pytest markers and shared fixtures for OpenMATLAB QA layout."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: fast unit / architecture tests")
    config.addinivalue_line("markers", "bdd: Gherkin / pytest-bdd scenarios")
    config.addinivalue_line(
        "markers",
        "conformance: golden / public-spec language-runtime cases",
    )
    config.addinivalue_line(
        "markers",
        "interactive: REPL/plot smoke (may need display; skip in default CI)",
    )
    config.addinivalue_line("markers", "slow: long-running tests")
    config.addinivalue_line("markers", "needs_numpy: requires NumPy")
    config.addinivalue_line(
        "markers", "needs_matplotlib: requires Matplotlib"
    )


@pytest.fixture
def feature_map():
    from openmatlab.qa.feature_map import load_feature_map

    return load_feature_map()

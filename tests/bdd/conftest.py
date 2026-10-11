"""Shared fixtures for Gherkin / pytest-bdd scenarios."""

from __future__ import annotations

import pytest


@pytest.fixture
def session():
    from openmatlab.runtime.session import Session

    return Session.create_default()

"""P08: engines.openmatlab SemVer range enforcement."""

from __future__ import annotations

import pytest

from openmatlab.extensions.engines import (
    EngineRangeError,
    check_compatible,
    satisfies,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "spec,host,ok",
    [
        (">=0.1.0 <0.2.0", "0.1.0", True),
        (">=0.1.0 <0.2.0", "0.1.9", True),
        (">=0.1.0 <0.2.0", "0.2.0", False),
        (">=0.1.0 <0.2.0", "0.0.9", False),
        ("0.1.0", "0.1.0", True),
        ("0.1.0", "0.1.1", False),
        (">=0.1.0", "9.0.0", True),
        ("<0.1.0", "0.1.0", False),
    ],
)
def test_satisfies(spec, host, ok):
    assert satisfies(spec, host) is ok


def test_check_compatible_raises():
    with pytest.raises(EngineRangeError, match="requires"):
        check_compatible(">=0.2.0", "0.1.0")


def test_invalid_clause():
    with pytest.raises(EngineRangeError):
        satisfies("!!!", "0.1.0")

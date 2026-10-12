"""CLI openmatlab desktop — list-only path (no window)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.host.cli import main

pytestmark = pytest.mark.unit

SAMPLE = Path("demos/plugins/community.signal")


def test_desktop_list_only(capsys):
    with pytest.raises(SystemExit) as ei:
        main(
            [
                "desktop",
                "--path",
                str(SAMPLE),
                "--list-only",
            ]
        )
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "community.signal.panel" in out
    assert "Signal" in out

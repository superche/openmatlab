"""P07: CLI openmatlab plugins."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.host.cli import main

pytestmark = pytest.mark.unit

SAMPLE = Path("demos/plugins/community.signal")


def test_plugins_list(capsys):
    with pytest.raises(SystemExit) as ei:
        main(
            [
                "plugins",
                "--path",
                str(SAMPLE),
                "--no-user-dir",
                "--no-entry-points",
            ]
        )
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "community.signal" in out
    assert "0.1.0" in out


def test_plugins_activate(capsys):
    with pytest.raises(SystemExit) as ei:
        main(
            [
                "plugins",
                "--path",
                str(SAMPLE),
                "--no-user-dir",
                "--no-entry-points",
                "--activate",
            ]
        )
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "active" in out


def test_plugins_yaml(capsys):
    with pytest.raises(SystemExit) as ei:
        main(
            [
                "plugins",
                "--path",
                str(SAMPLE),
                "--no-user-dir",
                "--no-entry-points",
                "--format",
                "yaml",
            ]
        )
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "community.signal" in out

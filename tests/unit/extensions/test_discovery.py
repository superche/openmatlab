"""P06: Discovery — path + entry points."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openmatlab.extensions.discovery import (
    discover_all,
    discover_from_paths,
    discover_in_root,
)
from openmatlab.extensions.manifest import load_manifest

pytestmark = pytest.mark.unit

SAMPLE = Path("demos/plugins/community.signal")


def test_discover_sample_folder():
    found = discover_in_root(SAMPLE)
    assert len(found) == 1
    assert found[0].id == "community.signal"


def test_discover_parent_with_children(tmp_path: Path):
    a = tmp_path / "a"
    a.mkdir()
    (a / "plugin.yaml").write_text(
        """
id: community.a
version: 0.1.0
engines:
  openmatlab: ">=0.1.0"
main: e.py
""",
        encoding="utf-8",
    )
    (a / "e.py").write_text("def activate(c): pass\n", encoding="utf-8")
    b = tmp_path / "b"
    b.mkdir()
    (b / "openmatlab.plugin.json").write_text(
        json.dumps(
            {
                "id": "community.b",
                "version": "0.1.0",
                "engines": {"openmatlab": ">=0.1.0"},
                "main": "e.py",
            }
        ),
        encoding="utf-8",
    )
    (b / "e.py").write_text("def activate(c): pass\n", encoding="utf-8")
    manifs, warns = discover_from_paths([tmp_path])
    ids = {m.id for m in manifs}
    assert ids == {"community.a", "community.b"}
    assert warns == []


def test_duplicate_id_warns(tmp_path: Path):
    for name in ("one", "two"):
        d = tmp_path / name
        d.mkdir()
        (d / "plugin.yaml").write_text(
            """
id: community.dup
version: 0.1.0
engines:
  openmatlab: ">=0.1.0"
main: e.py
""",
            encoding="utf-8",
        )
        (d / "e.py").write_text("def activate(c): pass\n", encoding="utf-8")
    with pytest.warns(UserWarning, match="duplicate"):
        manifs, warns = discover_from_paths([tmp_path])
    assert len(manifs) == 1
    assert any("duplicate" in w for w in warns)


def test_env_plugin_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    plug = tmp_path / "envplug"
    plug.mkdir()
    (plug / "plugin.yaml").write_text(
        """
id: community.env
version: 0.1.0
engines:
  openmatlab: ">=0.1.0"
main: e.py
""",
        encoding="utf-8",
    )
    (plug / "e.py").write_text("def activate(c): pass\n", encoding="utf-8")
    monkeypatch.setenv("OPENMATLAB_PLUGIN_PATH", str(plug))
    manifs, _ = discover_all(include_user_dir=False, include_entry_points=False)
    assert any(m.id == "community.env" for m in manifs)


def test_entry_points_optional(monkeypatch: pytest.MonkeyPatch):
    # Smoke: calling discover_entry_points / discover_all should not crash
    manifs, warns = discover_all(
        extra=[SAMPLE],
        include_user_dir=False,
        include_entry_points=True,
    )
    assert any(m.id == "community.signal" for m in manifs)

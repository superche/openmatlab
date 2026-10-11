"""P02: Manifest load/validate + schema tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openmatlab.extensions.manifest import (
    ManifestError,
    load_manifest,
    load_manifest_file,
    validate_raw,
)

pytestmark = pytest.mark.unit


def _write_yaml(tmp: Path, text: str) -> Path:
    root = tmp / "plug"
    root.mkdir()
    path = root / "plugin.yaml"
    path.write_text(text, encoding="utf-8")
    return root


def test_valid_yaml_manifest(tmp_path: Path):
    root = _write_yaml(
        tmp_path,
        """
id: community.demo
version: 1.2.3
displayName: Demo
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onStartupFinished
contributes:
  commands:
    - command: community.demo.run
      title: Run
""",
    )
    (root / "extension.py").write_text("def activate(c): pass\n", encoding="utf-8")
    m = load_manifest(root)
    assert m.id == "community.demo"
    assert m.version == "1.2.3"
    assert m.engines_openmatlab == ">=0.1.0 <0.2.0"
    assert m.main == "extension.py"
    assert m.activation == ["onStartupFinished"]
    assert m.contributes["commands"][0]["command"] == "community.demo.run"
    assert m.warnings == []


def test_valid_json_manifest(tmp_path: Path):
    root = tmp_path / "j"
    root.mkdir()
    data = {
        "id": "pub.jsonplug",
        "version": "0.0.1",
        "engines": {"openmatlab": "0.1.0"},
        "main": "main.py",
        "contributes": {"menus": [{"path": "Tools/X", "command": "x"}]},
    }
    (root / "openmatlab.plugin.json").write_text(json.dumps(data), encoding="utf-8")
    (root / "main.py").write_text("def activate(c): pass\n", encoding="utf-8")
    m = load_manifest(root)
    assert m.id == "pub.jsonplug"
    assert m.contributes["menus"]


def test_missing_id_fails(tmp_path: Path):
    with pytest.raises(ManifestError, match="id"):
        validate_raw(
            {
                "version": "1.0.0",
                "engines": {"openmatlab": ">=0.1.0"},
                "main": "x.py",
            },
            root=tmp_path,
        )


def test_missing_engines_fails(tmp_path: Path):
    with pytest.raises(ManifestError, match="engines"):
        validate_raw(
            {"id": "a", "version": "1.0.0", "main": "x.py"},
            root=tmp_path,
        )


def test_unknown_contributes_key_warns(tmp_path: Path):
    m = validate_raw(
        {
            "id": "a.b",
            "version": "1.0.0",
            "engines": {"openmatlab": ">=0.1.0"},
            "main": "x.py",
            "contributes": {"notARealSlot": []},
        },
        root=tmp_path,
    )
    assert any("notARealSlot" in w for w in m.warnings)


def test_default_activation_on_startup(tmp_path: Path):
    m = validate_raw(
        {
            "id": "a.b",
            "version": "1.0.0",
            "engines": {"openmatlab": ">=0.1.0"},
            "contributes": {"pathEntries": [{"relative": "m"}]},
        },
        root=tmp_path,
    )
    assert m.activation == ["onStartupFinished"]
    assert m.main is None


def test_missing_manifest_file(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ManifestError, match="plugin.yaml"):
        load_manifest(empty)


def test_load_manifest_file_json(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    path = root / "openmatlab.plugin.json"
    path.write_text(
        json.dumps(
            {
                "id": "x.y",
                "version": "0.1.0",
                "engines": {"openmatlab": ">=0.1.0"},
                "main": "e.py",
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest_file(path)
    assert m.id == "x.y"

"""Load and validate plugin manifests (plugin.yaml / openmatlab.plugin.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

KNOWN_CONTRIBUTES = frozenset(
    {
        "commands",
        "menus",
        "toolbar",
        "panels",
        "status",
        "pathEntries",
        "builtins",
        "uxHints",
        "configuration",
    }
)

MANIFEST_NAMES = ("plugin.yaml", "openmatlab.plugin.json")


class ManifestError(ValueError):
    """Manifest is missing, malformed, or fails schema checks."""


@dataclass
class PluginManifest:
    """Validated plugin manifest."""

    id: str
    version: str
    engines_openmatlab: str
    root: Path
    main: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    activation: List[str] = field(default_factory=list)
    contributes: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    source_file: Optional[Path] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def engine_range(self) -> str:
        return self.engines_openmatlab


def _load_yaml(text: str) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise ManifestError(
            "PyYAML is required to load plugin.yaml (pip install PyYAML)"
        ) from exc
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a mapping")
    return data


def _load_json(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a mapping")
    return data


def find_manifest_file(root: Path) -> Path:
    """Locate preferred manifest under plugin root."""
    root = Path(root)
    yaml_path = root / "plugin.yaml"
    json_path = root / "openmatlab.plugin.json"
    if yaml_path.is_file():
        return yaml_path
    if json_path.is_file():
        return json_path
    raise ManifestError(
        f"no plugin.yaml or openmatlab.plugin.json under {root}"
    )


def load_raw(path: Path) -> dict:
    """Load raw mapping from a manifest file path."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.name.endswith(".json"):
        return _load_json(text)
    if path.name.endswith((".yaml", ".yml")):
        return _load_yaml(text)
    raise ManifestError(f"unsupported manifest filename: {path.name}")


def validate_raw(data: Mapping[str, Any], *, root: Path) -> PluginManifest:
    """Validate a raw mapping into ``PluginManifest``."""
    warnings: List[str] = []
    if not isinstance(data, Mapping):
        raise ManifestError("manifest root must be a mapping")

    pid = data.get("id")
    if not isinstance(pid, str) or not pid.strip():
        raise ManifestError("manifest field 'id' is required (non-empty string)")
    pid = pid.strip()

    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ManifestError("manifest field 'version' is required (SemVer string)")
    version = version.strip()

    engines = data.get("engines")
    if not isinstance(engines, Mapping):
        raise ManifestError("manifest field 'engines' is required (mapping)")
    eng = engines.get("openmatlab")
    if not isinstance(eng, str) or not eng.strip():
        raise ManifestError("manifest engines.openmatlab is required (range string)")
    eng = eng.strip()

    main = data.get("main")
    if main is not None and not isinstance(main, str):
        raise ManifestError("manifest field 'main' must be a string when present")
    if isinstance(main, str):
        main = main.strip() or None

    contributes_raw = data.get("contributes") or {}
    if contributes_raw is None:
        contributes_raw = {}
    if not isinstance(contributes_raw, Mapping):
        raise ManifestError("manifest field 'contributes' must be a mapping")
    contributes: Dict[str, Any] = dict(contributes_raw)
    for key in list(contributes):
        if key not in KNOWN_CONTRIBUTES:
            warnings.append(f"unknown contributes key {key!r} (ignored)")

    if main is None and not contributes:
        raise ManifestError(
            "manifest must declare 'main' and/or non-empty 'contributes'"
        )

    activation = data.get("activation")
    if activation is None:
        activation_list: List[str] = ["onStartupFinished"]
    elif isinstance(activation, list):
        activation_list = []
        for item in activation:
            if not isinstance(item, str) or not item.strip():
                raise ManifestError("activation entries must be non-empty strings")
            activation_list.append(item.strip())
        if not activation_list:
            activation_list = ["onStartupFinished"]
    else:
        raise ManifestError("manifest field 'activation' must be a list of strings")

    display_name = data.get("displayName")
    if display_name is not None and not isinstance(display_name, str):
        raise ManifestError("displayName must be a string")
    description = data.get("description")
    if description is not None and not isinstance(description, str):
        raise ManifestError("description must be a string")

    return PluginManifest(
        id=pid,
        version=version,
        engines_openmatlab=eng,
        root=Path(root).resolve(),
        main=main,
        display_name=display_name,
        description=description,
        activation=activation_list,
        contributes=contributes,
        warnings=warnings,
        raw=dict(data),
    )


def load_manifest(root: Path) -> PluginManifest:
    """Find, load, and validate a plugin manifest under ``root``."""
    root = Path(root).resolve()
    path = find_manifest_file(root)
    raw = load_raw(path)
    manif = validate_raw(raw, root=root)
    manif.source_file = path
    return manif


def load_manifest_file(path: Path) -> PluginManifest:
    """Load and validate a specific manifest file (root = parent dir)."""
    path = Path(path).resolve()
    raw = load_raw(path)
    manif = validate_raw(raw, root=path.parent)
    manif.source_file = path
    return manif

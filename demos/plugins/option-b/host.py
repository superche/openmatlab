"""Manifest + path host (YAML; PyYAML if present, else tiny fallback)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_yaml(text: str) -> dict:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        # Minimal fallback for flat key: value and nested provides
        data: dict = {}
        provides: dict = {}
        in_provides = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if line.startswith(" ") or line.startswith("\t"):
                if in_provides and ":" in line:
                    k, v = line.strip().split(":", 1)
                    provides[k.strip()] = v.strip()
                continue
            in_provides = line.strip().startswith("provides:")
            if in_provides:
                data["provides"] = provides
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()
        if provides:
            data["provides"] = provides
        return data


def resolve_symbol(spec: str):
    """'pkg.mod:attr' → attribute."""
    mod_name, _, attr = spec.partition(":")
    mod = importlib.import_module(mod_name)
    return getattr(mod, attr)


def load_path(roots: List[Path]) -> Tuple[Dict[str, Any], List[dict], Dict[str, str]]:
    commands: Dict[str, Any] = {}
    panels: List[dict] = []
    ux: Dict[str, str] = {}
    for root in roots:
        root = root.resolve()
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        for manifest in sorted(root.glob("*/plugin.yaml")):
            meta = _load_yaml(manifest.read_text(encoding="utf-8"))
            provides = meta.get("provides") or {}
            if "commands" in provides:
                resolve_symbol(provides["commands"])(commands)
            if "ui_panels" in provides:
                resolve_symbol(provides["ui_panels"])(panels)
            if "ux" in provides:
                resolve_symbol(provides["ux"])(ux)
    return commands, panels, ux

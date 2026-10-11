"""Resolve paths to docs/feature_map.yaml across editable / repo layouts."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Best-effort repository root (contains docs/feature_map.yaml)."""
    here = Path(__file__).resolve()
    # src/openmatlab/qa/paths.py → parents[3] == repo root in src layout
    candidates = [
        here.parents[3],  # repo/src/openmatlab/qa → repo
        here.parents[2],  # fallback
        Path.cwd(),
    ]
    for root in candidates:
        if (root / "docs" / "feature_map.yaml").is_file():
            return root
    # Last resort: walk up
    for p in [here, *here.parents]:
        if (p / "docs" / "feature_map.yaml").is_file():
            return p
    raise FileNotFoundError(
        "docs/feature_map.yaml not found; run from repo or editable install"
    )


def feature_map_path() -> Path:
    return repo_root() / "docs" / "feature_map.yaml"

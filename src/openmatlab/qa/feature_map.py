"""Load and summarize docs/feature_map.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from openmatlab.qa.paths import feature_map_path

ALLOWED_STATUS = frozenset({"planned", "stub", "partial", "done", "wontfix"})

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - exercised when PyYAML missing
    yaml = None  # type: ignore


@dataclass
class Feature:
    id: str
    layer: str
    name: str
    status: str
    spec: Optional[str] = None
    tests: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Feature":
        return cls(
            id=str(d["id"]),
            layer=str(d["layer"]),
            name=str(d.get("name", d["id"])),
            status=str(d.get("status", "planned")),
            spec=d.get("spec"),
            tests=list(d.get("tests") or []),
            protocols=list(d.get("protocols") or []),
            depends_on=list(d.get("depends_on") or []),
            notes=d.get("notes"),
        )


@dataclass
class FeatureMap:
    version: int
    product: str
    features: List[Feature]
    layers: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def filter(
        self,
        *,
        layer: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Feature]:
        out = self.features
        if layer:
            out = [f for f in out if f.layer == layer]
        if status:
            out = [f for f in out if f.status == status]
        return out

    def validate(self) -> List[str]:
        """Return list of problems (empty if OK)."""
        problems: List[str] = []
        ids = [f.id for f in self.features]
        if len(ids) != len(set(ids)):
            problems.append("duplicate feature ids")
        id_set = set(ids)
        for f in self.features:
            if f.status not in ALLOWED_STATUS:
                problems.append(f"{f.id}: invalid status {f.status!r}")
            for dep in f.depends_on:
                if dep not in id_set:
                    problems.append(f"{f.id}: depends_on unknown id {dep!r}")
        return problems

    def format_table(self, features: Optional[Iterable[Feature]] = None) -> str:
        rows = list(features) if features is not None else self.features
        lines = [
            f"{'ID':<32} {'LAYER':<10} {'STATUS':<8} NAME",
            f"{'-'*32} {'-'*10} {'-'*8} {'-'*24}",
        ]
        for f in rows:
            lines.append(f"{f.id:<32} {f.layer:<10} {f.status:<8} {f.name}")
        lines.append(f"\n{len(rows)} features")
        return "\n".join(lines)

    def format_yaml(self) -> str:
        if yaml is None:
            raise RuntimeError("PyYAML required for --format yaml")
        return yaml.safe_dump(self.raw, sort_keys=False, allow_unicode=True)

    def counts_by_status(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self.features:
            counts[f.status] = counts.get(f.status, 0) + 1
        return counts


def _parse_minimal_yaml_map(text: str) -> Dict[str, Any]:
    """Tiny fallback if PyYAML missing — prefers installing PyYAML via [dev]."""
    raise RuntimeError(
        "PyYAML is required to load the feature map. "
        "Install with: pip install -e \".[dev]\""
    )


def load_feature_map(path: Optional[Path] = None) -> FeatureMap:
    path = path or feature_map_path()
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        _parse_minimal_yaml_map(text)
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("feature_map root must be a mapping")
    features = [Feature.from_dict(f) for f in (data.get("features") or [])]
    return FeatureMap(
        version=int(data.get("version", 1)),
        product=str(data.get("product", "openmatlab")),
        features=features,
        layers=list(data.get("layers") or []),
        raw=data,
    )

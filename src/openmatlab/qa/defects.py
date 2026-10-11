"""Load docs/defects/index.yaml (QA layer 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from openmatlab.qa.paths import repo_root

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def defects_index_path() -> Path:
    return repo_root() / "docs" / "defects" / "index.yaml"


@dataclass
class Defect:
    id: str
    title: str
    status: str
    type: str
    severity: str = "s2"
    feature_ids: List[str] = field(default_factory=list)
    case_ids: List[str] = field(default_factory=list)
    package: str = ""
    file: Optional[str] = None


@dataclass
class DefectIndex:
    version: int
    defects: List[Defect]
    raw: Dict[str, Any] = field(default_factory=dict)

    def filter(self, *, status: Optional[str] = None) -> List[Defect]:
        rows = self.defects
        if status:
            rows = [d for d in rows if d.status == status]
        return rows

    def format_table(self, rows: Optional[List[Defect]] = None) -> str:
        items = rows if rows is not None else self.defects
        lines = [
            f"{'ID':<8} {'STATUS':<12} {'TYPE':<8} {'SEV':<4} TITLE",
            "-" * 72,
        ]
        for d in items:
            lines.append(
                f"{d.id:<8} {d.status:<12} {d.type:<8} {d.severity:<4} {d.title}"
            )
        lines.append(f"\n{len(items)} defects")
        return "\n".join(lines)


def load_defect_index(path: Optional[Path] = None) -> DefectIndex:
    if yaml is None:
        raise RuntimeError('PyYAML required. pip install -e ".[dev]"')
    path = path or defects_index_path()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    defects = [
        Defect(
            id=d["id"],
            title=d.get("title", d["id"]),
            status=d.get("status", "open"),
            type=d.get("type", "gap"),
            severity=d.get("severity", "s2"),
            feature_ids=list(d.get("feature_ids") or []),
            case_ids=list(d.get("case_ids") or []),
            package=d.get("package", ""),
            file=d.get("file"),
        )
        for d in (data.get("defects") or [])
    ]
    return DefectIndex(
        version=int(data.get("version", 1)), defects=defects, raw=data
    )

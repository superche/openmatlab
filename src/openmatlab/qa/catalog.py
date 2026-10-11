"""Load docs/test_catalog.yaml (QA layer 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from openmatlab.qa.paths import repo_root

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def test_catalog_path() -> Path:
    return repo_root() / "docs" / "test_catalog.yaml"


@dataclass
class UseCase:
    id: str
    title: str
    actor: str = ""
    goal: str = ""
    features: List[str] = field(default_factory=list)
    priority: str = "p2"
    narrative: Optional[str] = None


@dataclass
class TestCase:
    id: str
    kind: str
    title: str
    features: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    impl: Optional[str] = None
    status: str = "planned"
    env: str = "unit"


@dataclass
class TestCatalog:
    version: int
    product: str
    use_cases: List[UseCase]
    test_cases: List[TestCase]
    raw: Dict[str, Any] = field(default_factory=dict)

    def filter(
        self,
        *,
        kind: Optional[str] = None,
        status: Optional[str] = None,
        env: Optional[str] = None,
        feature: Optional[str] = None,
    ) -> List[TestCase]:
        rows = self.test_cases
        if kind:
            rows = [t for t in rows if t.kind == kind]
        if status:
            rows = [t for t in rows if t.status == status]
        if env:
            rows = [t for t in rows if t.env == env]
        if feature:
            rows = [t for t in rows if feature in t.features]
        return rows

    def validate(self, known_feature_ids: Optional[set[str]] = None) -> List[str]:
        problems: List[str] = []
        uc_ids = [u.id for u in self.use_cases]
        tc_ids = [t.id for t in self.test_cases]
        if len(uc_ids) != len(set(uc_ids)):
            problems.append("duplicate use_case ids")
        if len(tc_ids) != len(set(tc_ids)):
            problems.append("duplicate test_case ids")
        uc_set, tc_set = set(uc_ids), set(tc_ids)
        for t in self.test_cases:
            for u in t.use_cases:
                if u not in uc_set:
                    problems.append(f"{t.id}: unknown use_case {u!r}")
            if known_feature_ids is not None:
                for f in t.features:
                    if f not in known_feature_ids:
                        problems.append(f"{t.id}: unknown feature {f!r}")
        for u in self.use_cases:
            if known_feature_ids is not None:
                for f in u.features:
                    if f not in known_feature_ids:
                        problems.append(f"{u.id}: unknown feature {f!r}")
        return problems

    def format_table(
        self,
        cases: Optional[List[TestCase]] = None,
        *,
        include_use_cases: bool = True,
    ) -> str:
        lines: List[str] = []
        if include_use_cases:
            lines += ["USE CASES", f"{'ID':<28} {'PRI':<4} TITLE", "-" * 60]
            for u in self.use_cases:
                lines.append(f"{u.id:<28} {u.priority:<4} {u.title}")
            lines.append("")
        rows = cases if cases is not None else self.test_cases
        lines += [
            "TEST CASES",
            f"{'ID':<32} {'KIND':<14} {'STATUS':<10} {'ENV':<12} TITLE",
            "-" * 80,
        ]
        for t in rows:
            lines.append(
                f"{t.id:<32} {t.kind:<14} {t.status:<10} {t.env:<12} {t.title}"
            )
        lines.append(f"\n{len(rows)} test cases")
        return "\n".join(lines)


def load_test_catalog(path: Optional[Path] = None) -> TestCatalog:
    if yaml is None:
        raise RuntimeError('PyYAML required. pip install -e ".[dev]"')
    path = path or test_catalog_path()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    use_cases = [
        UseCase(
            id=u["id"],
            title=u.get("title", u["id"]),
            actor=u.get("actor", ""),
            goal=u.get("goal", ""),
            features=list(u.get("features") or []),
            priority=u.get("priority", "p2"),
            narrative=u.get("narrative"),
        )
        for u in (data.get("use_cases") or [])
    ]
    test_cases = [
        TestCase(
            id=t["id"],
            kind=t.get("kind", "unit"),
            title=t.get("title", t["id"]),
            features=list(t.get("features") or []),
            use_cases=list(t.get("use_cases") or []),
            impl=t.get("impl"),
            status=t.get("status", "planned"),
            env=t.get("env", "unit"),
        )
        for t in (data.get("test_cases") or [])
    ]
    return TestCatalog(
        version=int(data.get("version", 1)),
        product=str(data.get("product", "openmatlab")),
        use_cases=use_cases,
        test_cases=test_cases,
        raw=data,
    )

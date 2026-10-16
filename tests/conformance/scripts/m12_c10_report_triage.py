"""M12 C10 - REPORT.md generation, deduplicated triage groups, pass->fail regression fails the gate."""

from pathlib import Path

from openmatlab.qa.corpus import report, triage


def run(tmp: Path) -> dict:
    base = [{"name": "a", "status": "pass"}, {"name": "b", "status": "pass"}]
    new = [{"name": "a", "status": "pass"}, {"name": "b", "status": "error", "category": "missing-builtin", "key": "strmatch"}]
    md = report.render(new, previous=base)
    groups = triage.group(new + [{"name": "c", "status": "error", "category": "missing-builtin", "key": "strmatch"}])
    return {"d1": int("Pass rate" in md), "d2": int(len(groups) == 1 and groups[0].count == 2),
            "d3": int(report.regressions(new, previous=base) == ["b"])}

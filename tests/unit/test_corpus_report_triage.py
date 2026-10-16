"""M12 C-E4 (Epic #764): REPORT dashboard, regression gate, deduplicated corpus issue filing."""

from __future__ import annotations

import json

import pytest

from openmatlab.qa.corpus import report as R
from openmatlab.qa.corpus import triage as T
from openmatlab.qa.corpus.__main__ import main

pytestmark = pytest.mark.unit

RECS = [
    {"id": "a", "source": "s", "t0": "pass", "t1": "pass", "status": "pass", "category": "pass"},
    {"id": "b", "source": "s", "t0": "pass", "t1": "error", "status": "error", "category": "missing-builtin", "key": "strmatch"},
    {"id": "c", "source": "s", "t0": "pass", "t1": "error", "status": "error", "category": "missing-builtin", "key": "strmatch"},
    {"id": "d", "source": "s", "t0": "error", "t1": "n/a", "status": "error", "category": "corpus-noise", "key": "x"},
    {"id": "e", "source": "s", "t0": "pass", "t1": "error", "status": "error", "category": "toolbox:symbolic", "key": "syms"},
    {"id": "f", "source": "s", "t0": "pass", "t1": "crash", "status": "crash", "category": "internal-crash", "key": "TypeError"},
]


def test_tier_rates_exclude_noise_and_toolbox():
    assert R.rate_of(RECS, "T0") == (5, 5)
    assert R.rate_of(RECS, "T1") == (1, 4)
    assert R.rate_of(RECS, "T2") == (0, 0)


def test_regressions_only_pass_to_fail_for_present_ids():
    prev = [{"id": "a", "status": "pass"}, {"id": "b", "status": "pass"}, {"id": "gone", "status": "pass"}]
    assert R.regressions(RECS, prev) == ["b"]
    assert R.regressions(prev, prev) == []


def test_groups_dedupe_and_skip_noise():
    gs = T.group(RECS)
    assert [(g.category, g.key, g.count) for g in gs][0] == ("missing-builtin", "strmatch", 2)
    assert not any(g.category == "corpus-noise" for g in gs)


def test_render_has_sections_and_regressions():
    md = R.render(RECS, previous=[{"id": "a", "status": "pass"}, {"id": "c", "status": "pass"}])
    for s in ("Pass rate by tier", "Pass rate by source", "Top failure groups", "Regressions", "`c`"):
        assert s in md


def test_threshold_read_from_m12_doc(tmp_path):
    doc = tmp_path / "m.md"
    doc.write_text("| C05 | T0 parse pass rate ≥ 87 % (locked) | x |\n", encoding="utf-8")
    assert R.threshold("T0", doc) == pytest.approx(0.87)
    with pytest.raises(ValueError):
        R.threshold("T1", doc)
    assert 0 < R.threshold("T0") <= 1


class FakeGh:
    def __init__(self, existing):
        self.existing, self.created = existing, []

    def __call__(self, args):
        if args[:2] == ["issue", "list"]:
            return json.dumps(self.existing)
        self.created.append(args)
        return f"https://github.com/o/r/issues/{900 + len(self.created)}\n"


def test_file_issues_dedupes_by_marker_in_any_state():
    gs = T.group(RECS)
    gh = FakeGh([{"number": 5, "body": f"x\n<!-- {gs[0].marker} -->\n"}])
    done = T.file_issues(gs, min_count=1, gh=gh)
    acts = {(g.category, a) for g, _, a in done}
    assert ("missing-builtin", "exists") in acts and ("internal-crash", "filed") in acts
    assert all("corpus" in a for a in gh.created)
    crash = [a for a in gh.created if "[corpus] internal-crash" in a[a.index("--title") + 1]][0]
    assert "p0" in crash
    gh2 = FakeGh([{"number": n, "body": f"<!-- {g.marker} -->"} for n, (g, _, _) in enumerate(done)])
    assert all(a == "exists" for _, _, a in T.file_issues(gs, min_count=1, gh=gh2)) and not gh2.created


def test_min_count_keeps_p0_and_dry_run_files_nothing():
    gh = FakeGh([])
    done = T.file_issues(T.group(RECS), min_count=2, dry_run=True, gh=gh)
    assert {g.key for g, _, _ in done} == {"strmatch", "TypeError"} and not gh.created


def test_cli_gate_and_report(tmp_path, capsys):
    base = tmp_path / "base.json"
    new = tmp_path / "new.json"
    base.write_text(json.dumps({"records": [{"id": "b", "status": "pass"}]}))
    new.write_text(json.dumps({"full_run": False, "records": RECS}))
    assert main(["gate", str(new), "--baseline", str(base)]) == 1
    assert "b" in capsys.readouterr().out
    out = tmp_path / "R.md"
    assert main(["report", "--results", str(new), "--out", str(out)]) == 0
    assert "Pass rate by tier" in out.read_text()
    assert main(["gate", str(tmp_path / "missing.json")]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_committed_report_is_current():
    doc = json.loads(R.report_path().with_name("results.json").read_text(encoding="utf-8"))
    meta = {k: v for k, v in doc.items() if k != "records"}
    assert R.report_path().read_text(encoding="utf-8") == R.render(doc["records"], meta=meta)

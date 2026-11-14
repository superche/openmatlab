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


_HISTORICAL_RUN = "5d9513a4974fde8fa54340fcf11c21b57defcc11"
_HISTORICAL_RESULTS_SHA256 = "e0f11588fa604e97e433ae84f5d49b9f6e1cff3c198b2466aafc9cd9c0453bb6"
_HISTORICAL_TABLE_ROWS = (
    "| T0 | 99.5 % (966/971) |",
    "| T1 | 70.5 % (474/672) |",
    "| T2 | 82.8 % (3442/4159) |",
    "| T3 | 75.3 % (55/73) |",
    "| chebfun | 326 | 100.0 % (326/326) | 55.3 % (162/293) | 55.3 % (162/293) | n/a (0) |",
    "| matlab2tikz | 119 | 100.0 % (118/118) | 97.1 % (100/103) | 97.1 % (100/103) | n/a (0) |",
    "| octave | 5036 | n/a (0) | n/a (0) | 84.5 % (3180/3763) | n/a (0) |",
    "| rosetta | 649 | 99.1 % (522/527) | 76.8 % (212/276) | n/a (0) | 75.3 % (55/73) |",
    "| `pass` | 3896 |",
    "| `semantics-diff` | 708 |",
    "| `toolbox:octave-only` | 442 |",
    "| `deferred` | 401 |",
    "| `toolbox:statistics` | 380 |",
    "| `corpus-noise` | 123 |",
    "| `timeout` | 56 |",
    "| `io-env` | 54 |",
    "| `toolbox:symbolic` | 38 |",
    "| `toolbox:phased` | 12 |",
    "| `graphics` | 7 |",
    "| `missing-builtin` | 6 |",
    "| `parse-error` | 5 |",
    "| `toolbox:java` | 2 |",
    "| `semantics-diff` | `assert-mismatch` | 276 | `octave/elfun/asech#1` |",
    "| `semantics-diff` | `MATLAB:UndefinedFunction` | 74 | `octave/elfun/atan2d#1` |",
    "| `timeout` | `` | 56 | `chebfun/chebfun/test_arclength` |",
    "| `toolbox:symbolic` | `symvar` | 33 | `chebfun/chebfun/test_abs` |",
    "| `semantics-diff` | `MATLAB:invalidType` | 15 | `octave/general/accumarray#17` |",
    "| `semantics-diff` | `Assertion failed.` | 13 | `chebfun/chebfun/test_changeTech` |",
    "| `semantics-diff` | `cast: usage cast(A, 'newclass')` | 11 | `octave/miscellaneous/cast#13` |",
    "| `semantics-diff` | `multi-assign: expected # outputs, got #` | 11 | `octave/general/gradient#2` |",
    "| `semantics-diff` | `Dimensions of arrays being concatenated are not consistent.` | 10 | `chebfun/chebfun/test_and` |",
    "| `semantics-diff` | `MATLAB:expectedScalar` | 8 | `octave/polynomial/polyfit#2` |",
    "| `semantics-diff` | `MATLAB:gallery:unknownName` | 8 | `octave/linear-algebra/linsolve#2` |",
    "| `semantics-diff` | `function-resolution:class-folder` | 7 | `chebfun/chebfun/test_le` |",
    "| `semantics-diff` | `Unable to allocate # TiB for an array with shape (#, #) and ` | 6 | `octave/general/isequal#100` |",
    "| `semantics-diff` | `end outside of an indexing expression` | 6 | `chebfun/chebfun/test_addBreaksAtRoots` |",
    "| `semantics-diff` | `warning: not enough input arguments` | 6 | `chebfun/chebfun/test_vectorCheck` |",
    "| `io-env` | `file` | 5 | `rosetta/CSV_data_manipulation/1` |",
    "| `semantics-diff` | `MATLAB:cell2mat:UnsupportedCellContent` | 5 | `octave/general/cell2mat#10` |",
    "| `semantics-diff` | `MATLAB:ishermitian:invalidInput` | 5 | `octave/linear-algebra/ishermitian#14` |",
    "| `semantics-diff` | `MATLAB:rectint:invalidInput` | 5 | `octave/geometry/rectint#13` |",
    "| `semantics-diff` | `Non-singleton dimensions of the two input arrays must match ` | 5 | `chebfun/chebfun/test_max` |",
    "| `semantics-diff` | `colon: expected Array, got CharValue` | 5 | `octave/specfun/nchoosek#10` |",
    "| `graphics` | `property` | 4 | `chebfun/chebfun/test_ivp` |",
    "| `io-env` | `system` | 4 | `rosetta/Delete_a_file/2` |",
    "| `semantics-diff` | `MATLAB:InputParser:ArgumentFailedValidation` | 4 | `octave/miscellaneous/inputParser#13` |",
    "| `semantics-diff` | `MATLAB:sizeDimensionsMustMatch` | 4 | `octave/general/cart2pol#7` |",
    "| `semantics-diff` | `MATLAB:square` | 4 | `octave/linear-algebra/trace#2` |",
    "| `semantics-diff` | `MATLAB:var:invalidWgts` | 4 | `octave/statistics/var#7` |",
    "| `semantics-diff` | `MATLAB:verLessThan:missingToolbox` | 4 | `octave/miscellaneous/verLessThan#1` |",
    "| `semantics-diff` | `airy: complex arguments are not supported yet.` | 4 | `chebfun/chebfun/test_airy` |",
    "| `semantics-diff` | `array assign: A null assignment can have only one non-colon ` | 4 | `chebfun/chebtech/test_happinessCheck` |",
    "| `semantics-diff` | `cannot convert float infinity to integer` | 4 | `octave/miscellaneous/mustBeGreaterThanOrEqual#1` |",
    "| `io-env` | `input` | 3 | `rosetta/2048/2` |",
    "| `io-env` | `urlread` | 3 | `rosetta/HTTP/1` |",
    "| `semantics-diff` | `MATLAB:accumarray:invalidInput` | 3 | `octave/general/accumarray#12` |",
    "| `semantics-diff` | `MATLAB:datevec:Inputs` | 3 | `octave/time/datevec#118` |",
    "| `semantics-diff` | `MATLAB:deblank:NonStringInput` | 3 | `octave/strings/deblank#10` |",
    "| `semantics-diff` | `MATLAB:dec2bin:InvalidInput` | 3 | `octave/strings/dec2bin#20` |",
    "| `semantics-diff` | `MATLAB:dec2hex:InvalidInput` | 3 | `octave/strings/dec2hex#19` |",
    "| `semantics-diff` | `MATLAB:griddedInterpolant:NonUniqueCompVecsPtsErrId` | 3 | `octave/general/interp1#101` |",
    "| `semantics-diff` | `MATLAB:isprime:InputNotPosInt` | 3 | `octave/specfun/isprime#6` |",
)


def test_render_explains_stored_provenance_and_unknown_stride():
    md = R.render(
        RECS,
        meta={
            "commit": _HISTORICAL_RUN,
            "generated": "2026-10-23T03:19:42Z",
            "full_run": True,
            "timeout": 20.0,
        },
    )
    assert f"Run commit: `{_HISTORICAL_RUN}`" in md
    assert "2026-10-23T03:19:42Z" in md
    assert "(UTC)" in md
    assert "2026-10-23 11:19:42 Asia/Shanghai (UTC+8)" in md
    assert "not the time this markdown was written" in md
    assert "full_run metadata: yes" in md
    assert "Sample stride: not stored in this results file. The stride is unknown." in md
    assert "timeout metadata: 20.0 s" in md
    assert "arbitrary MATLAB projects" in md
    assert "not a tier rate" in md
    assert "T0 does not drop `toolbox` or `io-env`" in md
    assert "outside the denominator" in md
    assert "| T0 | 100.0 % (5/5) |" in md
    assert "| T1 | 25.0 % (1/4) |" in md


def test_render_states_missing_historical_metadata():
    md = R.render(RECS, meta={"full_run": False})
    assert "Run commit: not stored in this results file." in md
    assert "Generated: not stored in this results file." in md
    assert "No date, time, or zone is stated." in md
    assert "full_run metadata: no" in md
    assert "marked as a sample" in md
    assert "Sample stride: not stored in this results file. The stride is unknown." in md
    assert "timeout metadata: not stored in this results file." in md
    assert _HISTORICAL_RUN not in md
    assert "Asia/Shanghai" not in md
    bare = R.render(RECS, meta={"generated": "not-a-clock", "full_run": True})
    assert "Generated: `not-a-clock`" in bare
    assert "no zone conversion is stated" in bare
    assert "Asia/Shanghai" not in bare
    absent = R.render(RECS, meta={"commit": "", "generated": "", "timeout": ""})
    assert "Run commit: not stored in this results file." in absent
    assert "full_run metadata: not stored in this results file." in absent
    assert "Generated: not stored in this results file." in absent
    assert "timeout metadata: not stored in this results file." in absent


def test_committed_historical_numbers_stay_on_the_saved_records():
    import hashlib

    raw = R.report_path().with_name("results.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _HISTORICAL_RESULTS_SHA256
    doc = json.loads(raw)
    records = doc["records"]
    meta = {k: v for k, v in doc.items() if k != "records"}
    assert meta["commit"] == _HISTORICAL_RUN
    assert meta["generated"] == "2026-10-23T03:19:42Z"
    assert meta["full_run"] is True
    assert meta["timeout"] == 20.0
    assert "sample" not in meta and "stride" not in meta
    assert len(records) == 6130
    assert sum(1 for r in records if r.get("category") == "pass") == 3896
    assert R.rate_of(records, "T0") == (966, 971)
    assert R.rate_of(records, "T1") == (474, 672)
    assert R.rate_of(records, "T2") == (3442, 4159)
    assert R.rate_of(records, "T3") == (55, 73)
    md = R.render(records, meta=meta)
    assert R.report_path().read_text(encoding="utf-8") == md
    for row in _HISTORICAL_TABLE_ROWS:
        assert row in md
    assert f"Run commit: `{_HISTORICAL_RUN}`" in md
    assert "2026-10-23 11:19:42 Asia/Shanghai (UTC+8)" in md
    assert "The stride is unknown." in md
    assert "full_run metadata: yes" in md

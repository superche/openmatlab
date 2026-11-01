"""M17 analyst story: readtable, wash missing values, groupsummary, writetable (issue #1034).

The CSV under demos/analyst/out/ is generated and gitignored. out/README.md is
the tracked convention. This test does not change any older test.
"""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
STORY = ROOT / "demos" / "analyst" / "story_assays.m"

SUMMARY = """\
site,GroupCount,mean_moisture_pct,sum_moisture_pct,mean_temp_c,sum_temp_c
North,3,18.4,55.2,21.2,63.6
South,2,21.5,43,18.2,36.4
East,2,15.5,31,24.2,48.4
West,0,,0,,0
"""

CLEANED = """\
site,shift,moisture_pct,temp_c,qc
North,Day,18.4,21,pass
North,Night,19.2,21.6,pass
South,Day,22,18,pass
South,Night,21,18.4,fail
East,Day,15,24,pass
East,Night,16,24.4,pass
North,Day,17.6,21,pass
"""


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def test_story_washes_and_writes_csv():
    text = STORY.read_text()
    assert "TreatAsMissing" in text
    assert "ismissing" in text
    assert "rmmissing" in text
    assert "fillmissing" in text and "'previous'" in text and "'constant'" in text
    assert "IncludeEmptyGroups" in text
    assert "writetable" in text
    assert "movmean" not in text
    assert ".xlsx" not in text

    session = Session.create_default()
    ReplSession(session).run_line(f"run('{STORY.as_posix()}');")
    assert _scalar(session, "nrows") == 12
    assert _scalar(session, "ncols") == 5
    assert _scalar(session, "nmiss") == 9
    assert _scalar(session, "n_after_site") == 10
    assert _scalar(session, "n_drop_site") == 2
    assert _scalar(session, "n_temp_filled") == 2
    assert _scalar(session, "n_qc_filled") == 2
    assert _scalar(session, "n_clean") == 7
    assert _scalar(session, "n_drop_moisture") == 3
    assert _scalar(session, "ngroups") == 4
    assert session.workspace.get("S").cols[0].labels() == ["North", "South", "East", "West"]
    means = np.asarray(session.workspace.get("S").cols[2].backend_buffer(), float).reshape(-1)
    assert means.tolist()[:3] == [18.4, 21.5, 15.5]
    assert np.isnan(means[3])

    summary = ROOT / "demos" / "analyst" / "out" / "site_summary.csv"
    cleaned = ROOT / "demos" / "analyst" / "out" / "cleaned.csv"
    assert summary.read_text() == SUMMARY
    assert cleaned.read_text() == CLEANED
    assert _scalar(session, "summary_bytes") == summary.stat().st_size == 166
    assert _scalar(session, "cleaned_bytes") == cleaned.stat().st_size == 197

    ignored = subprocess.run(
        ["git", "check-ignore", "-v", "demos/analyst/out/site_summary.csv", "demos/analyst/out/cleaned.csv"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert ignored.returncode == 0
    assert "site_summary.csv" in ignored.stdout and "cleaned.csv" in ignored.stdout
    kept = subprocess.run(
        ["git", "check-ignore", "-q", "demos/analyst/out/README.md"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert kept.returncode == 1
    tracked = subprocess.run(
        ["git", "ls-files", "demos/analyst"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert "site_summary.csv" not in tracked.stdout
    assert "cleaned.csv" not in tracked.stdout

    proc = subprocess.run(
        [sys.executable, "-m", "openmatlab.host.cli", "-e", f"run('{STORY.as_posix()}');"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert "Traceback" not in proc.stdout
    assert "Traceback" not in proc.stderr
    assert "ANALYST group=West count=0 mean_moisture=NaN mean_temp=NaN" in proc.stdout
    assert "ANALYST missing site=2 shift=0 moisture_pct=3 temp_c=2 qc=2 total=9" in proc.stdout

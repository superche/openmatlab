"""M15 V07: the record-100 story exports a 300 dpi PNG and PDF (Epic #1012).

The crop keeps the layout title and the citation footnote. The files are
written under demos/mitbih/out/ and are not committed. The raw-versus-filtered
axes stay the last figure.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

from .export_ecg import assert_ecg_page

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]

ROOT = repo_root()
DOI = "10.13026/C2F305"


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def test_v07_record100_png_and_pdf():
    ignored = subprocess.run(["git", "check-ignore", "-q", "downloads/mitbih/100.dat"], cwd=ROOT)
    assert ignored.returncode == 0

    story = ROOT / "demos" / "mitbih" / "story_record100.m"
    text = story.read_text()
    assert "exportgraphics(fig_lab, png_path, 'Resolution', 300)" in text
    assert "exportgraphics(fig_lab, pdf_path, 'Resolution', 300)" in text
    assert DOI in text

    session = Session.create_default()
    ReplSession(session).run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "nlines") == 2
    assert _scalar(session, "agree") == 0.0
    assert _scalar(session, "ntiles") == 4

    out = ROOT / "demos" / "mitbih" / "out"
    png = out / "story_record100.png"
    pdf = out / "story_record100.pdf"
    assert_ecg_page(png, pdf, 300)
    assert _scalar(session, "png_bytes") == png.stat().st_size
    assert _scalar(session, "pdf_bytes") == pdf.stat().st_size

    gfx = session.graphics
    figs = [fig for fig in gfx._figures if fig is not None]
    lab = next(fig for fig in figs if len(fig.axes) >= 4)
    last = gfx.last_figure
    assert last is not lab
    assert len(last.axes[0].lines) == 2
    title = last.axes[0].get_title() or ""
    assert "100" in title and "MLII" in title

    ignored = subprocess.run(
        ["git", "check-ignore", "-v", str(png), str(pdf)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert ignored.returncode == 0
    assert "story_record100.png" in ignored.stdout and "story_record100.pdf" in ignored.stdout
    tracked = subprocess.run(
        ["git", "ls-files", "demos/mitbih/out", "downloads/mitbih"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert tracked.stdout.strip() == ""

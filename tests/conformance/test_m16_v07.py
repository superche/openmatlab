"""M16 V07: the BBBC038 story exports a 300 dpi PNG and PDF (Epic #1024).

The crop keeps the layout title and the citation footnote. The files are
written under demos/bbbc038/out/ and are not committed. The 1-by-2 panel
stays current, and the area histogram stays the only other figure.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import graphics_builtins as gb
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

from .export_bbbc038 import assert_nuclei_page

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]

ROOT = repo_root()
FOOTNOTE = "CC0 1.0. J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019. BBBC038v1."


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def test_v07_bbbc038_png_and_pdf():
    ignored = subprocess.run(["git", "check-ignore", "-q", "downloads/bbbc038/stage1_test.zip"], cwd=ROOT)
    assert ignored.returncode == 0

    story = ROOT / "demos" / "bbbc038" / "story_stage1_test.m"
    text = story.read_text()
    assert "exportgraphics(fig_lab, png_path, 'Resolution', 300)" in text
    assert "exportgraphics(fig_lab, pdf_path, 'Resolution', 300)" in text
    lab = (ROOT / "demos" / "bbbc038" / "lab_figure.m").read_text()
    assert FOOTNOTE in lab

    session = Session.create_default()
    ReplSession(session).run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "ncount") == 6
    assert _scalar(session, "ntiles") == 2
    assert _scalar(session, "labtiles") == 4
    assert session.workspace.get("footnote").text == FOOTNOTE

    out = ROOT / "demos" / "bbbc038" / "out"
    png = out / "story_stage1_test.png"
    pdf = out / "story_stage1_test.pdf"
    assert_nuclei_page(png, pdf, 300)
    assert _scalar(session, "png_bytes") == png.stat().st_size
    assert _scalar(session, "pdf_bytes") == pdf.stat().st_size

    model = gb.model(session)
    current = model.gcf()
    layouts = [c for c in current.children if c.alive and c.type == "tiledlayout"]
    assert len(layouts) == 1
    assert list(layouts[0].props["GridSize"]) == [1.0, 2.0]
    others = [f for f in model.figures() if f is not current]
    assert len(others) == 1
    axes = [c for c in others[0].children if c.alive and c.type == "axes"]
    assert len(axes) == 1
    assert axes[0].props["Title"].props["String"] == "BBBC038 areas"

    ignored = subprocess.run(
        ["git", "check-ignore", "-v", str(png), str(pdf)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert ignored.returncode == 0
    assert "story_stage1_test.png" in ignored.stdout and "story_stage1_test.pdf" in ignored.stdout
    tracked = subprocess.run(
        ["git", "ls-files", "demos/bbbc038/out", "downloads/bbbc038"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert tracked.stdout.strip() == ""

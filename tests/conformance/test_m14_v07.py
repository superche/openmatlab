"""M14 V07: the FD001 story exports a 300 dpi PNG and PDF (Epic #998).

The crop keeps the layout title, the colorbar labels and the Saxena footnote.
The files are written under demos/cmapss/out/ and are not committed.
"""

from __future__ import annotations

import subprocess

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session
from tests.unit.test_m14_v07_export import assert_lab_page

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]

ROOT = repo_root()


def test_v07_story_png_and_pdf():
    story = ROOT / "demos" / "cmapss" / "story_fd001.m"
    text = story.read_text()
    assert "exportgraphics(fig_lab, png_path, 'Resolution', 300)" in text
    assert "exportgraphics(fig_lab, pdf_path, 'Resolution', 300)" in text
    assert "10.5281/zenodo.15346912" in text

    session = Session.create_default()
    ReplSession(session).run_line(f'run("{story.as_posix()}");')

    out = ROOT / "demos" / "cmapss" / "out"
    png = out / "story_fd001.png"
    pdf = out / "story_fd001.pdf"
    assert_lab_page(png, pdf, 300)

    ignored = subprocess.run(
        ["git", "check-ignore", "-v", str(png), str(pdf)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert ignored.returncode == 0
    assert "story_fd001.png" in ignored.stdout and "story_fd001.pdf" in ignored.stdout
    tracked = subprocess.run(
        ["git", "ls-files", "demos/cmapss/out", "downloads/cmapss"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert tracked.stdout.strip() == ""

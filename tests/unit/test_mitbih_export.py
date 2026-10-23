"""M15 B-E5 (#1012): 300 dpi PNG and PDF of the record-100 lab figure.

The series is synthetic. This checks the export the story uses: a slide-sized
2-by-2 layout, default 150 dpi, demo 300 dpi, and print at 300 dpi. The
footnote stays below the panels.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

from conformance.export_ecg import assert_ecg_page

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]

_LAYOUT = """
fig_lab = figure('Visible','off','Position',[100 100 1200 900]);
tl = tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'loose');
tl.Title.String = 'MIT-BIH record 100';
tl.XLabel.String = sprintf('G. B. Moody and R. G. Mark, IEEE Eng. Med. Biol. Mag. 20(3):45-50, 2001.\\nA. L. Goldberger et al., Circulation 101(23):e215-e220, 2000.\\nData: DOI 10.13026/C2F305 (ODC-By 1.0).');
nexttile; plot(1:40); xlabel('s'); ylabel('mV'); title('record 100 MLII raw');
nexttile; plot(1:40); hold on; plot(8, 8, 'o'); xlabel('s'); ylabel('mV'); title('record 100 MLII filtered, R peaks');
nexttile; histogram(0.5:0.05:1.2); xlabel('s'); ylabel('count'); title('record 100 RR');
nexttile; plot(0:60, sin(0:60)); xlim([0 60]); xlabel('Hz'); ylabel('mV'); title('record 100 MLII spectrum');
"""


def _run(code: str) -> None:
    ReplSession(Session.create_default()).run_line(code)


def test_exportgraphics_default_and_demo_dpi(tmp_path):
    d = tmp_path.as_posix()
    _run(
        _LAYOUT
        + f"exportgraphics(fig_lab, '{d}/default.png'); exportgraphics(fig_lab, '{d}/default.pdf'); "
        + f"exportgraphics(fig_lab, '{d}/demo.png', 'Resolution', 300); "
        + f"exportgraphics(fig_lab, '{d}/demo.pdf', 'Resolution', 300); close all"
    )
    assert_ecg_page(tmp_path / "default.png", tmp_path / "default.pdf", 150)
    assert_ecg_page(tmp_path / "demo.png", tmp_path / "demo.pdf", 300)


def test_print_keeps_title_and_footnote(tmp_path):
    d = tmp_path.as_posix()
    _run(
        _LAYOUT
        + f"print(fig_lab, '{d}/p.png', '-dpng', '-r300'); "
        + f"print(fig_lab, '{d}/p.pdf', '-dpdf', '-r300'); close all"
    )
    assert_ecg_page(tmp_path / "p.png", tmp_path / "p.pdf", 300)


def test_story_script_exports_both():
    root = Path(__file__).resolve().parents[2]
    text = (root / "demos" / "mitbih" / "story_record100.m").read_text()
    assert "exportgraphics(fig_lab, png_path, 'Resolution', 300)" in text
    assert "exportgraphics(fig_lab, pdf_path, 'Resolution', 300)" in text
    assert "10.13026/C2F305" in text
    assert "demos/mitbih/out/" in (root / ".gitignore").read_text()

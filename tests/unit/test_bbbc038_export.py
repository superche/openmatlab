"""M16 I-E5 (#1024): 300 dpi PNG and PDF of the nuclei lab figure.

The image is synthetic. This checks the export the story uses: a slide-sized
2-by-2 layout, default 150 dpi, demo 300 dpi, and print at 300 dpi. The
footnote stays below the panels.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

from conformance.export_bbbc038 import assert_nuclei_page

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]

_LAYOUT = """
A = uint8(zeros(40, 48, 3));
A(8:28, 10:30, :) = 200;
L = zeros(40, 48); L(8:28, 10:30) = 1;
B = labeloverlay(A, L);
fig_lab = figure('Visible','off','Position',[100 100 1200 900]);
tl = tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'loose');
tl.Title.String = 'BBBC038v1 stage1_test';
tl.XLabel.String = 'CC0 1.0. J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019. BBBC038v1.';
nexttile; imshow(A); title('BBBC038 raw');
nexttile; imshow(B); title('BBBC038 overlay');
nexttile; histogram([117 143 152 154 193 219]); title('Area (px)'); xlabel('Area (px)'); ylabel('Count');
nexttile; axis off; text(0.05, 0.72, sprintf('Nuclei 6\\nMean area 163 px\\nMedian area 153 px')); title('BBBC038 summary');
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
    assert_nuclei_page(tmp_path / "default.png", tmp_path / "default.pdf", 150)
    assert_nuclei_page(tmp_path / "demo.png", tmp_path / "demo.pdf", 300)


def test_print_keeps_title_and_footnote(tmp_path):
    d = tmp_path.as_posix()
    _run(
        _LAYOUT
        + f"print(fig_lab, '{d}/p.png', '-dpng', '-r300'); "
        + f"print(fig_lab, '{d}/p.pdf', '-dpdf', '-r300'); close all"
    )
    assert_nuclei_page(tmp_path / "p.png", tmp_path / "p.pdf", 300)


def test_story_script_exports_both():
    root = Path(__file__).resolve().parents[2]
    text = (root / "demos" / "bbbc038" / "story_stage1_test.m").read_text()
    assert "exportgraphics(fig_lab, png_path, 'Resolution', 300)" in text
    assert "exportgraphics(fig_lab, pdf_path, 'Resolution', 300)" in text
    assert "BBBC038v1" in text
    assert "demos/bbbc038/out/" in (root / ".gitignore").read_text()

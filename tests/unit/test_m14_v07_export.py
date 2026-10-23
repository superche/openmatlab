"""Epic #998 (M14 V07): lab-meeting PNG and PDF export.

A tiled heatmap figure keeps the layout canvas (not the default 560-by-420
window). exportgraphics crops with a pad so the title, colorbar labels and
footnote stay off the page edge. print keeps a canvas that already fits, and
grows the page when an artist would be clipped. Default resolution is 150 dpi.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]

DOI = "10.5281/zenodo.15346912"
_LAB = """
fig_lab = figure('Visible','off');
tl = tiledlayout(2, 3, 'TileSpacing', 'compact', 'Padding', 'loose');
tl.Title.String = 'FD001 unit 1';
tl.XLabel.String = sprintf('A. Saxena, K. Goebel, D. Simon, and N. Eklund, PHM08, 2008.\\nData: DOI 10.5281/zenodo.15346912 (CC BY 4.0).');
nexttile; plot(1:20, sin(1:20)); title('FD001 unit 1 sensor traces'); xlabel('cycle'); ylabel('z-score');
nexttile; plot(1:10, cos(1:10)); title('FD001 unit 1 early vs late'); xlabel('window index'); ylabel('sensor_4');
names = {'sensor_2','sensor_3','sensor_4','sensor_6','sensor_7','sensor_8','sensor_9','sensor_11','sensor_12','sensor_13','sensor_14','sensor_15','sensor_17','sensor_20','sensor_21'};
C = eye(15);
nexttile([2 1]);
heatmap(names, names, C, 'ColorLimits', [-1 1], 'Title', 'FD001 sensor correlation', 'XLabel', 'sensor', 'YLabel', 'sensor');
nexttile; histogram(120 + (1:40)); title('FD001 train failure cycles'); xlabel('failure cycle'); ylabel('units');
nexttile; plot(1:20, 20:-1:1); title('FD001 unit 1 train RUL'); xlabel('cycle'); ylabel('RUL');
"""


def _session(code: str) -> Session:
    session = Session.create_default()
    ReplSession(session).run_line(code)
    return session


def pdf_inches(path: Path) -> tuple[float, float]:
    raw = path.read_bytes()
    assert raw.startswith(b"%PDF")
    match = re.search(rb"/MediaBox\s*\[\s*([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)", raw)
    assert match, "PDF has no MediaBox"
    x0, y0, x1, y1 = (float(v) for v in match.groups())
    return (x1 - x0) / 72.0, (y1 - y0) / 72.0


def assert_lab_page(png: Path, pdf: Path, dpi: float) -> None:
    """Resolution, canvas size, and that the crop kept title, colorbar and footnote."""
    assert png.stat().st_size > 0 and pdf.stat().st_size > 0
    arr = np.asarray(Image.open(png).convert("RGB"))
    height, width = arr.shape[:2]
    page_w, page_h = pdf_inches(pdf)
    # The squashed default window is about 5.8 by 4.4 inches. The layout canvas is 13.5 by 8.
    assert page_w >= 10.5, page_w
    assert page_h >= 6.5, page_h
    got_x = width / page_w
    got_y = height / page_h
    # V07: the call's resolution is at least 150 dpi. Pixel rounding can sit a
    # fraction of a pixel under the nominal dpi; it must not be a whole step under.
    assert dpi >= 150
    assert got_x >= dpi - 0.5 and got_y >= dpi - 0.5, (got_x, got_y, dpi)
    assert abs(got_x - dpi) / dpi < 0.02, (got_x, dpi)
    assert abs(got_y - dpi) / dpi < 0.02, (got_y, dpi)

    ink = np.any(arr < 245, axis=2)
    ys, xs = np.where(ink)
    assert xs.size, "export is blank"
    margin_l = int(xs.min())
    margin_t = int(ys.min())
    margin_r = int(width - 1 - xs.max())
    margin_b = int(height - 1 - ys.max())
    assert min(margin_l, margin_t, margin_r, margin_b) >= 8, (margin_l, margin_t, margin_r, margin_b)

    dark = np.all(arr < 80, axis=2)
    # Layout title sits in the top band, footnote in the bottom band, both inset.
    assert dark[: int(height * 0.12), int(width * 0.25): int(width * 0.75)].sum() > 30
    assert dark[int(height * 0.88):, int(width * 0.15): int(width * 0.85)].sum() > 30
    _assert_colorbar_labels(arr, dark)


def _assert_colorbar_labels(arr: np.ndarray, dark: np.ndarray) -> None:
    """The colorbar strip is inset, and its tick labels sit to its right, not on the cut edge."""
    height, width = arr.shape[:2]
    x0 = int(width * 0.70)
    region = arr[:, x0:]
    sat = region.max(axis=2).astype(int) - region.min(axis=2).astype(int)
    colorful = sat > 35
    counts = colorful.sum(axis=0)
    bar_cols = np.where(counts > height * 0.12)[0]
    assert bar_cols.size, "no colorbar strip in the right of the page"
    bar_right = int(bar_cols.max())
    labels = dark[:, x0 + bar_right + 1:]
    assert labels.sum() > 20, "colorbar tick labels were cropped"
    label_xs = np.where(labels)[1]
    assert int(width - 1 - (x0 + bar_right + 1 + label_xs.max())) >= 4


def test_exportgraphics_default_and_demo_dpi(tmp_path):
    d = tmp_path.as_posix()
    _session(
        _LAB
        + f"exportgraphics(fig_lab, '{d}/default.png'); exportgraphics(fig_lab, '{d}/default.pdf'); "
        + f"exportgraphics(fig_lab, '{d}/demo.png', 'Resolution', 300); "
        + f"exportgraphics(fig_lab, '{d}/demo.pdf', 'Resolution', 300); close all"
    )
    assert_lab_page(tmp_path / "default.png", tmp_path / "default.pdf", 150)
    assert_lab_page(tmp_path / "demo.png", tmp_path / "demo.pdf", 300)


def test_print_keeps_title_colorbar_and_footnote(tmp_path):
    d = tmp_path.as_posix()
    _session(
        _LAB
        + f"print(fig_lab, '{d}/p.png', '-dpng', '-r300'); "
        + f"print(fig_lab, '{d}/p.pdf', '-dpdf', '-r300'); close all"
    )
    assert_lab_page(tmp_path / "p.png", tmp_path / "p.pdf", 300)


def test_story_script_exports_both():
    """The story's source asks for both files at 300 dpi. The run itself is the conformance test."""
    root = Path(__file__).resolve().parents[2]
    text = (root / "demos" / "cmapss" / "story_fd001.m").read_text()
    assert "exportgraphics(fig_lab, png_path, 'Resolution', 300)" in text
    assert "exportgraphics(fig_lab, pdf_path, 'Resolution', 300)" in text
    assert DOI in text
    assert "demos/cmapss/out/" in (root / ".gitignore").read_text()

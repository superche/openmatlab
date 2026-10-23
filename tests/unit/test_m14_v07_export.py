"""Epic #998 (M14 V07): lab-meeting PNG and PDF export.

A tiled heatmap figure keeps the layout canvas (not the default 560-by-420
window). exportgraphics crops with a pad so the title, colorbar labels and
footnote stay off the page edge. print keeps a canvas that already fits, and
grows the page when an artist would be clipped. Default resolution is 150 dpi.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

from conformance.export_page import assert_lab_page

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

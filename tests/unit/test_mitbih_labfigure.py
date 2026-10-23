"""M15 B-E4 (#1011): the 2-by-2 lab layout the record-100 story uses.

The ECG series is not loaded here. This checks the layout calls: grid, four
tiles, title, and the citation footnote.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

LAYOUT = """
fig = figure;
tl = tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'loose');
tl.Title.String = 'MIT-BIH record 100';
tl.XLabel.String = sprintf('G. B. Moody and R. G. Mark, 2001.\\nA. L. Goldberger et al., 2000.\\nData: DOI 10.13026/C2F305');
nexttile; plot(1:4); xlabel('s'); ylabel('mV'); title('record 100 MLII raw');
nexttile; plot(1:4); hold on; plot(2, 2, 'o'); xlabel('s'); ylabel('mV'); title('record 100 MLII filtered, R peaks');
nexttile; histogram(1:8); xlabel('s'); ylabel('count'); title('record 100 RR');
nexttile; plot(0:3, 1:4); xlim([0 60]); xlabel('Hz'); ylabel('mV'); title('record 100 MLII spectrum');
gs = tl.GridSize;
ntiles = numel(tl.Children);
"""


@pytest.fixture
def session():
    s = Session.create_default()
    ReplSession(s).run_line(LAYOUT)
    return s


def _col(session, name):
    return np.asarray(session.workspace.get(name).backend_buffer(), dtype=float).reshape(-1)


def test_grid_is_two_by_two_with_four_tiles(session):
    assert _col(session, "gs").tolist() == [2, 2]
    assert _col(session, "ntiles").tolist() == [4]
    model = session.plots._gmodel
    layouts = [c for fig in model.figures() for c in fig.children if c.alive and c.type == "tiledlayout"]
    assert len(layouts) == 1
    note = layouts[0].props["XLabel"].props["String"]
    assert "10.13026/C2F305" in note
    assert "Moody" in note and "2001" in note
    assert "Goldberger" in note and "2000" in note
    assert layouts[0].props["Title"].props["String"] == "MIT-BIH record 100"


def test_rendered_tiles_carry_units(session):
    figs = [fig for fig in session.graphics._figures if fig is not None]
    assert len(figs) == 1
    lab = figs[0]
    titles = [ax.get_title() or "" for ax in lab.axes]
    assert any("raw" in t for t in titles)
    assert any("R peaks" in t for t in titles)
    assert any("RR" in t for t in titles)
    assert any("spectrum" in t for t in titles)
    labels = " ".join((ax.get_xlabel() or "") + " " + (ax.get_ylabel() or "") for ax in lab.axes)
    assert "s" in labels and "mV" in labels and "Hz" in labels
    blob = lab._suptitle.get_text() if lab._suptitle is not None else ""
    blob += "\n" + "\n".join(t.get_text() for t in lab.texts)
    assert "10.13026/C2F305" in blob
    assert "record 100" in blob

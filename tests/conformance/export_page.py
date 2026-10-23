"""Page checks for a lab-meeting PNG and PDF (Epic #998).

Shared by the unit export tests and the V07 conformance script. Import it as
``conformance.export_page`` from unit tests, and as a relative import from
other modules in this package. ``tests`` is not a package.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image


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

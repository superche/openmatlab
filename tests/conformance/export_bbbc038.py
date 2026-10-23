"""Page checks for the BBBC038 lab PNG and PDF (Epic #1024).

The crop must keep the layout title and the citation footnote, and the
footnote must sit below the panels. Shared by the unit export test and the
V07 conformance script.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from conformance.export_page import pdf_inches


def assert_nuclei_page(png: Path, pdf: Path, dpi: float) -> None:
    """Non-empty files, the requested dpi, and a gap between the panels and the footnote."""
    assert png.is_file() and pdf.is_file()
    assert png.stat().st_size > 0 and pdf.stat().st_size > 0
    arr = np.asarray(Image.open(png).convert("RGB"))
    height, width = arr.shape[:2]
    page_w, page_h = pdf_inches(pdf)
    # The default window is about 5.8 by 4.4 inches. The lab figure is 1200 by 900
    # pixels, so the page stays large enough for four panels plus the footnote.
    assert page_w >= 9.0, page_w
    assert page_h >= 7.0, page_h
    got_x = width / page_w
    got_y = height / page_h
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
    # The title sits in the top band. The black FOV starts lower, so this band
    # is the layout title and not the image panels.
    assert dark[: int(height * 0.04), int(width * 0.25): int(width * 0.75)].sum() > 20
    # The footnote is the last ink. The panels end above this band.
    assert dark[int(height * 0.96):, int(width * 0.15): int(width * 0.85)].sum() > 20

    gap_in = _footnote_gap_inches(ink, got_y)
    assert gap_in >= 0.10, gap_in


def _footnote_gap_inches(ink: np.ndarray, dpi_y: float) -> float:
    """Longest white band in the bottom quarter that still has ink under it."""
    height = ink.shape[0]
    row = ink.mean(axis=1)
    white = row < 0.01
    start = int(height * 0.75)
    best = 0
    i = start
    while i < height:
        if not white[i]:
            i += 1
            continue
        j = i
        while j < height and white[j]:
            j += 1
        below = float(row[j: min(height, j + 15)].mean()) if j < height else 0.0
        if below > 0.02:
            best = max(best, j - i)
        i = j
    return best / dpi_y

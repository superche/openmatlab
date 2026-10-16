"""M13 (Graphics completion) conformance manifest. Single source for the exit criteria.

Same honesty model as M11. Handle-model criteria (G01-G08) are ``.m`` scripts asserting
MATLAB-documented property/handle behaviour; Workbench and snapshot criteria (G09, G10) are
``.py`` scripts exposing ``run(tmp) -> dict``. Compared to ``<script>.expected.json``.
Strict xfail until met.
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "G01": ("m13_g01_handle_arrays", "p0", [768, 673], "met"),
    "G02": ("m13_g02_findobj", "p0", [769, 593], "met"),
    "G03": ("m13_g03_layout_axes", "p0", [770, 593], "pending"),
    "G04": ("m13_g04_charts2d", "p1", [772, 593], "met"),
    "G05": ("m13_g05_colour_image", "p0", [771, 593], "pending"),
    "G06": ("m13_g06_3d", "p1", [771, 593], "pending"),
    "G07": ("m13_g07_annotation", "p1", [772], "met"),
    "G08": ("m13_g08_save_export", "p0", [773, 593], "pending"),
    "G09": ("m13_g09_workbench_figures", "p0", [767, 774, 760], "pending"),
    "G10": ("m13_g10_snapshots", "p1", [774], "pending"),
}

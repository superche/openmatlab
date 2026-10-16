"""M11 (Debugger and Workbench) conformance manifest. Single source for the exit criteria.

Same honesty model as M8. Language criteria (D01-D07) are ``.m`` scripts; a sibling
``.queue`` file, when present, holds the lines typed at the ``K>>``/``input`` prompt.
Workbench criteria (D08-D10) are ``.py`` scripts exposing ``run(tmp) -> dict`` against
the headless ``host/workbench.py`` model. Both compare to ``<script>.expected.json``.
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "D01": ("m11_d01_exception_stack_report", "p0", [698, 565], "met"),
    "D02": ("m11_d02_dbstack", "p0", [698, 611], "met"),
    "D03": ("m11_d03_breakpoints", "p0", [699], "met"),
    "D04": ("m11_d04_stepping", "p0", [699], "met"),
    "D05": ("m11_d05_paused_workspace", "p1", [699, 611], "met"),
    "D06": ("m11_d06_keyboard_input", "p1", [700, 577], "met"),
    "D07": ("m11_d07_error_stop", "p1", [700], "met"),
    "D08": ("m11_d08_workbench_debug_ui", "p0", [701], "met"),
    "D09": ("m11_d09_variable_editor", "p1", [702], "pending"),
    "D10": ("m11_d10_workbench_workflows", "p1", [703], "pending"),
}

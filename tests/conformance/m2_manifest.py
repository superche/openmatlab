"""M2 (Octave-breadth) conformance manifest — single source for exit criteria.

Each criterion maps to one script under ``scripts/``. ``met`` criteria must pass;
``pending`` ones run as strict xfail (they flip to failures once they pass, which
forces the manifest to be updated — no silent drift, no weakened tests).
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "C01": ("c01_control_flow", "p0", [], "met"),
    "C02": ("c02_indexing", "p0", [191], "pending"),
    "C03": ("c03_cells", "p0", [], "met"),
    "C04": ("c04_numeric_builtins", "p0", [192], "pending"),
    "C05": ("c05_sort_find_options", "p1", [95, 96], "pending"),
    "C06": ("c06_delete_elements", "p0", [120, 109], "pending"),
    "C07": ("c07_logical_indexing", "p0", [162], "pending"),
    "C08": ("c08_grow_on_assign", "p0", [119, 108], "pending"),
    "C09": ("c09_unique_issorted", "p1", [97], "pending"),
    "C10": ("c10_cellfun", "p1", [81], "pending"),
    "C11": ("c11_scalar_power_script", "p0", [193], "pending"),
}

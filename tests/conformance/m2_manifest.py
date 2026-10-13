"""M2 (Octave-breadth) conformance manifest — single source for exit criteria.

Each criterion maps to one script under ``scripts/``. ``met`` criteria must pass;
``pending`` ones run as strict xfail (they flip to failures once they pass, which
forces the manifest to be updated — no silent drift, no weakened tests).
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "C01": ("c01_control_flow", "p0", [], "met"),
    "C02": ("c02_indexing", "p0", [191], "met"),
    "C03": ("c03_cells", "p0", [], "met"),
    "C04": ("c04_numeric_builtins", "p0", [192], "met"),
    "C05": ("c05_sort_find_options", "p1", [95, 96], "met"),
    "C06": ("c06_delete_elements", "p0", [120, 109], "met"),
    "C07": ("c07_logical_indexing", "p0", [162], "met"),
    "C08": ("c08_grow_on_assign", "p0", [119, 108], "met"),
    "C09": ("c09_unique_issorted", "p1", [97], "met"),
    "C10": ("c10_cellfun", "p1", [81], "met"),
    "C11": ("c11_scalar_power_script", "p0", [193], "met"),
    "C14": ("c14_int_string_classes", "p2", [72, 78, 183], "met"),
    "C13": ("c13_complex", "p2", [71, 229, 228], "met"),
    "C12": ("c12_nd_arrays", "p2", [74, 182, 173, 259, 322, 330], "met"),
    "C15": ("c15_string_arrays", "p2", [459, 460], "met"),
    "C16": ("c16_sparse", "p2", [451], "met"),
    "C17": ("c17_linear_solve", "p2", [496], "met"),
    "C18": ("c18_structs", "p2", [506, 504], "met"),
}

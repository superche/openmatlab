"""M7 (MATLAB core language & I/O) conformance manifest — single source for exit criteria.

Same honesty model as M2: ``pending`` criteria run as strict xfail and flip to
failures once they pass, forcing the manifest (and the milestone doc) to be
updated in the same PR.
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "C01": ("m7_c01_errors", "p0", [530, 540, 541], "met"),
    "C02": ("m7_c02_functions", "p0", [531, 529, 542, 543, 544], "met"),
    "C03": ("m7_c03_command_syntax", "p0", [532, 545, 546], "met"),
    "C04": ("m7_c04_file_io", "p0", [533, 547, 548], "met"),
    "C05": ("m7_c05_core_math", "p0", [534, 550, 551, 552], "met"),
    "C06": ("m7_c06_arrays_sets", "p0", [535, 553, 554], "met"),
    "C07": ("m7_c07_strings", "p0", [536, 555, 556], "met"),
    "C08": ("m7_c08_graphics_core", "p0", [537, 557, 558, 559], "pending"),
    "C09": ("m7_c09_linalg_decomp", "p1", [538, 560], "pending"),
    "C10": ("m7_c10_map_datetime", "p1", [539, 561, 562], "pending"),
}

"""M3 (Domain toolboxes) conformance manifest. This is the single source for the exit criteria.

``pending`` criteria run as strict xfail (see ``m8_manifest``). T06 runs with the
community.signal plugin mfiles on the path, because those functions ship as a
community plugin and not in core.
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "T01": ("m3_t01_fft", "p1", [625], "met"),
    "T02": ("m3_t02_poly_interp", "p1", [626], "met"),
    "T03": ("m3_t03_calculus_ode_opt", "p1", [627, 581], "met"),
    "T04": ("m3_t04_stats", "p1", [628, 581], "met"),
    "T05": ("m3_t05_data_io", "p1", [629], "met"),
    "T06": ("m3_t06_signal_plugin", "p2", [630], "met"),
    "T07": ("m3_t07_sparse", "p2", [631, 527], "met"),
}

PLUGIN_SCRIPTS = {"m3_t06_signal_plugin"}

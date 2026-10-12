"""Domain business-conformance manifest — milestone/5 exit criteria.

Each criterion maps to one script under ``scripts/`` (D01–D03) or a dedicated
Python gate (D04). ``met`` criteria must pass; ``pending`` ones run as strict
xfail (they flip to failures once they pass — no silent drift, no weakened
tests).

Scripts D01–D03 assume the community.signal ``mfiles`` directory is on the path
(see ``test_domain_conformance.py`` harness). D04 proves PluginHost path
contribution → ``which`` without a raw Session ``addpath`` in the test body.
"""

from __future__ import annotations

# id -> (script_or_gate, priority, tracking issues, status)
# script_or_gate: .m basename for script criteria; "plugin_which" for D04 gate
CRITERIA = {
    "D01": ("d01_hamming", "p0", [373], "met"),
    "D02": ("d02_rectwin", "p0", [374], "met"),
    "D03": ("d03_blackman", "p0", [375], "met"),
    "D04": ("plugin_which", "p1", [376], "met"),
}

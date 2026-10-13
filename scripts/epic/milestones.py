"""Milestone registry shared by epicdocs.py / accept.py (select with MS env or config key "ms")."""
MS = {
    "m7": dict(manifest="tests/conformance/m7_manifest.py", test="tests/conformance/test_m7_conformance.py", fn="test_m7_criterion",
               doc="docs/milestones/M7-core-language-io.md", title="MATLAB core language & I/O (M7)", num=7, label="M7"),
    "m8": dict(manifest="tests/conformance/m8_manifest.py", test="tests/conformance/test_m8_conformance.py", fn="test_m8_criterion",
               doc="docs/milestones/M8-object-system.md", title="Object system (M8)", num=8, label="M8"),
    "m3": dict(manifest="tests/conformance/m3_manifest.py", test="tests/conformance/test_m3_conformance.py", fn="test_m3_criterion",
               doc="docs/milestones/M3-domain-toolboxes.md", title="Domain toolboxes (M3)", num=3, label="M3"),
}


def total(key):
    import re
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / MS[key]["manifest"]).read_text()
    return len(re.findall(r'^\s+"[A-Z]\d+": \(', src, re.M))

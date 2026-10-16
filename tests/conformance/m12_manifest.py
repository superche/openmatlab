"""M12 (Real-script compatibility gate) conformance manifest. Single source for the exit criteria.

Same honesty model as M11. Every criterion is a ``.py`` script exposing ``run(tmp) -> dict``
against ``openmatlab.qa.corpus``; tier criteria (C05-C09) read the committed full-run results
(``docs/corpus/results.json``; the corpus code itself is never committed). Compared to
``<script>.expected.json``. Strict xfail until met.
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "C01": ("m12_c01_corpus_manifest", "p0", [762], "pending"),
    "C02": ("m12_c02_runner_isolation", "p0", [761], "met"),
    "C03": ("m12_c03_preprocess", "p0", [763], "pending"),
    "C04": ("m12_c04_classifier", "p0", [763], "pending"),
    "C05": ("m12_c05_tier0", "p0", [766], "pending"),
    "C06": ("m12_c06_tier1", "p0", [766], "pending"),
    "C07": ("m12_c07_tier2", "p1", [765], "pending"),
    "C08": ("m12_c08_tier3", "p1", [765], "pending"),
    "C09": ("m12_c09_no_crash", "p0", [766], "pending"),
    "C10": ("m12_c10_report_triage", "p1", [764], "pending"),
}

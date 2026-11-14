"""Corpus REPORT dashboard, tier pass rates and the pass->fail regression gate (M12 C10, Epic #764).

``render(records, previous=None)`` turns run records into ``docs/corpus/REPORT.md``;
``regressions(new, previous)`` lists entries that passed before and do not pass now (the CI gate);
``load_results()`` wraps the committed full run for the tier criteria (C05-C09), and ``threshold(tier)``
reads the threshold locked in ``docs/milestones/M12-corpus-gate.md``.

Tiers: T0 parses; T1 runs; T2 self-checks; T3 matches a golden.
``excluded`` drops ``corpus-noise`` on every tier, and ``toolbox`` / ``io-env`` on T1-T3.
``tier_outcome`` then counts only ``pass``, ``error``, ``timeout``, and ``crash``;
a success is the value ``pass``.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from openmatlab.qa.paths import repo_root

TIERS = ("T0", "T1", "T2", "T3")
TIER_CRITERION = {"T0": "C05", "T1": "C06", "T2": "C07", "T3": "C08"}
RAN = ("pass", "error", "timeout", "crash")


def _id(r: dict) -> str:
    return str(r.get("id", r.get("name", "")))


def _top(cat: str) -> str:
    return (cat or "").split(":", 1)[0]


def excluded(r: dict, tier: str) -> bool:
    top = _top(r.get("category", ""))
    if top == "corpus-noise":
        return True
    return tier != "T0" and top in ("toolbox", "io-env")


def tier_outcome(r: dict, tier: str) -> Optional[bool]:
    """True/False when the tier applies to the record and it is counted, else None."""
    if excluded(r, tier):
        return None
    v = r.get(tier.lower())
    if v in RAN:
        return v == "pass"
    return None


def rate_of(records: List[dict], tier: str) -> tuple:
    """``(passed, counted)`` for a tier."""
    outs = [o for o in (tier_outcome(r, tier) for r in records) if o is not None]
    return sum(outs), len(outs)


def _passed(r: dict) -> bool:
    return r.get("status") == "pass"


def regressions(new: List[dict], previous: List[dict]) -> List[str]:
    """Ids that passed in ``previous`` and are present but not passing in ``new`` (sorted)."""
    before = {_id(r) for r in previous if _passed(r)}
    return sorted(_id(r) for r in new if _id(r) in before and not _passed(r))


def threshold(tier: str, doc: Optional[Path] = None) -> float:
    """Threshold (fraction) for a tier from the M12 criteria table (``| C05 | T0 ... ≥ 98 % ...``)."""
    doc = doc or repo_root() / "docs" / "milestones" / "M12-corpus-gate.md"
    cid = TIER_CRITERION[tier]
    for line in doc.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {cid} |"):
            m = re.search(r"≥\s*([0-9.]+)\s*%", line)
            if m:
                return float(m.group(1)) / 100.0
    raise ValueError(f"no threshold for {tier} ({cid}) in {doc.name}")


@dataclass
class Results:
    records: List[dict]
    full_run: bool = False
    meta: Dict = field(default_factory=dict)

    def rate(self, tier: str) -> float:
        p, n = rate_of(self.records, tier)
        return p / n if n else 0.0

    def count(self, category: str) -> int:
        return sum(1 for r in self.records if r.get("category") == category or _top(r.get("category", "")) == category)


def load_results(src: Optional[Path] = None) -> Results:
    from . import results

    doc = results.load(src)
    return Results(doc.get("records", []), bool(doc.get("full_run")),
                   {k: v for k, v in doc.items() if k != "records"})


def _pct(p: int, n: int) -> str:
    return f"{100.0 * p / n:.1f} % ({p}/{n})" if n else "n/a (0)"


def _generated_lines(raw) -> List[str]:
    """State the stored clock. Never substitute the time this function runs."""
    if raw is None or raw == "":
        return ["Generated: not stored in this results file. No date, time, or zone is stated."]
    text = str(raw)
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z", text)
    if not m:
        return [
            f"Generated: `{text}`. This value is not a UTC timestamp of the form "
            "YYYY-MM-DDTHH:MM:SSZ, so no zone conversion is stated."
        ]
    import datetime as _dt

    try:
        utc = _dt.datetime(
            int(m.group(1)), int(m.group(2)), int(m.group(3)),
            int(m.group(4)), int(m.group(5)), int(m.group(6)),
            tzinfo=_dt.timezone.utc,
        )
    except ValueError:
        return [
            f"Generated: `{text}`. This value is not a UTC timestamp of the form "
            "YYYY-MM-DDTHH:MM:SSZ, so no zone conversion is stated."
        ]
    shanghai = utc.astimezone(_dt.timezone(_dt.timedelta(hours=8)))
    shown = shanghai.strftime("%Y-%m-%d %H:%M:%S")
    return [
        f"Generated: `{text}` (UTC). The same instant is {shown} Asia/Shanghai (UTC+8). "
        "This is the stored `generated` field, not the time this markdown was written."
    ]


def _provenance_lines(meta: dict) -> List[str]:
    """Explain fields this results dict actually carries. The sample stride is not one of them."""
    lines = ["## Run record", ""]
    commit = meta.get("commit") if "commit" in meta else None
    if commit:
        lines.append(
            f"Run commit: `{commit}`. This is the `commit` field stored with these records. "
            "It identifies the run that produced them, not a later repository tip."
        )
    else:
        lines.append("Run commit: not stored in this results file.")
    lines.extend(_generated_lines(meta.get("generated") if "generated" in meta else None))
    if "full_run" not in meta:
        lines.append("full_run metadata: not stored in this results file.")
    elif meta.get("full_run"):
        lines.append("full_run metadata: yes. This file is marked as a full run.")
    else:
        lines.append("full_run metadata: no. This file is marked as a sample.")
    lines.append("Sample stride: not stored in this results file. The stride is unknown.")
    if "timeout" not in meta or meta.get("timeout") in (None, ""):
        lines.append("timeout metadata: not stored in this results file.")
    else:
        lines.append(f"timeout metadata: {meta.get('timeout')} s. This is the stored `timeout` field.")
    lines.append(
        "The tables below count records in this results file only. "
        "Do not infer from them a compatibility rate for arbitrary MATLAB projects."
    )
    lines.append("")
    return lines


def _counting_lines() -> List[str]:
    """Describe ``excluded`` and ``tier_outcome`` as they are implemented."""
    return [
        "A tier rate is the pair `rate_of` returns: successes over counted records. "
        "It is not the category tally further down, and it is not a compatibility rate for arbitrary MATLAB projects.",
        "",
        "`excluded` drops a record from T0, T1, T2, and T3 when the category text before the first `:` is "
        "`corpus-noise`. For T1, T2, and T3 it also drops a record when that prefix is `toolbox` or `io-env`. "
        "T0 does not drop `toolbox` or `io-env`.",
        "",
        "After that drop, `tier_outcome` counts a record only when its tier field (`t0`, `t1`, `t2`, or `t3`) "
        "is `pass`, `error`, `timeout`, or `crash`. The numerator counts only `pass`. "
        "`error`, `timeout`, and `crash` stay in the denominator. "
        "Any other tier-field text, and a missing tier field, is outside the denominator.",
        "",
    ]


def render(records: List[dict], previous: Optional[List[dict]] = None, meta: Optional[dict] = None) -> str:
    """Markdown dashboard: tier pass rates (overall and per source), categories, top failure groups."""
    from . import triage

    meta = meta or {}
    out = ["# Corpus report (M12)", "",
           "Generated by `python -m openmatlab.qa.corpus report` from `docs/corpus/results.json`. "
           "Do not edit by hand.", ""]
    if meta:
        out += _provenance_lines(meta)
    out += ["## Pass rate by tier", ""]
    out += _counting_lines()
    out += ["| Tier | Pass rate |", "|---|---|"]
    for t in TIERS:
        out.append(f"| {t} | {_pct(*rate_of(records, t))} |")
    sources = sorted({r.get("source", "") for r in records})
    out += ["", "## Pass rate by source", "", "| Source | Entries | " + " | ".join(TIERS) + " |",
            "|---|---|" + "---|" * len(TIERS)]
    for s in sources:
        rs = [r for r in records if r.get("source", "") == s]
        out.append(f"| {s or '-'} | {len(rs)} | " + " | ".join(_pct(*rate_of(rs, t)) for t in TIERS) + " |")
    cats = Counter(r.get("category", "") or "-" for r in records)
    out += ["", "## Categories", "",
            "A `pass` row counts records whose `category` string is `pass`. "
            "That count is not a tier rate, and it is not a compatibility rate for arbitrary MATLAB projects.",
            "",
            "| Category | Entries |", "|---|---|"]
    out += [f"| `{c}` | {n} |" for c, n in sorted(cats.items(), key=lambda kv: (-kv[1], kv[0]))]
    groups = triage.group(records)
    out += ["", "## Top failure groups", "", "Deduplicated by `(category, key)`; filed as `corpus` issues.", "",
            "| Category | Key | Entries | Example |", "|---|---|---|---|"]
    for g in groups[:40]:
        key = g.key.replace("|", "\\|")[:80]
        out.append(f"| `{g.category}` | `{key}` | {g.count} | `{g.ids[0]}` |")
    if previous is not None:
        reg = regressions(records, previous)
        out += ["", "## Regressions (pass -> fail)", ""]
        out += [f"- `{i}`" for i in reg] or ["None."]
    return "\n".join(out) + "\n"


def report_path() -> Path:
    return repo_root() / "docs" / "corpus" / "REPORT.md"

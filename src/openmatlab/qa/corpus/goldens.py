"""T3 golden oracle (M12 C08, Epic C-E5 #765).

Compares a script's stdout with a golden. Two golden sources are allowed under Shaw's
2026-10-17 approval ("都按照matlab文档来"):

1. **MATLAB transcript** — command-window output the author pasted under ``>>`` prompts
   (the text C03 de-prompting drops). Source tag ``golden:matlab``.
2. **Octave-produced at run time** — Octave stdout for the same script, only when a
   MATLAB documentation URL is attached for the behaviour under test. Source tag
   ``golden:octave`` plus the doc URL. Hashes / pass-fail / counts only; never commit
   Octave output or expected values. Where Octave differs from documented MATLAB, the
   entry is a dialect exclusion (never a pass).

Normalisation (fixed in advance): whitespace and blank lines; ``Columns N through M``
wrap headers (terminal width); a sign separated from its number. Numbers compare with
relative tolerance ``GOLDEN_RTOL``, or, when both are printed with decimals at different
precisions (the session's ``format`` is not in the code), at the coarser of the two
precisions. Integer and exponent displays get no rounding. Display-style differences
(cell or struct layout) are failures. Scripts whose output depends on the clock, the
random generator, typed input or the host (:data:`NONDETERMINISTIC`) have no golden.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

GOLDEN_RTOL = 1e-10

_NUM = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?i?$")
# Output that cannot be a golden: it depends on the clock, the random generator or typed input.
NONDETERMINISTIC = re.compile(
    r"\b(rand|randn|randi|randperm|rng|clock|now|date|datestr|datetime|tic|toc|cputime|"
    r"input|keyboard|getenv|pwd|memory|version|ver|computer|tempname)\b"
)
_WRAP = re.compile(r"^\s*Columns?\s+\d+(\s+(through|and|to)\s+\d+)?:?\s*$", re.M)


def golden_source(notes: List[str], code: str) -> str:
    """``"matlab"`` when the entry's transcript came from MATLAB ``>>`` prompts, else ``""``."""
    if "deprompted" not in notes:
        return ""
    prompts = re.findall(r"^\s*(>>|octave:\d+>|>(?=\s))", code, re.M)
    return "matlab" if prompts and all(p == ">>" for p in prompts) else ""


def nondeterministic(code: str) -> str:
    """The first clock/random/input call in ``code`` (outside strings and comments), or ``""``."""
    from .classify import _without_strings

    m = NONDETERMINISTIC.search(_without_strings(code))
    return m.group(1) if m else ""


def _tokens(text: str) -> List[str]:
    text = _WRAP.sub("", text)  # column-wrap headers depend on the terminal width
    text = re.sub(r"(?<![\w.)\]])([-+])\s+(?=[\d.])", r"\1", text)  # "- 6i" and "-6i" are one value
    return [t for t in re.split(r"\s+", text) if t]


def _decimals(tok: str) -> Optional[int]:
    m = re.match(r"^[-+]?\d*\.(\d*)$", tok.rstrip("i"))
    return len(m.group(1)) if m else None


def _num_equal(x: str, y: str) -> bool:
    if x.endswith("i") != y.endswith("i"):
        return False
    fx, fy = float(x.rstrip("i")), float(y.rstrip("i"))
    if abs(fx - fy) <= GOLDEN_RTOL * max(abs(fx), abs(fy)):
        return True
    dx, dy = _decimals(x), _decimals(y)
    if dx is None or dy is None or "e" in (x + y).lower():
        return False  # integer display or exponent: no rounding is forgiven
    d = min(dx, dy)  # the session's `format` is not in the code: compare at the coarser precision
    return d > 0 and abs(fx - fy) <= 0.5 * 10.0 ** -d * (1 + 1e-9)


def golden_match(stdout: str, golden: str) -> Tuple[bool, str]:
    """Token comparison (see the module docstring for the normalisation)."""
    a, b = _tokens(stdout or ""), _tokens(golden or "")
    for i, (x, y) in enumerate(zip(a, b)):
        if x == y or (_NUM.match(x) and _NUM.match(y) and _num_equal(x, y)):
            continue
        return False, f"token {i + 1} differs"
    if len(a) != len(b):
        return False, f"{len(a)} output tokens, golden has {len(b)}"
    return True, ""

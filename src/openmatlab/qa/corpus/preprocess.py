"""Deterministic corpus preprocessing (M12 C03, Epic #763).

Real-world snippets are often not runnable files as published. Three pure, deterministic
transforms turn them into what their author ran, without guessing at semantics:

* **Transcript de-prompting.** A block that contains command-window prompts (``>> code``)
  keeps only the prompted code (plus the continuation lines of an open ``...`` or block
  statement) and drops the echoed output. The dropped output is kept as ``transcript`` for
  the T3 golden oracle (C-E5).
* **Function-file detection.** A file whose first statement is ``function`` and that has no
  script code after its functions is a function file: it is parsed (T0) but not run as a
  script (T1).
* **``input`` fixtures.** Every ``input(...)``/``keyboard`` call gets a deterministic answer
  (``'s'`` form -> ``hello``, numeric form -> ``5``), followed by spare answers, so a script
  that prompts does not fail on end-of-input.

The same input always gives the same output; nothing here touches the network or the clock.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

PROMPT = re.compile(r"^\s*(>>|octave:\d+>)\s?(.*)$")
_OPEN = re.compile(r"^\s*(for|parfor|while|if|switch|try|function|do)\b")
_END = re.compile(r"(^|[\s;,])(end|endfor|endwhile|endif|endswitch|end_try_catch|endfunction|until)\b\s*[;,]?\s*(%.*)?$")
_INPUT = re.compile(r"\binput\s*\(([^()]*(?:\([^()]*\))?[^()]*)\)")
SPARE_ANSWERS = 20


@dataclass
class Prepared:
    code: str
    role: str  # "script" | "function"
    transcript: str = ""  # dropped command-window output (golden candidate)
    input_lines: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def _strip_comment(line: str) -> str:
    out, q = [], False
    for i, ch in enumerate(line):
        if ch == "'" and not q and i and (line[i - 1].isalnum() or line[i - 1] in ")]}'_."):
            out.append(ch)  # transpose, not a quote
            continue
        if ch in "'\"":
            q = not q
        if ch == "%" and not q:
            break
        out.append(ch)
    return "".join(out).rstrip()


def _depth_delta(line: str) -> int:
    s = _strip_comment(line)
    if not s.strip():
        return 0
    d = 0
    for part in re.split(r"[;,]", s):
        if _OPEN.match(part):
            d += 1
        if re.search(r"(^|\s)(end|endfor|endwhile|endif|endswitch|end_try_catch|endfunction|until)\b\s*$", part):
            d -= 1
    return d


def deprompt(code: str) -> tuple[str, str]:
    """Return ``(code, transcript)``; unchanged when the text has no prompts."""
    lines = code.splitlines()
    if not any(PROMPT.match(ln) for ln in lines):
        return code, ""
    kept, dropped = [], []
    depth, cont = 0, False
    for ln in lines:
        m = PROMPT.match(ln)
        if m:
            body = m.group(2)
            kept.append(body)
            depth = max(0, depth + _depth_delta(body))
            cont = body.rstrip().endswith("...")
        elif depth > 0 or cont:
            kept.append(ln)
            depth = max(0, depth + _depth_delta(ln))
            cont = ln.rstrip().endswith("...")
        else:
            dropped.append(ln)
    return "\n".join(kept) + "\n", "\n".join(dropped).strip("\n")


def _statements(code: str):
    for ln in code.splitlines():
        s = _strip_comment(ln).strip()
        if s:
            yield s


def role_of(code: str) -> str:
    """``function`` for a pure function file, else ``script``."""
    stmts = list(_statements(code))
    if not stmts or not re.match(r"function\b", stmts[0]):
        return "script"
    depth, uses_end = 0, any(re.match(r"(end|endfunction)\b\s*;?$", s) for s in stmts)
    for s in stmts:
        if re.match(r"function\b", s):
            if depth and not uses_end:
                depth = 0
            depth = 1 if not uses_end else depth + 1
            continue
        if not uses_end:
            continue
        depth += _depth_delta(s) if not re.match(r"function\b", s) else 0
        if depth <= 0 and not re.match(r"(end|endfunction)\b", s):
            return "script"  # code after the last function end: a script with local functions
    return "function"


def input_fixture(code: str) -> List[str]:
    answers = []
    for m in _INPUT.finditer(code):
        answers.append("hello" if re.search(r",\s*['\"]s['\"]\s*$", m.group(1)) else "5")
    if re.search(r"\bkeyboard\b", code):
        answers.append("dbcont")
    if not answers:
        return []
    return answers + ["5"] * SPARE_ANSWERS


def prepare(code: str) -> Prepared:
    notes = []
    body, transcript = deprompt(code)
    if transcript or body != code:
        notes.append("deprompted")
    role = role_of(body)
    if role == "function":
        notes.append("function-file")
    fixture = input_fixture(body) if role == "script" else []
    if fixture:
        notes.append("input-fixture")
    return Prepared(code=body, role=role, transcript=transcript, input_lines=fixture, notes=notes)


@dataclass
class Normalized:
    """``prepare`` result in the shape the corpus pipeline and the C03 criterion use."""

    code: str
    kind: str  # "script" | "function"
    expected_stdout: Optional[str]  # transcript output (T3 golden candidate) or None
    stdin_fixture: Optional[List[str]]  # answers for input()/keyboard, or None
    notes: List[str]


def normalize(code: str) -> Normalized:
    p = prepare(code)
    return Normalized(code=p.code, kind=p.role, expected_stdout=p.transcript if "deprompted" in p.notes else None,
                      stdin_fixture=p.input_lines or None, notes=p.notes)


def results_path():
    from openmatlab.qa.paths import repo_root

    return repo_root() / "docs" / "corpus" / "results.json"


def noise_rate(records, source: str = "rosetta") -> float:
    """Share of a source's script entries whose outcome is ``corpus-noise``."""
    rows = [r for r in records if r.get("source") == source and r.get("kind") == "script"]
    return sum(r.get("category") == "corpus-noise" for r in rows) / max(1, len(rows))


def pilot_noise_rate(path=None) -> float:
    """Noise rate of the Rosetta script set (the pilot population) in the committed full run."""
    import json

    doc = json.loads((path or results_path()).read_text(encoding="utf-8"))
    return noise_rate(doc["records"])

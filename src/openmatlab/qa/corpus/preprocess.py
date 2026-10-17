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

PROMPT = re.compile(r"^\s*(>>|octave:\d+>|>(?=\s))\s?(.*)$")  # MATLAB, numbered and bare Octave prompts
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


def _bracket_delta(line: str) -> int:
    """Net open ``[``/``{``/``(`` count outside strings and comments (multi-line literals)."""
    s = re.sub(r"(?<![\w)\]}.'])'(?:[^'\n]|'')*'", "''", _strip_comment(line))
    s = re.sub(r'"[^"\n]*"', '""', s)
    return sum(s.count(c) for c in "[{(") - sum(s.count(c) for c in "]})")


def deprompt(code: str) -> tuple[str, str]:
    """Return ``(code, transcript)``; unchanged when the text has no prompts."""
    lines = code.splitlines()
    if not any(PROMPT.match(ln) for ln in lines):
        return code, ""
    kept, dropped = [], []
    depth, cont, brackets = 0, False, 0
    for ln in lines:
        m = PROMPT.match(ln)
        if m:
            body = m.group(2)
            kept.append(body)
            depth = max(0, depth + _depth_delta(body))
            brackets = max(0, _bracket_delta(body))
            cont = body.rstrip().endswith("...")
        elif depth > 0 or cont or brackets > 0:
            kept.append(ln)
            depth = max(0, depth + _depth_delta(ln))
            brackets = max(0, brackets + _bracket_delta(ln))
            cont = ln.rstrip().endswith("...")
        else:
            dropped.append(ln)
    return "\n".join(kept) + "\n", "\n".join(dropped).strip("\n")


_DISPLAY_HEADER = re.compile(r"^\s*(ans|[A-Za-z_]\w*)\s*=\s*$")
_DISPLAY_ROW = re.compile(r"^\s*$|^\s*(Columns?\s+\d+.*|[-+\d.eEiInfNa\s:/*]+|\{.*\}|\[.*\]|'[^']*'(\s+'[^']*')*|"
                          r"\S.*\[\d+x\d+ \w+\].*|<\d+x\d+ \w+>|(true|false)(\s+(true|false))*|\d+x\d+ \w+ array.*|"
                          r"[A-Za-z]\w*: .*)$")


def strip_echo(code: str) -> tuple[str, str]:
    """Drop command-window echo pasted without prompts (``name =`` header plus display rows)."""
    lines = code.splitlines()
    if not any(_DISPLAY_HEADER.match(ln) for ln in lines):
        return code, ""
    kept, dropped, in_out = [], [], False
    for i, ln in enumerate(lines):
        if _DISPLAY_HEADER.match(ln):
            in_out = True
        elif in_out and not _DISPLAY_ROW.match(ln):
            in_out = False
        (dropped if in_out else kept).append(ln)
    return "\n".join(kept).rstrip("\n") + "\n", "\n".join(dropped).strip("\n")


_KEYWORDS = {"if", "else", "elseif", "end", "for", "parfor", "while", "switch", "case", "otherwise", "try", "catch",
             "function", "return", "break", "continue", "global", "persistent", "classdef", "properties", "methods",
             "events", "enumeration", "spmd", "do", "until"}
_CONSTANTS = {"i", "j", "Inf", "inf", "NaN", "nan", "ans", "varargin", "varargout", "nargin", "nargout", "end", "true",
              "false", "pi", "eps", "NA", "e",
              # MATLAB functions commonly used as bare values; never call them context
              "matlabroot", "version", "pwd", "date", "clock", "now", "cputime", "userpath", "tempdir", "path"}
_KNOWN: Optional[set] = None


def known_functions() -> set:
    """Names OpenMATLAB resolves without a file (builtins, intrinsics), lower-cased."""
    global _KNOWN
    if _KNOWN is None:
        from openmatlab.libs.function_intrinsics import INTRINSICS
        from openmatlab.runtime.session import Session

        _KNOWN = {n.lower() for n in Session.create_default().functions.builtins} | {n.lower() for n in INTRINSICS}
    return _KNOWN


def _clean(code: str) -> List[str]:
    out = []
    for ln in code.splitlines():
        ln = re.sub(r'"[^"\n]*"', '""', ln)
        ln = re.sub(r"(?<![\w)\]}.'])'(?:[^'\n]|'')*'", "''", ln)
        out.append(re.sub(r"%.*$", "", ln))
    return out


def free_reads(code: str, siblings=()) -> List[str]:
    """Identifiers read as values (operands/arguments) that nothing in the file or the engine defines.

    Conservative: a name that is ever called with ``(``, used as a whole statement (command
    form), used alone on an assignment right-hand side, or field-accessed is never reported,
    because it may be a function OpenMATLAB lacks (``missing-builtin``) rather than context.
    """
    lines = _clean(code)
    text = "\n".join(lines)
    assigned = set(re.findall(r"(?:^|[;,])\s*([A-Za-z_]\w*)\s*(?:\([^=\n]*\)|\{[^=\n]*\}|\.[\w.]+)?\s*=(?!=)", text, re.M))
    for grp in re.findall(r"\[([^\]\n]*)\]\s*=(?!=)", text):
        assigned.update(re.findall(r"[A-Za-z_]\w*", grp))
    assigned.update(re.findall(r"\b(?:for|parfor)\s*\(?\s*([A-Za-z_]\w*)\s*=", text))
    for sig in re.findall(r"^\s*function\b([^\n]*)", text, re.M):
        assigned.update(re.findall(r"[A-Za-z_]\w*", sig))
    assigned.update(re.findall(r"\b(?:global|persistent)\s+([\w ]+)", text) and
                    re.findall(r"[A-Za-z_]\w*", " ".join(re.findall(r"\b(?:global|persistent)\s+([\w ]+)", text))))
    assigned.update(re.findall(r"@\(([^)]*)\)", text) and re.findall(r"[A-Za-z_]\w*", " ".join(re.findall(r"@\(([^)]*)\)", text))))
    called = set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", text)) | set(re.findall(r"@([A-Za-z_]\w*)", text))
    command = set(re.findall(r"(?:^|(?<=[;,]))\s*([A-Za-z_]\w*)\s*(?=[;,]|$|\s+[A-Za-z'\-])", text, re.M))
    for args in re.findall(r"(?:^|(?<=[;,]))\s*[A-Za-z_]\w*((?:[ \t]+[A-Za-z_]\w*)+)[ \t]*(?=[;,]|$)", text, re.M):
        command.update(args.split())  # command-syntax arguments: hold on, axis equal, format long
    rhs_alone = set(re.findall(r"=\s*([A-Za-z_]\w*)\s*(?:[;,]|$)", text, re.M))
    fielded = set(re.findall(r"\b([A-Za-z_]\w*)\s*\.(?!['*/^\\])", text))
    known = known_functions()
    out = []
    for name in re.findall(r"(?<![\w.@'])([A-Za-z_]\w*)\b(?!\s*\()", text):
        if (name in assigned or name in called or name in command or name in rhs_alone or name in fielded
                or name in _KEYWORDS or name in _CONSTANTS or name.lower() in known or name in siblings or name in out):
            continue
        out.append(name)
    return out


def _statements(code: str):
    for ln in code.splitlines():
        s = _strip_comment(ln).strip()
        if s:
            yield s


def role_of(code: str) -> str:
    """``function`` for a pure function file, else ``script``."""
    stmts = list(_statements(code))
    if stmts and re.match(r"classdef\b", stmts[0]):
        return "function"  # a class definition file: parsed (T0), never run as a script
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


def prepare(code: str, siblings=()) -> Prepared:
    from .classify import dialect_marker

    notes = []
    body, transcript = deprompt(code)
    if transcript or body != code:
        notes.append("deprompted")
    else:
        body, transcript = strip_echo(code)
        if transcript:
            notes.append("echo-stripped")
    role = role_of(body)
    dialect = dialect_marker(body)
    if dialect:
        return Prepared(code=body, role="noise", transcript=transcript, notes=notes + ["dialect:" + dialect])
    if role == "script":
        free = free_reads(body, siblings)
        if free:
            return Prepared(code=body, role="noise", transcript=transcript, notes=notes + ["fragment:" + ",".join(free[:5])])
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
    return Normalized(code=p.code, kind=p.role, expected_stdout=p.transcript if p.transcript else None,
                      stdin_fixture=p.input_lines or None, notes=p.notes)


def results_path():
    from openmatlab.qa.paths import repo_root

    return repo_root() / "docs" / "corpus" / "results.json"


def noise_rate(records, source: str = "rosetta") -> float:
    """Residual noise: share of a source's script entries that preprocessing passed on as runnable
    but whose run still failed for a sample reason (``corpus-noise`` found only at run time).

    Entries preprocessing itself sets aside (``role == "noise"``: dialect, fragment) are
    de-noised, not residual; they are counted by :func:`filtered_rate`.
    """
    rows = [r for r in records if r.get("source") == source and r.get("kind") == "script"]
    return sum(r.get("category") == "corpus-noise" and r.get("role") != "noise" for r in rows) / max(1, len(rows))


def filtered_rate(records, source: str = "rosetta") -> float:
    rows = [r for r in records if r.get("source") == source and r.get("kind") == "script"]
    return sum(r.get("role") == "noise" for r in rows) / max(1, len(rows))


def pilot_noise_rate(path=None) -> float:
    """Noise rate of the Rosetta script set (the pilot population) in the committed full run."""
    import json

    doc = json.loads((path or results_path()).read_text(encoding="utf-8"))
    return noise_rate(doc["records"])

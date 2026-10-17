"""T2 self-check tier (M12 C07, Epic C-E5 #765): scripts' own assertions, run at run time.

Sources of self-checks (all fetched into the local cache, never committed):

* **Octave** ``%!assert`` / ``%!test`` blocks (GPL-3.0-or-later, pinned). Each block is one T2
  record ``octave/<dir>/<name>#<k>``. Only pass/fail, the block's sha256, counts, an error
  identifier and a redacted message (digits and quoted text removed) are kept: block source
  and expected values are never written to the results. ``%!shared`` initialisation runs
  before every later block; ``%!function`` helpers are staged as function files. Other block
  kinds (``%!error``, ``%!warning``, ``%!testif``, ``%!xtest``, ``%!demo``, ``%!fail``) are
  counted as skipped. Octave-only syntax in a block is normalised to MATLAB at run time by
  :func:`octave_to_matlab` (``#`` comments, ``!``/``!=``, ``endif``-style keywords, ``"..."``
  char strings, ``x += y``, ``printf``).
* **chebfun** ``tests/`` (BSD-3-Clause): the driver asserts ``all(pass(:))`` of the test's
  own result vector, so T2 = T1 for ``selftest`` entries.
* **matlab2tikz** bundled ACID test suite (BSD-2-Clause): a scene's own status, so T2 = T1
  for ``acid-scene`` entries (T3 would be its reference TikZ hashes; not built here).
"""

from __future__ import annotations

import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from . import manifest as M
from .runner import run_one

COUNTED = ("assert", "test")
KEYWORDS = ("assert", "test", "xtest", "testif", "shared", "function", "endfunction", "error", "warning", "demo",
            "fail")
MSG_CAP = 160
# Functions whose Octave tests are outside a MATLAB T2 rate (same exclusion model as T1, report.excluded).
OCTAVE_ONLY = frozenset("""accumdim asctime bincoeff bug_report center citation common_size commutation_matrix cstrcat
ctime discrete_cdf discrete_inv discrete_pdf discrete_rnd duplication_matrix empirical_cdf empirical_inv empirical_pdf
empirical_rnd gls housh index info is_leap_year isdefinite jupyter_notebook kendall list_primes ls_command meansq
nthargout ols ostrsplit parseparams polyaffine polygcd polyout polyreduce postpad prepad ppjumps qzhess ranks rindex
rotdim run_count runlength spearman splinefit statistics strtrunc substr untabify vech""".split())
TOOLBOX_TESTS = {"statistics": frozenset("iqr kurtosis skewness mad moment prctile quantile range zscore corr".split()),
                 "phased": frozenset("rotx roty rotz".split()),
                 "symbolic": frozenset({"symvar"})}
ENV_TESTS = frozenset("""bunzip2 copyfile delete dir edit fileattrib gunzip ls menu mex mkdir movefile news open pack perl
publish python recycle tar untar unzip unpack what zip memory dos unix grabcode license""".split())


def excluded_category(name: str) -> str:
    """Category for a tested function outside the MATLAB T2 rate, else ''."""
    if name in OCTAVE_ONLY:
        return "toolbox:octave-only"
    for tb, fs in TOOLBOX_TESTS.items():
        if name in fs:
            return "toolbox:" + tb
    return "io-env" if name in ENV_TESTS else ""


T2LIB = Path(__file__).with_name("t2lib")
_KW = re.compile(r"^%!(" + "|".join(sorted(KEYWORDS, key=len, reverse=True)) + r")\b(.*)$")


@dataclass
class Block:
    kind: str
    text: str  # code (for assert: the full ``assert ...`` call)
    index: int = 0
    shared: List[str] = field(default_factory=list)  # %!shared code that precedes this block


@dataclass
class Parsed:
    blocks: List[Block]
    functions: List[str]
    skipped: int


def parse_blocks(src: str) -> Parsed:
    raw: List[List] = []  # [kind, header_rest, [body lines]]
    for line in src.splitlines():
        if not line.startswith("%!"):
            continue
        m = _KW.match(line)
        if m:
            raw.append([m.group(1), m.group(2), []])
        elif raw:
            raw[-1][2].append(line[2:])
    blocks, funcs, skipped, shared, k = [], [], 0, [], 0
    for kind, rest, body in raw:
        if kind == "shared":
            names = rest.split("#")[0].split("%")[0].replace(",", " ").split()
            shared = [f"{n} = [];" for n in names] + body
        elif kind == "function":
            funcs.append("function" + rest + "\n" + "\n".join(body) + "\nend\n")
        elif kind == "endfunction":
            continue
        elif kind in COUNTED:
            k += 1
            text = ("assert" + rest + "\n" + "\n".join(body)) if kind == "assert" else (rest + "\n" + "\n".join(body))
            blocks.append(Block(kind, text, k, list(shared)))
        else:
            skipped += 1
    return Parsed(blocks, funcs, skipped)


_END = re.compile(r"\b(endif|endwhile|endfor|endfunction|endswitch|end_try_catch|end_unwind_protect|endparfor)\b")
_OPEQ = re.compile(r"^(\s*)([A-Za-z_][\w.]*(?:\([^=]*\))?)\s*([-+*/])=(?!=)\s*(.+?)\s*(;?)\s*$")
_ESC = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'", "r": "\r", "a": "\a", "0": "\0"}


def _dq_to_char(body: str) -> str:
    out, i = [], 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            e = body[i + 1]
            out.append(_ESC.get(e, "\\" + e))
            i += 2
            continue
        if c == '"' and i + 1 < len(body) and body[i + 1] == '"':
            out.append('"')
            i += 2
            continue
        out.append(c)
        i += 1
    s = "".join(out)
    if any(ch in s for ch in "\n\t\r\a\0"):  # control characters: build with char codes
        parts, cur = [], ""
        for ch in s:
            if ch in "\n\t\r\a\0":
                if cur:
                    parts.append("'" + cur.replace("'", "''") + "'")
                    cur = ""
                parts.append(f"char({ord(ch)})")
            else:
                cur += ch
        if cur:
            parts.append("'" + cur.replace("'", "''") + "'")
        return "[" + ", ".join(parts) + "]"
    return "'" + s.replace("'", "''") + "'"


def _line(line: str) -> str:
    out, i, n, prev = [], 0, len(line), ""
    while i < n:
        c = line[i]
        if c in "#%":
            if c == "#" and line[i:i + 2] in ("#{", "#}"):
                break
            break  # comment to end of line
        if c == "'":
            if prev and (prev.isalnum() or prev in ")]}_.'"):
                out.append(c)
                prev = c
                i += 1
                continue
            j = i + 1
            while j < n:
                if line[j] == "'" and j + 1 < n and line[j + 1] == "'":
                    j += 2
                    continue
                if line[j] == "'":
                    break
                j += 1
            out.append(line[i:j + 1])
            prev = "'"
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == '"' and j + 1 < n and line[j + 1] == '"':
                    j += 2
                    continue
                if line[j] == '"':
                    break
                j += 1
            out.append(_dq_to_char(line[i + 1:j]))
            prev = "'"
            i = j + 1
            continue
        if c == "!":
            out.append("~")
            prev = "~"
            i += 1
            continue
        out.append(c)
        if not c.isspace():
            prev = c
        i += 1
    s = "".join(out).rstrip()
    s = _END.sub("end", s)
    s = re.sub(r"\bprintf\s*\(", "fprintf(", s)
    s = re.sub(r"\bunwind_protect_cleanup\b", "%", s)
    m = _OPEQ.match(s)
    if m and m.group(4):
        s = f"{m.group(1)}{m.group(2)} = {m.group(2)} {m.group(3)} ({m.group(4)}){m.group(5)}"
    s = re.sub(r"^(\s*)unwind_protect\s*$", r"\1", s)
    return s


def octave_to_matlab(code: str) -> str:
    """Best-effort runtime normalisation of Octave-only syntax in a test block to MATLAB."""
    lines, in_block = [], False
    for line in code.splitlines():
        st = line.strip()
        if st in ("%{", "#{"):
            in_block = True
            continue
        if st in ("%}", "#}"):
            in_block = False
            continue
        if not in_block:
            lines.append(re.sub(r"\bassert\b(?=\s*\()", "t2_assert", _line(line)))
    return "\n".join(lines)


def redact(msg: str) -> str:
    """Engine message without literal values: quoted text other than names and digits removed."""
    msg = re.sub(r"'([^']*)'", lambda m: m.group(0) if re.fullmatch(r"[A-Za-z_]\w*", m.group(1)) else "'…'", msg or "")
    msg = re.sub(r"\d+(?:\.\d+)?(?:e[-+]?\d+)?", "#", msg)
    return msg.splitlines()[0][:MSG_CAP] if msg else ""


def _driver(n: int, out: Path) -> str:
    o = str(out).replace("'", "''")
    lines = [f"fid__ = fopen('{o}', 'w');"]
    for k in range(1, n + 1):
        lines += [f"fprintf(fid__, 'S {k}\\n');",
                  "try",
                  f"  t2blk_{k}();",
                  f"  fprintf(fid__, 'P {k}\\n');",
                  "catch err__",
                  f"  fprintf(fid__, 'F {k} %s\\t%s\\n', err__.identifier, strrep(strrep(err__.message, char(10), ' '), char(13), ' '));",
                  "end"]
    lines.append("fclose(fid__);")
    return "\n".join(lines) + "\n"


def run_octave_file(e: M.Entry, cache: Path, timeout: float) -> List[dict]:
    """One T2 record per counted block of an Octave test file (pass/fail and hashes only)."""
    src = cache / e.file
    base = {"source": e.source, "kind": "octave-block", "t0": "n/a", "t1": "n/a"}
    if not src.is_file():
        return []
    p = parse_blocks(src.read_text(encoding="utf-8", errors="replace"))
    if not p.blocks:
        return []
    skip = excluded_category(e.id.rsplit("/", 1)[-1])
    if skip:  # not run: excluded from the T2 rate like toolbox / io-env entries in T1
        return [dict(base, id=f"{e.id}#{b.index}", role=b.kind, sha256=M.sha256(b.text), t2="n/a", status="n/a",
                     category=skip, key=skip) for b in p.blocks]
    stage = Path(tempfile.mkdtemp(prefix="omt2-"))
    try:
        for b in p.blocks:
            body = octave_to_matlab("\n".join(b.shared) + "\n" + b.text)
            (stage / f"t2blk_{b.index}.m").write_text(f"function t2blk_{b.index}()\n{body}\nend\n", encoding="utf-8")
        shutil.copyfile(T2LIB / "t2_assert.m", stage / "t2_assert.m")
        for f in p.functions:
            code = octave_to_matlab(f)
            m = re.search(r"function\s+(?:\[[^\]]*\]\s*=\s*|\w+\s*=\s*)?([A-Za-z_]\w*)", code)
            if m:
                (stage / f"{m.group(1)}.m").write_text(code, encoding="utf-8")
        outf = Path(tempfile.gettempdir()) / f"omt2-{uuid.uuid4().hex}.txt"
        drv = stage / "t2_driver.m"
        drv.write_text(_driver(len(p.blocks), outf), encoding="utf-8")
        r = run_one(drv, timeout=timeout * 3, name=e.id).to_json()
        seen = {}
        if outf.is_file():
            for line in outf.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.split(" ", 2)
                if len(parts) >= 2 and parts[1].isdigit():
                    seen[int(parts[1])] = (parts[0], parts[2] if len(parts) > 2 else "")
            outf.unlink()
        recs = []
        for b in p.blocks:
            st, rest = seen.get(b.index, ("", ""))
            rec = dict(base, id=f"{e.id}#{b.index}", role=b.kind, sha256=M.sha256(b.text))
            if st == "P":
                rec.update(t2="pass", status="pass", category="pass", key="")
            elif st == "F":
                eid, _, msg = rest.partition("\t")
                rec.update(t2="error", status="error", error_id=eid, message=redact(msg), category="semantics-diff",
                           key=_key(eid, msg))
            elif st == "S" or r["status"] in ("timeout", "crash"):
                cat = "timeout" if r["status"] == "timeout" else "internal-crash" if r["status"] == "crash" else "semantics-diff"
                rec.update(t2=r["status"] if r["status"] != "pass" else "error", status=r["status"], category=cat,
                           key=cat, message=redact(r["message"]))
            else:
                rec.update(t2="error", status="error", category="semantics-diff", key="driver",
                           message=redact(r["message"]))
            recs.append(rec)
        return recs
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _key(eid: str, msg: str) -> str:
    m = re.search(r"Undefined (?:function or variable|function|variable)[^']*'([A-Za-z_]\w*)'", msg or "")
    if m:
        return f"undefined:{m.group(1)}"
    if (msg or "").startswith("ASSERT") or "assert" in (eid or "").lower() or "Assertion" in (msg or ""):
        return "assert-mismatch"
    return eid or redact(msg)[:60]

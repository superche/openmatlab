"""T2 self-check and T3 golden oracles (M12 C07/C08, Epic C-E5 #765).

**T2 (self-check)** is measured per corpus entry, the same unit as every other tier:

* *chebfun self-tests*: the driver already runs ``pass = test_x(); assert(all(pass(:)))``, so the
  entry's T2 outcome is the driver outcome (all of the test's own checks pass).
* *GNU Octave ``%!`` tests*: :func:`octave_blocks` splits a function file's test blocks;
  ``%!assert`` and ``%!test`` blocks (with their ``%!shared`` set-up and ``%!function`` helpers)
  are translated to MATLAB by :func:`octave_script` and run against **OpenMATLAB's own**
  implementation of the function (the Octave file itself is never on the path). The entry
  passes T2 only when **every** applicable block passes. Blocks that need Octave-only syntax
  or functions are set aside deterministically (:func:`block_dialect`), like the C03 dialect
  rule; ``%!error``/``%!warning``/``%!fail`` (Octave error texts), ``%!testif`` (Octave build
  features), ``%!xtest`` (known Octave failures) and ``%!demo`` are not self-checks of values.
  An entry with no applicable block is ``corpus-noise`` (not counted).

  Octave's ``assert (observed, expected, tol)`` form is not MATLAB's ``assert``; tests call a
  staged clean-room helper (:data:`ASSERT_HELPER`, written for this project from the documented
  interface) instead.

**T3 (golden)** compares a script's stdout with the command-window output its author pasted
under MATLAB ``>>`` prompts (the transcript that C03 de-prompting drops). Whitespace and
blank lines are normalised and numbers compare with a relative tolerance of 1e-10; nothing
else is forgiven. Transcripts under Octave prompts are **not** used as goldens (Octave output
is a golden only with MATLAB documentation evidence, M12 C08), so the set of Octave-sourced
goldens is empty by construction and every entry of it trivially carries a doc link.

No corpus text is stored: records keep counts and token positions only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

RESULT_FILE = "omt2.res"
GOLDEN_RTOL = 1e-10

# ---------------------------------------------------------------- Octave %! blocks

_HEAD = re.compile(r"^%!(\w+)\b ?(.*)$")
SELF_CHECK_KINDS = ("assert", "test")
SKIPPED_KINDS = ("error", "warning", "fail", "testif", "xtest", "demo")
# Octave-only functions and values seen in %! blocks (no MATLAB base equivalent): a block using
# one is Octave dialect. Kept short and explicit; anything else that is missing counts as a failure.
OCTAVE_ONLY = {"columns", "rows", "postpad", "prepad", "print_usage", "nthargout", "isargout", "lookup", "merge",
               "ifelse", "fail", "NA", "isna", "sizeof", "vec", "printf", "puts", "fputs", "fdisp", "index", "rindex",
               "do_string_escapes", "undo_string_escapes", "program_name", "OCTAVE_VERSION", "pkg", "ostrsplit",
               "validatestring_", "isargout", "inputname_", "typecast_", "numel_", "common_size", "sizemax",
               "unwind_protect", "end_unwind_protect", "endfunction", "print_empty_dimensions", "output_precision",
               "save_precision", "struct_levels_to_print", "split_long_rows", "fixed_point_format", "page_screen_output",
               "isguirunning", "have_window_system", "compare_versions", "ispc_", "nproc", "getpid", "argn",
               "mlock", "munlock", "mislocked", "exist_", "warning_ids", "lasterror", "rethrow_", "evalc_",
               "isdeployed_", "dbstack_", "inputParser_", "func2str_", "str2func_", "isvarname_", "toc_", "cputime_",
               "bitshift_", "bincoeff", "nchoosek_", "primes_", "isprime_", "sign_", "mat2str_", "int2str_", "toascii",
               "lower_", "blanks_", "deblank_", "regexptranslate_", "strvcat_", "substr", "strtok_", "validatestring"}


@dataclass
class Block:
    kind: str  # assert | test | shared | function | error | ...
    code: str  # body with the %! markers removed
    line: int  # 1-based line of the block head in the file


def octave_blocks(text: str) -> List[Block]:
    """Split the ``%!`` test blocks of an Octave file (a block runs to the next ``%!keyword`` line)."""
    out: List[Block] = []
    cur: Optional[Block] = None
    for i, ln in enumerate(text.splitlines(), 1):
        if not ln.startswith("%!"):
            cur = None
            continue
        m = _HEAD.match(ln)
        if m:
            cur = Block(m.group(1), m.group(2), i)
            out.append(cur)
        elif cur is not None:
            cur.code += "\n" + ln[2:]
    return out


def _strip_bug_tag(code: str) -> str:
    return re.sub(r"^\s*<[^>\n]*>\s*", "", code)  # %!assert <*12345> (...), %!test <54321>


def _dq_to_sq(code: str) -> Optional[str]:
    """Octave double-quoted strings are char arrays: rewrite escape-free ones as MATLAB char literals."""
    out, i, n = [], 0, len(code)
    while i < n:
        ch = code[i]
        if ch == "'" and not (i and (code[i - 1].isalnum() or code[i - 1] in ")]}'_.")):
            j = i + 1
            while j < n and not (code[j] == "'" and (j + 1 >= n or code[j + 1] != "'")):
                j += 2 if code[j] == "'" else 1
                if code[j - 1] == "\n":
                    return None
            out.append(code[i:j + 1])
            i = j + 1
            continue
        if ch == '"':
            j = code.find('"', i + 1)
            if j < 0:
                return None
            body = code[i + 1:j]
            if "\\" in body or "\n" in body:
                return None
            out.append("'" + body.replace("'", "''") + "'")
            i = j + 1
            continue
        if ch == "%":  # comment to end of line
            j = code.find("\n", i)
            j = n if j < 0 else j
            out.append(code[i:j])
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def block_dialect(code: str) -> str:
    """Why a translated block is Octave dialect, or ``""`` when it is MATLAB."""
    from .classify import _without_strings, dialect_marker

    d = dialect_marker(code)
    if d:
        return d
    clean = _without_strings(code)
    if "#" in clean:  # MATLAB uses '#' only inside text
        return "octave-comment"
    if re.search(r"(?<![=<>~!])=(?!=)[^=;,\n]*?\b[A-Za-z_]\w*\s*=(?!=)", re.sub(r"\([^()]*\)|\{[^{}]*\}|\[[^\[\]]*\]", "", clean)):
        return "octave-chained-assign"
    if re.search(r"[)\]}]\(|\}\{", clean):  # f (x)(2), [1 2](1), c{1}(2): MATLAB indexes once per call

        return "octave-index-chain"
    if "**" in clean:
        return "octave-power"
    if re.search(r"\b__\w+__\b", clean):
        return "octave-internal"
    for name in re.findall(r"[A-Za-z_]\w*", clean):
        if name in OCTAVE_ONLY:
            return "octave-only:" + name
    return ""


@dataclass
class OctavePlan:
    script: str  # MATLAB script
    helpers: dict  # file name -> MATLAB text (assert helper, %!function helpers)
    applicable: int  # self-check blocks that run
    set_aside: List[str] = field(default_factory=list)  # dialect reasons of skipped self-check blocks
    skipped: int = 0  # %!error, %!testif, ... (not self-checks)


_ASSERT_CALL = re.compile(r"(?<![\w.])assert\s*\(")


def _translate(code: str) -> Tuple[Optional[str], str]:
    body = _dq_to_sq(_strip_bug_tag(code))
    if body is None:
        return None, "octave-dquote-escape"
    d = block_dialect(body)
    return (None, d) if d else (body, "")


def octave_script(text: str) -> OctavePlan:
    """Translate the self-check blocks of one Octave file into a MATLAB script plus staged helpers.

    The script appends ``P <i>`` or ``F <i> <identifier>\\t<message>`` per applicable block to
    :data:`RESULT_FILE` as it goes, so a timeout still leaves the finished blocks' verdicts.
    """
    helpers = {"omt2_assert.m": ASSERT_HELPER, "omt2_mark.m": MARK_HELPER}
    lines = [f"omt2_mark(0, '', '');  % truncate {RESULT_FILE}"]
    shared: List[str] = []
    n, aside, skipped = 0, [], 0
    for b in octave_blocks(text):
        if b.kind == "function":
            body, d = _translate("function " + b.code)
            if body is not None:
                name = re.search(r"function\s+(?:\[[^\]]*\]\s*=\s*|\w+\s*=\s*)?([A-Za-z_]\w*)", body)
                if name:
                    helpers[name.group(1) + ".m"] = _ASSERT_CALL.sub("omt2_assert(", body) + "\nend\n"
            continue
        if b.kind in ("endfunction",):
            continue
        if b.kind == "shared":
            head, _, rest = b.code.partition("\n")
            shared = [v for v in re.findall(r"[A-Za-z_]\w*", head)]
            init, d = _translate(rest) if rest.strip() else ("", "")
            lines.append("clearvars;")
            lines += [f"{v} = [];" for v in shared]
            if init:
                lines += ["try", _ASSERT_CALL.sub("omt2_assert(", init), "catch omt2_e", "end"]
            continue
        if b.kind in SKIPPED_KINDS or b.kind not in SELF_CHECK_KINDS:
            skipped += 1
            continue
        code = b.code
        if b.kind == "assert":
            args = _strip_bug_tag(b.code).strip()
            if not args.startswith("("):
                aside.append("octave-assert-form")
                continue
            code = "assert" + args + ";"
        body, d = _translate(code)
        if body is None:
            aside.append(d)
            continue
        n += 1
        keep = ", ".join(f"'{v}'" for v in shared)
        lines.append(f"clearvars('-except', {keep});" if shared else "clearvars;")
        lines += ["try", _ASSERT_CALL.sub("omt2_assert(", body), f"omt2_mark({n}, '', '');",
                  "catch omt2_e", f"omt2_mark({n}, omt2_e.identifier, omt2_e.message);", "end"]
    return OctavePlan("\n".join(lines) + "\n", helpers, n, aside, skipped)


def octave_verdict(collected: str, applicable: int) -> Tuple[int, int, str, str]:
    """``(passed, finished, first_error_id, first_message)`` from the result file."""
    passed, done, eid, msg = 0, set(), "", ""
    for ln in (collected or "").splitlines():
        m = re.match(r"([PF]) (\d+)(?: ([^\t]*)\t(.*))?$", ln)
        if not m or int(m.group(2)) < 1 or int(m.group(2)) > applicable or int(m.group(2)) in done:
            continue
        done.add(int(m.group(2)))
        if m.group(1) == "P":
            passed += 1
        elif not msg:
            eid, msg = m.group(3) or "", m.group(4) or ""
    return passed, len(done), eid, msg


MARK_HELPER = """function omt2_mark(i, id, msg)
%OMT2_MARK  Append one block verdict to omt2.res (M12 T2 oracle; i == 0 truncates the file).
if i == 0
    fid = fopen('omt2.res', 'w');
elseif isempty(msg) && isempty(id)
    fid = fopen('omt2.res', 'a');
    fprintf(fid, 'P %d\\n', i);
else
    fid = fopen('omt2.res', 'a');
    msg = strrep(strrep(msg, sprintf('\\n'), ' '), sprintf('\\t'), ' ');
    if isempty(msg)
        msg = 'error';
    end
    fprintf(fid, 'F %d %s\\t%s\\n', i, id, msg);
end
fclose(fid);
end
"""

# Clean-room helper for Octave's documented assert interface (written for OpenMATLAB, MIT):
#   assert (cond), assert (cond, errmsg, ...)      -> error unless all(cond(:)) is true
#   assert (observed, expected)                    -> class, size and values must agree
#   assert (observed, expected, tol)               -> tol > 0 absolute, tol < 0 relative
ASSERT_HELPER = """function omt2_assert(cond, varargin)
%OMT2_ASSERT  Octave-style assert for the M12 T2 oracle (clean-room, MIT).
if nargin == 1 || (nargin > 1 && islogical(cond) && ischar(varargin{1}))
    if isempty(cond) || ~all(cond(:))
        if nargin > 1
            error('omt2:assert', varargin{:});
        end
        error('omt2:assert', 'assert (cond) failed');
    end
    return
end
expected = varargin{1};
tol = 0;
if nargin > 2
    tol = varargin{2};
end
err = omt2_cmp(cond, expected, tol);
if ~isempty(err)
    error('omt2:assert', 'ASSERT errors: %s', err);
end
end

function err = omt2_cmp(obs, ex, tol)
err = '';
if ischar(ex)
    if ~ischar(obs) || ~isequal(size(obs), size(ex)) || ~all(obs(:) == ex(:))
        err = 'strings differ';
    end
elseif iscell(ex)
    if ~iscell(obs) || ~isequal(size(obs), size(ex))
        err = 'cell size or class differs';
        return
    end
    for k = 1:numel(ex)
        err = omt2_cmp(obs{k}, ex{k}, tol);
        if ~isempty(err)
            err = sprintf('cell %d: %s', k, err);
            return
        end
    end
elseif isstruct(ex)
    if ~isstruct(obs) || ~isequal(size(obs), size(ex))
        err = 'struct size or class differs';
        return
    end
    fo = sort(fieldnames(obs));
    fe = sort(fieldnames(ex));
    if ~isequal(fo, fe)
        err = 'struct fields differ';
        return
    end
    for k = 1:numel(ex)
        for f = 1:numel(fe)
            err = omt2_cmp(obs(k).(fe{f}), ex(k).(fe{f}), tol);
            if ~isempty(err)
                err = sprintf('field %s: %s', fe{f}, err);
                return
            end
        end
    end
elseif isnumeric(ex) || islogical(ex)
    if ~(isnumeric(obs) || islogical(obs))
        err = sprintf('class %s != %s', class(obs), class(ex));
        return
    end
    if ~isequal(size(obs), size(ex))
        err = sprintf('dimensions %s != %s', mat2str(size(obs)), mat2str(size(ex)));
        return
    end
    if ~strcmp(class(obs), class(ex)) && all(tol(:) == 0)
        err = sprintf('class %s != %s', class(obs), class(ex));
        return
    end
    if isempty(ex)
        return
    end
    o = double(obs(:));
    e = double(ex(:));
    if any(isnan(o) ~= isnan(e))
        err = 'NaN positions differ';
        return
    end
    k = ~isnan(e);
    o = o(k);
    e = e(k);
    inf_e = isinf(real(e)) | isinf(imag(e));
    if any(inf_e ~= (isinf(real(o)) | isinf(imag(o)))) || any(o(inf_e) ~= e(inf_e))
        err = 'Inf values differ';
        return
    end
    o = o(~inf_e);
    e = e(~inf_e);
    t = tol(:);
    if numel(t) > 1
        t = t(k);
        t = t(~inf_e);
    end
    d = abs(o - e);
    if all(t == 0)
        bad = d ~= 0;
    else
        lim = abs(t) .* ones(size(d));
        rel = t < 0;
        if any(rel)
            sc = abs(e) .* ones(size(d));
            lim(rel | false(size(d))) = lim(rel | false(size(d))) .* sc(rel | false(size(d)));
        end
        bad = d > lim;
    end
    if any(bad)
        err = sprintf('%d of %d values differ (max |diff| %g)', nnz(bad), numel(bad), max(d(bad)));
    end
else
    if ~isequal(obs, ex)
        err = sprintf('%s values differ', class(ex));
    end
end
end
"""

# ---------------------------------------------------------------- T3 goldens

_NUM = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$")


def golden_source(notes: List[str], code: str) -> str:
    """``"matlab"`` when the entry's transcript came from MATLAB ``>>`` prompts, else ``""``."""
    if "deprompted" not in notes:
        return ""
    prompts = re.findall(r"^\s*(>>|octave:\d+>|>(?=\s))", code, re.M)
    return "matlab" if prompts and all(p == ">>" for p in prompts) else ""


def _tokens(text: str) -> List[str]:
    return [t for t in re.split(r"\s+", text) if t]


def golden_match(stdout: str, golden: str) -> Tuple[bool, str]:
    """Token comparison with whitespace normalised; numbers within :data:`GOLDEN_RTOL` (relative)."""
    a, b = _tokens(stdout or ""), _tokens(golden or "")
    for i, (x, y) in enumerate(zip(a, b)):
        if x == y:
            continue
        if _NUM.match(x) and _NUM.match(y):
            fx, fy = float(x), float(y)
            if abs(fx - fy) <= GOLDEN_RTOL * max(abs(fx), abs(fy)):
                continue
        return False, f"token {i + 1} differs"
    if len(a) != len(b):
        return False, f"{len(a)} output tokens, golden has {len(b)}"
    return True, ""

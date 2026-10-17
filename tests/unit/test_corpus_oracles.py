"""C-E5 #765: T2 (Octave %! self-check) and T3 (MATLAB transcript golden) oracles (M12 C07/C08)."""

import subprocess
import sys

import pytest

from openmatlab.qa.corpus import oracles as O
from openmatlab.qa.corpus import report

pytestmark = pytest.mark.unit

# Synthetic Octave-style test file (written for this test; not Octave code).
SAMPLE = """function y = twice (x)
  y = 2 * x;
endfunction

%!assert (twice (2), 4)
%!assert <*12345> (twice ([1 2]), [2 4])
%!shared a
%! a = 3;
%!test
%! b = twice (a);
%! assert (b, 6);
%!test
%! x = 1; x += 1;
%!error <Invalid call> twice ()
%!testif HAVE_FOO
%! assert (1)
%!assert (strtrim ("  ab "), "ab")
%!assert (columns (ones (2, 3)), 3)
"""


def test_blocks_split_and_kinds():
    kinds = [b.kind for b in O.octave_blocks(SAMPLE)]
    assert kinds == ["assert", "assert", "shared", "test", "test", "error", "testif", "assert", "assert"]


def test_plan_counts_and_set_aside():
    p = O.octave_script(SAMPLE)
    assert p.applicable == 4  # two asserts, the shared test, the dq-string assert
    assert sorted(a.split(":")[0] for a in p.set_aside) == ["octave-assign-op", "octave-only"]
    assert p.skipped == 2  # %!error, %!testif
    assert "omt2_assert(twice ([1 2]), [2 4]);" in p.script
    assert "omt2_assert(strtrim ('  ab '), 'ab');" in p.script
    assert "clearvars('-except', 'a');" in p.script
    assert set(p.helpers) == {"omt2_assert.m", "omt2_mark.m"}


@pytest.mark.parametrize("code,why", [
    ("x = 1; # comment", "octave-comment"),
    ("a = b = 3;", "octave-chained-assign"),
    ("y = magic (3)(2);", "octave-index-chain"),
    ("y = [1 2](1);", "octave-index-chain"),
    ("y = 2 ** 3;", "octave-power"),
    ("y = __foo__ (1);", "octave-internal"),
    ("if (x != 1) y = 1; end", "octave-not"),
    ("y = rows (x);", "octave-only:rows"),
])
def test_block_dialect(code, why):
    assert O.block_dialect(code) == why


@pytest.mark.parametrize("code", ["y = x(1);", "y = x';", "c = {1, 2}; z = c{2};", "[a, b] = deal (1, 2);",
                                  "assert (isequal ([1 (2)], [1 2]))"])
def test_block_dialect_matlab_is_clean(code):
    assert O.block_dialect(code) == ""


def test_dq_escape_is_set_aside():
    p = O.octave_script('%!assert (sprintf ("a\\n"), "a\\n")\n')
    assert p.applicable == 0 and p.set_aside == ["octave-dquote-escape"]


def test_verdict_parsing_ignores_forged_or_duplicate_lines():
    txt = "P 1\nF 2 my:id\tbad thing\nP 2\nP 9\ngarbage\n"
    assert O.octave_verdict(txt, 3) == (1, 2, "my:id", "bad thing")


def _run_m(tmp_path, code):
    (tmp_path / "omt2_assert.m").write_text(O.ASSERT_HELPER)
    (tmp_path / "omt2_mark.m").write_text(O.MARK_HELPER)
    p = subprocess.run([sys.executable, "-m", "openmatlab", "-e", f"addpath(pwd); {code}"], capture_output=True,
                       text=True, cwd=tmp_path)
    return p.returncode, p.stdout + p.stderr


@pytest.mark.parametrize("call", [
    "omt2_assert(true)", "omt2_assert([1 2 3], [1 2 3])", "omt2_assert(pi, 3.14159, 1e-5)",
    "omt2_assert(100, 101, -0.02)", "omt2_assert({1, 'a'}, {1, 'a'})", "omt2_assert('ab', 'ab')",
    "omt2_assert([1 NaN Inf], [1 NaN Inf])", "omt2_assert(struct('a', 1), struct('a', 1))",
    "omt2_assert(int8(3), int8(3))", "omt2_assert(true, 'message %d', 3)",
])
def test_assert_helper_passes(tmp_path, call):
    rc, out = _run_m(tmp_path, call)
    assert rc == 0 and "error" not in out.lower(), out


@pytest.mark.parametrize("call,frag", [
    ("omt2_assert(false)", "failed"), ("omt2_assert([1 2], [1 2 3])", "dimensions"),
    ("omt2_assert(pi, 3.14, 1e-5)", "differ"), ("omt2_assert(int8(3), 3)", "class"),
    ("omt2_assert([1 NaN], [1 2])", "NaN"), ("omt2_assert('ab', 'ac')", "strings"),
    ("omt2_assert(-Inf, Inf)", "Inf"), ("omt2_assert(struct('a', 1), struct('b', 1))", "fields"),
    ("omt2_assert(false, 'custom %d', 7)", "custom 7"), ("omt2_assert([], 1)", "dimensions"),
])
def test_assert_helper_fails(tmp_path, call, frag):
    rc, out = _run_m(tmp_path, call)
    assert rc != 0 and frag in out and "Traceback" not in out, out


def test_mark_helper_writes_verdicts(tmp_path):
    rc, out = _run_m(tmp_path, "omt2_mark(0,'',''); omt2_mark(1,'',''); omt2_mark(2,'a:b',sprintf('x\\ny'));")
    assert rc == 0, out
    assert (tmp_path / O.RESULT_FILE).read_text() == "P 1\nF 2 a:b\tx y\n"


def test_golden_source_only_matlab_prompts():
    assert O.golden_source(["deprompted"], ">> x = 1\nx =\n     1\n") == "matlab"
    assert O.golden_source(["deprompted"], "octave:1> x = 1\nx = 1\n") == ""
    assert O.golden_source(["deprompted"], ">> a\n> b\n") == ""
    assert O.golden_source(["echo-stripped"], ">> x = 1\n") == ""


@pytest.mark.parametrize("out,golden,ok", [
    ("x =\n\n     3\n\n", "x =\n     3", True),
    ("ans = 3.1416", "ans =\n\n    3.1416\n", True),
    ("x =\n     3\n", "x =\n     4\n", False),
    ("x =\n     3\n", "x =\n     3\n y =\n", False),
    ("1.00000000000001", "1", True),
    ("1.0001", "1", False),
])
def test_golden_match(out, golden, ok):
    assert O.golden_match(out, golden)[0] is ok


def test_t2_t3_rates_count_only_attempted_entries():
    recs = [{"id": "a", "t2": "pass", "category": "pass"}, {"id": "b", "t2": "error", "category": "semantics-diff"},
            {"id": "c", "t2": "n/a", "category": "corpus-noise"}, {"id": "d", "category": "pass"},
            {"id": "e", "t3": "pass", "category": "pass"}, {"id": "f", "t3": "timeout", "category": "timeout"}]
    assert report.rate_of(recs, "T2") == (1, 2)
    assert report.rate_of(recs, "T3") == (1, 2)

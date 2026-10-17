"""T2 self-check harness (M12 C07, C-E5 #765): block parsing, Octave normalisation, redaction, t2_assert."""

from __future__ import annotations

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.qa.corpus import selfcheck as S
from openmatlab.qa.corpus.results import KEEP

pytestmark = [pytest.mark.unit]

SRC = """function y = f(x)
  y = x;
end
%!shared a, b
%! a = 1; b = 2;
%!assert (f (a), 1)
%!test
%! z = f (b);
%! assert (z, 2);
%!error f ()
%!function r = helper (q)
%!  r = q + 1;
%!endfunction
%!xtest
%! assert (false)
"""


def test_parse_blocks_counts_assert_and_test_only():
    p = S.parse_blocks(SRC)
    assert [b.kind for b in p.blocks] == ["assert", "test"]
    assert [b.index for b in p.blocks] == [1, 2]
    assert p.skipped == 2  # %!error, %!xtest
    assert p.blocks[0].shared[0] == "a = [];" and "a = 1; b = 2;" in p.blocks[0].shared[-1]
    assert p.blocks[0].text.startswith("assert (f (a), 1)")
    assert len(p.functions) == 1 and "helper" in p.functions[0]


def test_octave_to_matlab_normalises_dialect():
    code = S.octave_to_matlab('x = 1; # note\nif x != 2 && !false, y = "a\\tb"; endif\nx += 3;\nassert (x, 4)')
    assert "#" not in code and "!" not in code and "endif" not in code
    assert "~=" in code and "~false" in code
    assert "char(9)" in code
    assert "x = x + (3);" in code
    assert "t2_assert (x, 4)" in code


def test_transpose_is_not_a_string():
    assert S.octave_to_matlab("y = a';") == "y = a';"
    assert S.octave_to_matlab("s = 'it''s';") == "s = 'it''s';"


def test_redact_drops_values_keeps_names():
    m = S.redact("Undefined function 'foo' at 3.5 with 'a b c'")
    assert "'foo'" in m and "3.5" not in m and "a b c" not in m


def test_excluded_categories():
    assert S.excluded_category("postpad") == "toolbox:octave-only"
    assert S.excluded_category("zscore") == "toolbox:statistics"
    assert S.excluded_category("mkdir") == "io-env"
    assert S.excluded_category("fliplr") == ""


def test_results_keep_t2_fields():
    assert {"t2", "t2_blocks", "sha256"} <= set(KEEP)


@pytest.mark.parametrize("code,ok", [
    ("t2_assert(true)", True),
    ("t2_assert([1 0])", False),
    ("t2_assert(false, 'msg %d', 3)", False),
    ("t2_assert([1 2], [1 2])", True),
    ("t2_assert([1 2], [1 3])", False),
    ("t2_assert([1 2], [1 2]')", False),
    ("t2_assert(pi, 3.1416, 1e-4)", True),
    ("t2_assert(100, 101, -0.02)", True),
    ("t2_assert(100, 103, -0.02)", False),
    ("t2_assert('abc', 'abc')", True),
    ("t2_assert('abc', 'abd')", False),
    ("t2_assert({1, 'a'}, {1, 'a'})", True),
    ("t2_assert(struct('a', 1), struct('a', 1))", True),
    ("t2_assert(single(1), 1)", False),
    ("t2_assert([NaN 1], [NaN 1])", True),
    ("t2_assert([Inf 1], [-Inf 1])", False),
    ("t2_assert(zeros(0, 3), zeros(0, 3))", True),
])
def test_t2_assert(code, ok):
    r = ReplSession()
    r.run_line(f"addpath('{S.T2LIB.as_posix()}');")
    r.run_line(f"try, {code}; ok__ = 1; catch, ok__ = 0; end")
    assert bool(r.session.workspace.get("ok__").backend_buffer().item()) is ok


def test_paren_continuation_and_bug_tags():
    assert S.octave_to_matlab("assert (f (1,\n 2), [1 2\n 3 4])") == "t2_assert (f (1, ...\n 2), [1 2\n 3 4])"
    assert S.parse_blocks("%!test <*123>\n%! x = 1;").blocks[0].text.strip() == "x = 1;"

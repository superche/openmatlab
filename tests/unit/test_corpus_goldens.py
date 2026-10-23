"""C-E5 #765: T3 MATLAB-transcript / Octave-runtime golden oracle (M12 C08)."""

from __future__ import annotations

import pytest

from openmatlab.qa.corpus import goldens as G
from openmatlab.qa.corpus import report


def test_golden_source_only_matlab_prompts():
    assert G.golden_source(["deprompted"], ">> x = 1\nx =\n     1\n") == "matlab"
    assert G.golden_source(["deprompted"], "octave:1> x = 1\nx = 1\n") == ""
    assert G.golden_source(["deprompted"], ">> a\n> b\n") == ""
    assert G.golden_source(["echo-stripped"], ">> x = 1\n") == ""


@pytest.mark.parametrize("out,golden,ok", [
    ("x =\n\n     3\n\n", "x =\n     3", True),
    ("ans = 3.1416", "ans =\n\n    3.1416\n", True),
    ("x =\n     3\n", "x =\n     4\n", False),
    ("x =\n     3\n", "x =\n     3\n y =\n", False),
    ("1.00000000000001", "1", True),
    ("1.0001", "1", False),
])
def test_golden_match(out, golden, ok):
    assert G.golden_match(out, golden)[0] is ok


def test_t3_rates_count_only_attempted_entries():
    recs = [
        {"id": "a", "t2": "pass", "category": "pass"},
        {"id": "b", "t2": "error", "category": "semantics-diff"},
        {"id": "c", "t2": "n/a", "category": "corpus-noise"},
        {"id": "d", "category": "pass"},
        {"id": "e", "t3": "pass", "category": "pass"},
        {"id": "f", "t3": "timeout", "category": "timeout"},
    ]
    assert report.rate_of(recs, "T2") == (1, 2)
    assert report.rate_of(recs, "T3") == (1, 2)


@pytest.mark.parametrize("out,golden,ok", [
    ("ans =\n    0.8415\n", "ans =\n   0.841470984807897\n", True),  # format long session
    ("a =\n1 + 1i\n", "a =\n  1.000000000000000 + 1.000000000000000i\n", True),
    ("ans =\n-4 + 10i\n", "ans =\n -4.000000000000000 +10.000000000000000i\n", True),
    ("ans =\n3\n", "ans =\n   3.141512000000000\n", False),  # integer display: no rounding forgiven
    ("ans =\n0.8416\n", "ans =\n   0.841470984807897\n", False),
    ("ans =\n  Columns 1 through 2\n 1 2\n  Column 3\n 3\n", "ans =\n 1 2 3\n", True),
    ("ans =\n1.0e+03\n", "ans =\n1.0001e+03\n", False),
])
def test_golden_match_precision_and_wrap(out, golden, ok):
    assert G.golden_match(out, golden)[0] is ok


@pytest.mark.parametrize("code,hit", [
    ("x = rand(3)", "rand"),
    ("disp(date)", "date"),
    ("s = input('?')", "input"),
    ("x = 'rand'; disp(x)", ""),
    ("% tic\nx = 1", ""),
    ("y = operand(2)", ""),
])
def test_nondeterministic_scripts_have_no_golden(code, hit):
    assert G.nondeterministic(code) == hit


def test_committed_t3_records_are_documented_goldens():
    """M12 C08: every T3 attempt is golden:matlab or golden:octave with a MATLAB doc URL."""
    from openmatlab.qa.corpus import results

    doc = results.load()
    t3 = [r for r in doc.get("records", []) if r.get("t3") in ("pass", "error", "timeout", "crash")]
    if not t3:
        return  # harness landed before the first full T3 run
    for r in t3:
        tag = str(r.get("oracle", ""))
        assert tag.startswith("golden:matlab") or tag.startswith("golden:octave"), r.get("id")
        if tag.startswith("golden:octave"):
            assert "https://www.mathworks.com/help/" in tag or "doc:" in tag, r.get("id")


def test_committed_records_carry_no_corpus_text():
    """Results keep ids / tiers / categories / short messages only — never golden stdout."""
    from openmatlab.qa.corpus import results

    doc = results.load()
    blob = " ".join(
        f"{r.get('oracle','')} {r.get('message','')} {r.get('key','')}" for r in doc.get("records", [])
    )
    # no multi-line MATLAB banners that look like pasted transcripts
    assert "Columns 1 through" not in blob

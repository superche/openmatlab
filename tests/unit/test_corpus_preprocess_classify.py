"""M12 C-E3 (Epic #763): deterministic preprocessing and the root-cause classifier."""

from __future__ import annotations

import pytest

from openmatlab.qa.corpus import classify as C
from openmatlab.qa.corpus import preprocess as P

pytestmark = pytest.mark.unit


def test_deprompt_keeps_code_and_transcript():
    n = P.normalize(">> a = 2+3\n\na =\n\n     5\n\n>> b = a*2\n")
    assert n.code == "a = 2+3\nb = a*2\n"
    assert n.expected_stdout == "a =\n\n     5"


def test_deprompt_keeps_open_block_and_continuation():
    n = P.normalize(">> for k = 1:2\ndisp(k)\nend\n     1\n     2\n>> x = [1, ...\n2];\n")
    assert n.code == "for k = 1:2\ndisp(k)\nend\nx = [1, ...\n2];\n"
    assert "1\n     2" in n.expected_stdout


def test_octave_prompt_and_no_prompt_unchanged():
    assert P.normalize("octave:1> y = 3\ny = 3\n").code == "y = 3\n"
    src = "x = 1;\ndisp(x)\n"
    n = P.normalize(src)
    assert (n.code, n.expected_stdout, n.notes) == (src, None, [])


def test_deterministic():
    src = ">> a = 1\na = 1\n>> input('q? ')\n"
    assert P.normalize(src) == P.normalize(src)


@pytest.mark.parametrize("src,kind", [
    ("function y = f(x)\ny = x;\nend\n", "function"),
    ("function y = f(x)\ny = x;\n", "function"),
    ("% helper\nfunction f\n  if 1, disp(1), end\nend\nfunction g\nend\n", "function"),
    ("x = 1;\nfunction y = f(x)\ny = x;\nend\n", "script"),
    ("function f\ndisp(1)\nend\nf()\n", "script"),
])
def test_function_file_detection(src, kind):
    assert P.normalize(src).kind == kind


def test_input_fixture():
    n = P.normalize("n = input('n? ');\ns = input('name: ', 's');\n")
    assert n.stdin_fixture[:2] == ["5", "hello"] and len(n.stdin_fixture) == 2 + P.SPARE_ANSWERS
    assert P.normalize("disp(1)\n").stdin_fixture is None


def test_input_fixture_reaches_script(tmp_path):
    from openmatlab.qa.corpus.runner import run_one

    f = tmp_path / "ask.m"
    f.write_text("n = input('n? ');\nfprintf('%d\\n', 2*n);\n")
    r = run_one(f, timeout=30, input_lines=P.normalize(f.read_text()).stdin_fixture)
    assert r.status == "pass" and r.stdout.strip().endswith("10")


def test_noise_rate():
    rows = [{"source": "rosetta", "kind": "script", "category": c} for c in ("corpus-noise", "pass", "pass", "pass")]
    assert P.noise_rate(rows + [{"source": "octave", "kind": "script", "category": "corpus-noise"}]) == 0.25


def _err(msg, kind="eval", **kw):
    return dict(status="error", kind=kind, message=msg, **kw)


@pytest.mark.parametrize("result,code,want", [
    ({"status": "crash", "kind": "internal", "message": "AssertionError: "}, "", "internal-crash"),
    (_err("x", stderr="Traceback (most recent call last):\n"), "", "internal-crash"),
    ({"status": "timeout", "kind": "timeout", "message": ""}, "while 1, end", "timeout"),
    ({"status": "timeout", "kind": "timeout", "message": ""}, "x = input('a');", "io-env"),
    (_err("Unexpected token REL_GT", kind="parse"), "# comment\nx=1", "corpus-noise"),
    (_err("Unexpected token NEWLINE", kind="parse"), "x = [1 2", "parse-error"),
    (_err("Undefined function or variable: printf"), "printf('%d', 1)", "corpus-noise"),
    (_err("Undefined function or variable: vpa"), "vpa(pi, 50)", "toolbox:symbolic"),
    (_err("Undefined function or variable: urlread"), "urlread('http://x')", "io-env"),
    (_err("Undefined function or variable: polarplot"), "polarplot(1:3)", "graphics"),
    (_err("Undefined function or variable: strmatch"), "strmatch('a', {'a'})", "missing-builtin"),
    (_err("Undefined variable: x"), "disp(x)", "corpus-noise"),
    (_err("Undefined function or variable: makeGrid"), "g = makeGrid(3);", "corpus-noise"),
    (_err("Invalid file identifier. Use fopen to generate a valid file identifier."), "fprintf(f, 'a')", "io-env"),
    (_err("Index exceeds the number of array elements (3)."), "a = 1:3; a(4)", "semantics-diff"),
])
def test_classifier_rules(result, code, want):
    cat, _key = C.classify(result, code)
    assert cat == want


def test_missing_dependency_from_sibling():
    assert C.classify(_err("Undefined function or variable: hailstone"), "hailstone(3)", siblings=["hailstone"]) == (
        "corpus-noise", "missing-dependency")


def test_pass_is_pass():
    assert C.classify({"status": "pass"}) == ("pass", "")


def test_labelled_set_scores():
    s = C.evaluate_labelled_set()
    assert s.n >= 60 and s.accuracy >= 0.90 and s.crash_recall == 1.0


def test_labelled_features_match_cache():
    """The stored features are what the pipeline derives today (skipped without the corpus cache)."""
    import json

    from openmatlab.qa.corpus import manifest as M
    from openmatlab.qa.corpus.pipeline import jobs_for

    m = M.load()
    labels = json.loads((M.corpus_dir() / "labels.json").read_text())["labels"]
    jobs = {j.e.id: j for j in jobs_for(m)}
    checked = 0
    for x in labels:
        j = jobs.get(x["id"])
        f = M.cache_dir() / j.e.file if j else None
        if not f or not f.is_file() or j.e.call:
            continue
        code = P.prepare(f.read_text(encoding="utf-8", errors="replace"), j.siblings).code
        got = C.features(code, j.siblings)
        assert {k: got[k] for k in ("dialect", "defined", "siblings")} == {k: x["features"][k] for k in ("dialect", "defined", "siblings")}, x["id"]
        checked += 1
    if not checked:
        pytest.skip("corpus cache not present")

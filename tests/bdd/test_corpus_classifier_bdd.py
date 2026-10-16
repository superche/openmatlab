from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.qa.corpus import classify as C
from openmatlab.qa.corpus import preprocess as P

pytestmark = [pytest.mark.bdd, pytest.mark.unit]
scenarios("../../features/corpus_classifier.feature")


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse('the snippet "{line}" followed by its echoed output'))
def snippet(ctx, line):
    ctx["src"] = f"{line}\n\na =\n\n     5\n\n"


@when("I normalize it")
def norm(ctx):
    ctx["n"] = P.normalize(ctx["src"])


@then(parsers.parse('the code is "{code}" and the echo is kept as expected output'))
def code_is(ctx, code):
    assert ctx["n"].code.strip() == code and "5" in ctx["n"].expected_stdout


@when(parsers.parse('I classify an eval error "{msg}"'))
def cls(ctx, msg):
    ctx["cat"] = C.classify({"status": "error", "kind": "eval", "message": msg}, "printf('%d', 1)")[0]


@then(parsers.parse('the category is "{cat}"'))
def cat_is(ctx, cat):
    assert ctx["cat"] == cat


@when("I score the classifier on the labelled set")
def score(ctx):
    ctx["s"] = C.evaluate_labelled_set()


@then(parsers.parse("at least {n:d} failures are labelled"))
def count(ctx, n):
    assert ctx["s"].n >= n


@then(parsers.parse("the accuracy is at least {pct:d} percent with full internal-crash recall"))
def acc(ctx, pct):
    assert ctx["s"].accuracy >= pct / 100 and ctx["s"].crash_recall == 1.0

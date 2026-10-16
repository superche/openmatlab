from __future__ import annotations

import json

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.qa.corpus import report as R
from openmatlab.qa.corpus import triage as T

pytestmark = [pytest.mark.bdd, pytest.mark.unit]
scenarios("../../features/corpus_report.feature")


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse('a baseline where entry "{i}" passes'))
def baseline(ctx, i):
    ctx["base"] = [{"id": i, "status": "pass"}]


@when(parsers.parse('a new run reports "{i}" as an error'))
def new_run(ctx, i):
    ctx["new"] = [{"id": i, "status": "error", "category": "semantics-diff", "key": "k"}]


@then(parsers.parse('the gate lists "{i}" as a regression'))
def gate(ctx, i):
    assert R.regressions(ctx["new"], ctx["base"]) == [i]


@given(parsers.parse('two failures with category "{cat}" and key "{key}"'))
def two(ctx, cat, key):
    ctx["recs"] = [{"id": n, "status": "error", "category": cat, "key": key} for n in ("x", "y")]


@when("I group the failures")
def grp(ctx):
    ctx["groups"] = T.group(ctx["recs"])


@then(parsers.parse("there is one group of {n:d} entries"))
def one(ctx, n):
    assert len(ctx["groups"]) == 1 and ctx["groups"][0].count == n


@then("filing twice opens only one issue")
def twice(ctx):
    issues = []

    def gh(args):
        if args[:2] == ["issue", "list"]:
            return json.dumps(issues)
        issues.append({"number": len(issues) + 1, "body": args[args.index("--body") + 1]})
        return f"https://x/issues/{len(issues)}"

    T.file_issues(ctx["groups"], gh=gh)
    T.file_issues(ctx["groups"], gh=gh)
    assert len(issues) == 1

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.qa.corpus.runner import run_many

pytestmark = [pytest.mark.bdd, pytest.mark.unit]
scenarios("../../features/corpus_runner.feature")


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse('scripts "{a}" containing "{sa}" and "{b}" containing "{sb}"'))
def scripts(ctx, tmp_path, a, sa, b, sb):
    ctx["paths"] = []
    for name, src in ((a, sa), (b, sb)):
        (tmp_path / name).write_text(src + "\n")
        ctx["paths"].append(tmp_path / name)


@when(parsers.parse("I run them with a {n:d} second timeout"))
def run(ctx, n):
    ctx["res"] = {r.name: r for r in run_many(ctx["paths"], timeout=n)}


@then(parsers.parse('"{name}" has status "{status}"'))
def status(ctx, name, status):
    assert ctx["res"][name].status == status


@then(parsers.parse('"{name}" has error id "{ident}"'))
def ident(ctx, name, ident):
    assert ctx["res"][name].error_id == ident

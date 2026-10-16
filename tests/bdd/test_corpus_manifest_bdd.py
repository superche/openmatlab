from __future__ import annotations

import copy

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.qa.corpus import manifest as M

pytestmark = [pytest.mark.bdd, pytest.mark.unit]
scenarios("../../features/corpus_manifest.feature")


@pytest.fixture
def ctx():
    return {}


@when("I run the corpus licence check")
def check(ctx):
    ctx["m"] = M.load()
    ctx["probs"] = M.check_allowlist(ctx["m"]) + M.scan_repo_for_copyleft_bodies(ctx["m"])


@then("it reports no problems")
def none(ctx):
    assert ctx["probs"] == []


@then(parsers.parse("the manifest lists at least {n:d} runnable entries from {k:d} sources"))
def size(ctx, n, k):
    m = ctx["m"]
    assert sum(e.runnable for e in m.entries) >= n and len({e.source for e in m.entries}) >= k


@given(parsers.parse('the manifest with source "{src}" set to policy "{pol}"'))
def mod(ctx, src, pol):
    ctx["m"] = copy.deepcopy(M.load())
    ctx["m"].sources[src]["policy"] = pol


@when("I check the allow-list")
def chk(ctx):
    ctx["probs"] = M.check_allowlist(ctx["m"])


@then(parsers.parse('a problem mentions "{word}"'))
def mentions(ctx, word):
    assert any(word in p for p in ctx["probs"])

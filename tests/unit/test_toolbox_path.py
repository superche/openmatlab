"""ToolboxPath + FunctionResolver path slice (Issue #6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.libs.path import ToolboxPath
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.session import Session

pytestmark = pytest.mark.unit


def test_find_mfile(tmp_path: Path):
    f = tmp_path / "mysum.m"
    f.write_text("function y = mysum(a, b)\ny = a + b;\n")
    path = ToolboxPath()
    path.addpath(tmp_path)
    assert path.find_mfile("mysum") == f.resolve()
    assert path.find_mfile("missing") is None


def test_resolver_which_and_resolve_stub(tmp_path: Path):
    (tmp_path / "foo.m").write_text("% placeholder\n")
    path = ToolboxPath()
    path.addpath(tmp_path)
    res = FunctionResolver(path=path)
    assert res.which("foo").endswith("foo.m")
    with pytest.raises(NotImplementedError, match="foo.m"):
        res.resolve("foo")
    with pytest.raises(LookupError):
        res.resolve("nope")


def test_session_path_wired(tmp_path: Path):
    s = Session.create_default()
    s.path.addpath(tmp_path)
    (tmp_path / "bar.m").write_text("% bar\n")
    assert s.functions.which("bar").endswith("bar.m")

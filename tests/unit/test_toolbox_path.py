"""ToolboxPath + FunctionResolver path / .m load (Issue #6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.libs.path import ToolboxPath
from openmatlab.numerics.numpy_backend import NumPyArrayBackend
from openmatlab.runtime.functions import FunctionResolver, parse_mfile
from openmatlab.runtime.session import Session

pytestmark = pytest.mark.unit


def test_find_mfile(tmp_path: Path):
    f = tmp_path / "mysum.m"
    f.write_text("function y = mysum(a, b)\ny = a + b;\nend\n")
    path = ToolboxPath()
    path.addpath(tmp_path)
    assert path.find_mfile("mysum") == f.resolve()
    assert path.find_mfile("missing") is None


def test_resolver_which(tmp_path: Path):
    (tmp_path / "foo.m").write_text(
        "function y = foo(x)\ny = x;\nend\n"
    )
    path = ToolboxPath()
    path.addpath(tmp_path)
    res = FunctionResolver(path=path)
    assert res.which("foo").endswith("foo.m")
    assert res.which("nope") == ""


def test_session_path_wired(tmp_path: Path):
    s = Session.create_default()
    s.path.addpath(tmp_path)
    (tmp_path / "bar.m").write_text("function y = bar(x)\ny = x;\nend\n")
    assert s.functions.which("bar").endswith("bar.m")

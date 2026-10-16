"""#874: a signature-only declaration in a concrete methods block implements an inherited abstract method."""
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = pytest.mark.unit


def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_signature_only_method_makes_class_concrete(tmp_path):
    _write(tmp_path, "@base874/base874.m",
           "classdef base874\n methods (Abstract = true, Static = true)\n  m = mk(d);\n end\nend\n")
    _write(tmp_path, "@kid874/kid874.m",
           "classdef kid874 < base874\n methods (Static = true)\n  m = mk(d)\n end\nend\n")
    s = Session.create_default()
    ReplSession(s).run_line(f"addpath('{tmp_path}'); k = kid874(); c = class(k);")
    assert s.workspace.get("c").text == "kid874"


def test_abstract_without_declaration_still_rejected(tmp_path):
    _write(tmp_path, "@base875/base875.m",
           "classdef base875\n methods (Abstract = true)\n  y = f(o);\n end\nend\n")
    _write(tmp_path, "@kid875/kid875.m", "classdef kid875 < base875\nend\n")
    s = Session.create_default()
    ReplSession(s).run_line(
        f"addpath('{tmp_path}'); try, kid875(); id = 'none'; catch e, id = e.identifier; end")
    assert s.workspace.get("id").text == "MATLAB:class:abstract"

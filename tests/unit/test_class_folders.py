"""#766: @class folders - classdef in @X/X.m, method bodies in separate files, folder-private helpers."""
import pytest

from openmatlab.host.repl import ReplSession

pytestmark = pytest.mark.unit

CLS = """classdef Pt
  properties
    x = 0
  end
  methods
    function o = Pt(v)
      if nargin, o.x = v; end
    end
    r = norm2(o)
  end
  methods (Static)
    o = origin()
  end
end
"""


@pytest.fixture
def tree(tmp_path):
    d = tmp_path / "@Pt"
    (d / "private").mkdir(parents=True)
    (d / "Pt.m").write_text(CLS)
    (d / "norm2.m").write_text("function r = norm2(o)\nr = helperp(o.x);\n")
    (d / "origin.m").write_text("function o = origin()\no = Pt(0);\n")
    (d / "private" / "helperp.m").write_text("function r = helperp(x)\nr = x^2;\n")
    return tmp_path


def test_class_folder_methods(tree, capsys):
    ReplSession().run_line(f"addpath('{tree}'); p = Pt(3); fprintf('%d %d %d %s\\n', p.norm2(), norm2(p), Pt.origin().x, class(p));")
    assert capsys.readouterr().out.strip() == "9 9 0 Pt"

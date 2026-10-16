"""#766: functions in a private/ folder are visible only to files in the parent folder."""
import pytest

from openmatlab.host.repl import ReplSession

pytestmark = pytest.mark.unit


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "sq.m").write_text("function r = sq(x)\nr = helper2(x) + 1;\n")
    (tmp_path / "private" / "helper2.m").write_text("function r = helper2(x)\nr = x^2;\n")
    (tmp_path / "drv.m").write_text("disp(sq(3))\n")
    (tmp_path / "pub.m").write_text("function r = pub()\nr = sq(2);\n")
    (tmp_path / "private" / "disp.m").write_text("function disp(x)\nfprintf('private disp\\n');\n")
    return tmp_path


def _out(capsys, line):
    ReplSession().run_line(line)
    return capsys.readouterr().out


def test_script_and_function_see_private(tree, capsys):
    out = _out(capsys, f"addpath('{tree}'); x = pub(); fprintf('%d\\n', x); run('{tree / 'drv.m'}');")
    assert "5" in out and "private disp" in out  # private shadows the builtin disp


def test_private_hidden_from_outside(tree, capsys):
    out = _out(capsys, f"addpath('{tree}'); try, sq(1), catch e, fprintf('%s\\n', e.message), end")
    assert "Undefined function or variable: sq" in out

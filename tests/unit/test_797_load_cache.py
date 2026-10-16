"""#797: load_mfile memoisation must re-parse an edited file."""

from openmatlab.runtime.functions import load_mfile


def test_edited_file_is_reparsed(tmp_path):
    f = tmp_path / "g.m"
    f.write_text("function y = g()\ny = 1;\nend\n", encoding="utf-8")
    a = load_mfile(f)
    assert load_mfile(f) is a
    f.write_text("function y = g()\ny = 2;\nend\n", encoding="utf-8")
    b = load_mfile(f)
    assert b is not a and b != a

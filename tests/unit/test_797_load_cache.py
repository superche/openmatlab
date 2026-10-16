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


def test_find_mfile_sees_new_files_immediately(tmp_path):
    from openmatlab.libs.path import ToolboxPath

    tp = ToolboxPath()
    tp.addpath(tmp_path)
    assert tp.find_mfile("h") is None
    (tmp_path / "h.m").write_text("function h\nend\n", encoding="utf-8")
    assert tp.find_mfile("h") == (tmp_path / "h.m").resolve()
    (tmp_path / "@k").mkdir()
    (tmp_path / "@k" / "k.m").write_text("classdef k\nend\n", encoding="utf-8")
    assert tp.find_mfile("k") == (tmp_path / "@k" / "k.m").resolve()

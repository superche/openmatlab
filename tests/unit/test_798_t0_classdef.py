"""#798: the corpus T0 (parse-only) check parses classdef files with the classdef parser."""

from openmatlab.qa.corpus.runner import run_one


def test_classdef_parses_in_t0(tmp_path):
    f = tmp_path / "Pt.m"
    f.write_text("classdef Pt\n    properties\n        x\n    end %properties\n"
                 "    methods\n        function o = Pt(v)\n            o.x = v;\n        end\n    end\nend\n",
                 encoding="utf-8")
    assert run_one(f, mode="parse").status == "pass"


def test_broken_classdef_still_fails_t0(tmp_path):
    f = tmp_path / "Bad.m"
    f.write_text("classdef Bad\n    methods\n        function o = Bad(\n    end\nend\n", encoding="utf-8")
    assert run_one(f, mode="parse").status == "error"

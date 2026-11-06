"""readtable and detectImportOptions VariableNamingRule for delimited text (#1044)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def run(tmp_path):
    s = Session.create_default()
    r = ReplSession(s)

    def go(code):
        r.run_line(f"d = '{tmp_path.as_posix()}'; " + code)
        return s

    go.dir = tmp_path
    return go


def _write(run, name, body, encoding="utf-8"):
    (run.dir / name).write_text(body, encoding=encoding)


def _num(s, name):
    return np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def _names(s, table="T"):
    return list(s.workspace.get(table).names)


def test_preserve_keeps_header_text_and_modify_matches_the_default(run):
    _write(run, "a.csv", "Last Name,2nd,a/b,Smoker (1 or 0)\nAda,1,2,3\nBea,4,5,6\n")
    _write(run, "long.csv", ("a" * 70) + ",id\n1,2\n")
    _write(run, "cafe.csv", "caf\u00e9 price,id\n9,8\n", encoding="latin-1")
    s = run("M = readtable(fullfile(d,'a.csv'));"
            "D = readtable(fullfile(d,'a.csv'), 'VariableNamingRule', 'modify');"
            "P = readtable(fullfile(d,'a.csv'), 'VariableNamingRule', 'PRESERVE');"
            "U = readtable(fullfile(d,'a.csv'), \"VariableNamingRule\", \"preserve\");"
            "L = readtable(fullfile(d,'long.csv'));"
            "K = readtable(fullfile(d,'long.csv'), 'VariableNamingRule', 'preserve');"
            "C = readtable(fullfile(d,'cafe.csv'), 'VariableNamingRule', 'preserve');"
            "E = readtable(fullfile(d,'cafe.csv'));"
            "k = double(strcmp(P.Properties.VariableNames{1}, 'Last Name'));"
            "emptyDesc = double(isempty(P.Properties.VariableDescriptions) && "
            "isempty(M.Properties.VariableDescriptions));")
    assert _names(s, "M") == _names(s, "D")
    assert _names(s, "P") == ["Last Name", "2nd", "a/b", "Smoker (1 or 0)"]
    assert _names(s, "U") == _names(s, "P")
    assert _num(s, "k") == [1]
    assert _num(s, "emptyDesc") == [1]
    assert np.asarray(s.workspace.get("P").cols[1].backend_buffer()).reshape(-1).tolist() == [1, 4]
    assert len(_names(s, "L")[0]) == 63
    assert _names(s, "K") == ["a" * 70, "id"]
    assert _names(s, "C") == ["caf\u00e9 price", "id"]
    assert _names(s, "C") != _names(s, "E")
    assert np.asarray(s.workspace.get("C").cols[1].backend_buffer()).reshape(-1).tolist() == [8]


def test_preserve_does_not_warn_and_duplicates_stay_unique(run):
    _write(run, "a.csv", "Last Name,Last Name,id\nAda,Bea,1\n")
    _write(run, "b.csv", "id,,Last Name\n1,2,3\n")
    s = run("lastwarn('','');"
            "P = readtable(fullfile(d,'a.csv'), 'VariableNamingRule', 'preserve');"
            "[w, id] = lastwarn;"
            "Q = readtable(fullfile(d,'b.csv'), 'VariableNamingRule', 'preserve');"
            "R = readtable(fullfile(d,'a.csv'), 'ReadVariableNames', false, 'VariableNamingRule', 'preserve');"
            "S = readtable(fullfile(d,'a.csv'), 'VariableNames', {'Last Name','score','n'},"
            " 'VariableNamingRule', 'modify');")
    assert _names(s, "P") == ["Last Name", "Last Name_1", "id"]
    assert s.workspace.get("w").text == ""
    assert s.workspace.get("id").text == ""
    assert _names(s, "Q") == ["id", "Var2", "Last Name"]
    assert _names(s, "R") == ["Var1", "Var2", "Var3"]
    assert _names(s, "S") == ["Last Name", "score", "n"]
    assert np.asarray(s.workspace.get("P").cols[2].backend_buffer()).reshape(-1).tolist() == [1]


def test_rule_on_format_range_and_delimiter(run):
    _write(run, "a.txt", "# skip\nLast Name;when;score\nAda;2020-01-02;9\nBea;2020-03-04;8\n")
    s = run("T = readtable(fullfile(d,'a.txt'), 'HeaderLines', 1, 'Delimiter', 'semi',"
            " 'VariableNamingRule', 'preserve', 'Range', 'A:C', 'DatetimeType', 'text');"
            "F = readtable(fullfile(d,'a.txt'), 'HeaderLines', 1, 'Delimiter', 'semi',"
            " 'Format', '%s%s%f', 'VariableNamingRule', 'preserve');")
    assert _names(s, "T") == ["Last Name", "when", "score"]
    assert np.asarray(s.workspace.get("T").cols[2].backend_buffer()).reshape(-1).tolist() == [9, 8]
    assert _names(s, "F") == ["Last Name", "when", "score"]
    assert np.asarray(s.workspace.get("F").cols[2].backend_buffer()).reshape(-1).tolist() == [9, 8]


def test_detect_records_the_rule_and_readtable_uses_those_names(run):
    _write(run, "a.csv", "Last Name,2nd\nAda,1\nBea,2\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'), 'VariableNamingRule', 'preserve');"
            "plain = detectImportOptions(fullfile(d,'a.csv'));"
            "T = readtable(fullfile(d,'a.csv'), opts);"
            "D = readtable(fullfile(d,'a.csv'), plain);"
            "rule = opts.VariableNamingRule;"
            "kept = opts.VariableNamingRule;"
            "opts.VariableNamingRule = 'modify';"
            "still = strjoin(opts.VariableNames, '|');"
            "back = readtable(fullfile(d,'a.csv'), opts);"
            "opts.VariableNamingRule = 'preserve';"
            "opts.VariableNames = {'Last Name','score'};"
            "opts.SelectedVariableNames = {'Last Name'};"
            "one = setvaropts(opts, 'Last Name', 'Type', 'char');"
            "R = readtable(fullfile(d,'a.csv'), one);"
            "plain.VariableNamingRule = 'preserve';"
            "frozen = strjoin(plain.VariableNames, '|');")
    assert s.workspace.get("opts").variable_naming_rule == "preserve"
    assert s.workspace.get("rule").text == "preserve"
    assert "VariableNamingRule" in s.workspace.get("opts").display_text()
    assert _names(s, "T") == ["Last Name", "2nd"]
    assert _names(s, "D") == ["LastName", "x2nd"]
    assert s.workspace.get("plain").variable_naming_rule == "preserve"
    assert s.workspace.get("frozen").text == "LastName|x2nd"
    assert s.workspace.get("still").text == "Last Name|2nd"
    assert _names(s, "back") == ["Last Name", "2nd"]
    assert [v.name for v in s.workspace.get("one").variables] == ["Last Name", "score"]
    assert s.workspace.get("one").variables[0].type == "char"
    assert _names(s, "R") == ["Last Name"]
    assert s.workspace.get("kept").text == "preserve"


def test_modify_still_rejects_an_identifier_that_preserve_accepts(run):
    _write(run, "a.csv", "id,score\n1,2\n")
    run("opts = detectImportOptions(fullfile(d,'a.csv'));")
    with pytest.raises(EvalError) as ei:
        run("opts.VariableNames = {'a b','score'};")
    assert ei.value.identifier == "MATLAB:table:InvalidVarNames"
    s = run("opts.VariableNamingRule = 'preserve';"
            "opts.VariableNames = {'a b','score'};"
            "T = readtable(fullfile(d,'a.csv'), opts);"
            "opts.VariableNamingRule = 'modify';")
    assert _names(s, "T") == ["a b", "score"]
    with pytest.raises(EvalError) as ei:
        run("opts.VariableNames = {'a b','score'};")
    assert ei.value.identifier == "MATLAB:table:InvalidVarNames"
    assert "Traceback" not in str(ei.value)


def test_bad_values_and_opts_name_value_are_eval_errors(run):
    _write(run, "a.csv", "Last Name,id\nAda,1\n")
    cases = [
        ("readtable(fullfile(d,'a.csv'), 'VariableNamingRule', 1)", "MATLAB:readtable:InvalidVariableNamingRule"),
        ("readtable(fullfile(d,'a.csv'), 'VariableNamingRule', 'banana')",
         "MATLAB:readtable:InvalidVariableNamingRule"),
        ("readtable(fullfile(d,'a.csv'), 'VariableNamingRule', 'numbered')",
         "MATLAB:readtable:InvalidVariableNamingRule"),
        ("readtable(fullfile(d,'missing.csv'), 'VariableNamingRule', 'nope')",
         "MATLAB:readtable:InvalidVariableNamingRule"),
        ("detectImportOptions(fullfile(d,'a.csv'), 'VariableNamingRule', 'preserve ')",
         "MATLAB:readtable:InvalidVariableNamingRule"),
        ("detectImportOptions(fullfile(d,'missing.csv'), 'VariableNamingRule', 'nope')",
         "MATLAB:readtable:InvalidVariableNamingRule"),
    ]
    for code, ident in cases:
        with pytest.raises(EvalError) as ei:
            run(code)
        assert ei.value.identifier == ident
        assert "modify" in str(ei.value) and "preserve" in str(ei.value)
        assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'), 'VariableNamingRule', 'preserve');")
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), opts, 'VariableNamingRule', 'preserve')")
    assert ei.value.identifier == "MATLAB:textio:textio:UnknownParameter"
    with pytest.raises(EvalError) as ei:
        run("opts.VariableNamingRule = 'banana';")
    assert ei.value.identifier == "MATLAB:readtable:InvalidVariableNamingRule"
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'missing.csv'), 'VariableNamingRule', 'preserve')")
    assert ei.value.identifier == "MATLAB:textio:textio:FileNotFound"
    assert s.workspace.get("opts").names == ["Last Name", "id"]


def test_spreadsheet_is_rejected_before_the_file_is_opened(run):
    _write(run, "a.csv", "Last Name,id\nAda,1\n")
    _write(run, "book.xlsx", "Last Name,id\nAda,1\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'));")
    for ext in (".xlsx", ".xls", ".xlsm", ".xlsb", ".ods"):
        for value in ("preserve", "nope"):
            with pytest.raises(EvalError) as ei:
                run(f"readtable(fullfile(d,'missing{ext}'), 'VariableNamingRule', '{value}')")
            assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
            assert not (run.dir / f"missing{ext}").exists()
            with pytest.raises(EvalError) as ei:
                run(f"detectImportOptions(fullfile(d,'missing{ext}'), 'VariableNamingRule', '{value}')")
            assert ei.value.identifier == "MATLAB:detectImportOptions:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'book.xlsx'), 'VariableNamingRule', 'preserve')")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'missing.xlsx'), 'Format', '%f', 'VariableNamingRule', 'nope')")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    assert not (run.dir / "missing.xlsx").exists()
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), 'FileType', 'spreadsheet', 'VariableNamingRule', 'nope')")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("detectImportOptions(fullfile(d,'a.csv'), 'FileType', 'spreadsheet', 'VariableNamingRule', 'preserve')")
    assert ei.value.identifier == "MATLAB:detectImportOptions:UnsupportedFileType"
    assert s.workspace.get("opts").matlab_class() == "DelimitedTextImportOptions"
    assert s.workspace.get("opts").names == ["LastName", "id"]

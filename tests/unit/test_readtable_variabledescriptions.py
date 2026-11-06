"""readtable stores original headers in VariableDescriptions when it rewrites them (#1045)."""

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


def _num(s, name):
    return np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def _txt(s, name):
    return s.workspace.get(name).text


def _names(s, table="T"):
    return list(s.workspace.get(table).names)


def _write(run, name, body, encoding="utf-8"):
    (run.dir / name).write_text(body, encoding=encoding)


def test_rewritten_headers_are_a_row_cell_including_valid_names(run):
    _write(run, "a.csv", "id, Last Name,2nd,a/b\nAda,1,2,3\nBea,4,5,6\n")
    _write(run, "long.csv", ("a" * 70) + ",id\n1,2\n")
    _write(run, "cafe.csv", "caf\u00e9 price,id\n9,8\n", encoding="latin-1")
    _write(run, "ok.csv", "id,score\n1,2\n")
    s = run("lastwarn('','');"
            "T = readtable(fullfile(d,'a.csv'));"
            "[w, id] = lastwarn;"
            "desc = strjoin(T.Properties.VariableDescriptions, '|');"
            "sz = size(T.Properties.VariableDescriptions);"
            "cls = class(T.Properties.VariableDescriptions);"
            "one = class(T.Properties.VariableDescriptions{1});"
            "L = readtable(fullfile(d,'long.csv'));"
            "ld = strjoin(L.Properties.VariableDescriptions, '|');"
            "C = readtable(fullfile(d,'cafe.csv'));"
            "cd = strjoin(C.Properties.VariableDescriptions, '|');"
            "lastwarn('','');"
            "K = readtable(fullfile(d,'ok.csv'));"
            "[w2, id2] = lastwarn;"
            "emptyOk = double(isempty(K.Properties.VariableDescriptions));")
    assert _names(s, "T") == ["id", "LastName", "x2nd", "a_b"]
    assert _txt(s, "desc") == "id| Last Name|2nd|a/b"
    assert _num(s, "sz") == [1, 4]
    assert _txt(s, "cls") == "cell"
    assert _txt(s, "one") == "char"
    assert _txt(s, "id") == "MATLAB:table:ModifiedAndSavedVarnames"
    assert "VariableDescriptions" in _txt(s, "w")
    assert _txt(s, "ld") == ("a" * 70) + "|id"
    assert len(_names(s, "L")[0]) == 63
    assert _txt(s, "cd") == "caf\u00e9 price|id"
    assert _names(s, "C")[0] == "caf\u00e9Price"
    assert _names(s, "K") == ["id", "score"]
    assert _num(s, "emptyOk") == [1]
    assert _txt(s, "id2") == ""
    assert [s.workspace.get("T").cols[0].rows[i][0].text for i in range(2)] == ["Ada", "Bea"]


def test_preserve_duplicates_blanks_and_supplied_names(run):
    _write(run, "a.csv", "Last Name,2nd\nAda,1\n")
    _write(run, "dup.csv", "id,id\n1,2\n")
    _write(run, "both.csv", "Last Name,Last Name\nAda,Bea\n")
    _write(run, "gap.csv", "id,,Last Name\n1,2,3\n")
    _write(run, "pad.csv", "id,   ,x y\n1,2,3\n")
    s = run("lastwarn('','');"
            "P = readtable(fullfile(d,'a.csv'), 'VariableNamingRule', 'preserve');"
            "[w, id] = lastwarn;"
            "emptyP = double(isempty(P.Properties.VariableDescriptions));"
            "D = readtable(fullfile(d,'dup.csv'));"
            "[w2, id2] = lastwarn;"
            "emptyD = double(isempty(D.Properties.VariableDescriptions));"
            "B = readtable(fullfile(d,'both.csv'));"
            "bd = strjoin(B.Properties.VariableDescriptions, '|');"
            "G = readtable(fullfile(d,'gap.csv'), 'VariableNamingRule', 'preserve');"
            "gd = strjoin(G.Properties.VariableDescriptions, '|');"
            "M = readtable(fullfile(d,'pad.csv'));"
            "md = strjoin(M.Properties.VariableDescriptions, '|');"
            "Q = readtable(fullfile(d,'pad.csv'), 'VariableNamingRule', 'preserve');"
            "emptyQ = double(isempty(Q.Properties.VariableDescriptions));"
            "lastwarn('','');"
            "S = readtable(fullfile(d,'a.csv'), 'VariableNames', {'a','b'});"
            "R = readtable(fullfile(d,'a.csv'), 'ReadVariableNames', false);"
            "[w3, id3] = lastwarn;"
            "emptyS = double(isempty(S.Properties.VariableDescriptions) && "
            "isempty(R.Properties.VariableDescriptions));")
    assert _names(s, "P") == ["Last Name", "2nd"]
    assert _num(s, "emptyP") == [1]
    assert _txt(s, "w") == "" and _txt(s, "id") == ""
    assert _names(s, "D") == ["id", "id_1"]
    assert _num(s, "emptyD") == [1]
    assert _txt(s, "id2") == ""
    assert _names(s, "B") == ["LastName", "LastName_1"]
    assert _txt(s, "bd") == "Last Name|Last Name"
    assert _names(s, "G") == ["id", "Var2", "Last Name"]
    assert _txt(s, "gd") == "id||Last Name"
    assert _names(s, "M") == ["id", "Var2", "xY"]
    assert _txt(s, "md") == "id|   |x y"
    assert _names(s, "Q") == ["id", "   ", "x y"]
    assert _num(s, "emptyQ") == [1]
    assert _names(s, "S") == ["a", "b"]
    assert _names(s, "R") == ["Var1", "Var2"]
    assert _num(s, "emptyS") == [1]
    assert _txt(s, "id3") == ""


def test_format_range_and_import_options(run):
    _write(run, "a.csv", "id,Last Name,score\nAda,1,9\nBea,2,8\n")
    _write(run, "wide.csv", "id,Last Name,extra\n1,Ada,9\n")
    s = run("lastwarn('','');"
            "F = readtable(fullfile(d,'a.csv'), 'Format', '%s%f');"
            "fd = strjoin(F.Properties.VariableDescriptions, '|');"
            "A = readtable(fullfile(d,'wide.csv'), 'Format', 'auto', 'Range', 'A:B');"
            "ad = strjoin(A.Properties.VariableDescriptions, '|');"
            "lastwarn('','');"
            "K = readtable(fullfile(d,'a.csv'), 'Format', '%s%*s%f');"
            "[w, id] = lastwarn;"
            "emptyK = double(isempty(K.Properties.VariableDescriptions));"
            "lastwarn('','');"
            "opts = detectImportOptions(fullfile(d,'a.csv'));"
            "[w2, id2] = lastwarn;"
            "lastwarn('','');"
            "T = readtable(fullfile(d,'a.csv'), opts);"
            "[w3, id3] = lastwarn;"
            "td = strjoin(T.Properties.VariableDescriptions, '|');"
            "opts.SelectedVariableNames = {'LastName','score'};"
            "S = readtable(fullfile(d,'a.csv'), opts);"
            "sd = strjoin(S.Properties.VariableDescriptions, '|');"
            "popts = detectImportOptions(fullfile(d,'a.csv'), 'VariableNamingRule', 'preserve');"
            "P = readtable(fullfile(d,'a.csv'), popts);"
            "emptyP = double(isempty(P.Properties.VariableDescriptions));"
            "ropts = detectImportOptions(fullfile(d,'wide.csv'), 'Range', 'A:B');"
            "R = readtable(fullfile(d,'wide.csv'), ropts);"
            "rd = strjoin(R.Properties.VariableDescriptions, '|');")
    assert _names(s, "F") == ["id", "LastName"]
    assert _txt(s, "fd") == "id|Last Name"
    assert _txt(s, "ad") == "id|Last Name"
    assert _names(s, "K") == ["id", "score"]
    assert _num(s, "emptyK") == [1]
    assert _txt(s, "id") == ""
    assert _txt(s, "id2") == "MATLAB:table:ModifiedAndSavedVarnames"
    assert "VariableDescriptions" in _txt(s, "w2")
    assert _txt(s, "id3") == ""
    assert _txt(s, "w3") == ""
    assert _names(s, "T") == ["id", "LastName", "score"]
    assert _txt(s, "td") == "id|Last Name|score"
    assert _names(s, "S") == ["LastName", "score"]
    assert _txt(s, "sd") == "Last Name|score"
    assert _names(s, "P") == ["id", "Last Name", "score"]
    assert _num(s, "emptyP") == [1]
    assert _names(s, "R") == ["id", "LastName"]
    assert _txt(s, "rd") == "id|Last Name"
    assert np.asarray(s.workspace.get("F").cols[1].backend_buffer()).reshape(-1).tolist() == [1, 2]


def test_descriptions_follow_the_variables(run):
    _write(run, "a.csv", "id,Last Name,2nd\nAda,1,2\nBea,4,5\n")
    _write(run, "ok.csv", "score\n9\n8\n")
    s = run("T = readtable(fullfile(d,'a.csv'));"
            "C = T(:, [1 3]);"
            "cd = strjoin(C.Properties.VariableDescriptions, '|');"
            "R = removevars(T, 'LastName');"
            "rd = strjoin(R.Properties.VariableDescriptions, '|');"
            "V = movevars(T, 'x2nd', 'Before', 'id');"
            "vd = strjoin(V.Properties.VariableDescriptions, '|');"
            "A = addvars(T, [7;8], 'NewVariableNames', 'extra');"
            "ad = strjoin(A.Properties.VariableDescriptions, '|');"
            "U = readtable(fullfile(d,'ok.csv'));"
            "H = [T(:, 1) U];"
            "hd = strjoin(H.Properties.VariableDescriptions, '|');"
            "T.LastName = [];"
            "dd = strjoin(T.Properties.VariableDescriptions, '|');")
    assert _names(s, "C") == ["id", "x2nd"]
    assert _txt(s, "cd") == "id|2nd"
    assert _txt(s, "rd") == "id|2nd"
    assert _names(s, "V") == ["x2nd", "id", "LastName"]
    assert _txt(s, "vd") == "2nd|id|Last Name"
    assert _txt(s, "ad") == "id|Last Name|2nd|"
    assert _names(s, "U") == ["score"]
    assert _txt(s, "hd") == "id|"
    assert _names(s, "T") == ["id", "x2nd"]
    assert _txt(s, "dd") == "id|2nd"


def test_spreadsheet_still_raises_before_the_file_is_opened(run):
    _write(run, "a.csv", "Last Name,id\nAda,1\n")
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'missing.xlsx'))")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    assert not (run.dir / "missing.xlsx").exists()
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), 'FileType', 'spreadsheet')")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("detectImportOptions(fullfile(d,'missing.xlsx'))")
    assert ei.value.identifier == "MATLAB:detectImportOptions:UnsupportedFileType"
    assert not (run.dir / "missing.xlsx").exists()

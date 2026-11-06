"""readtable and detectImportOptions Range for delimited text (#1041)."""

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


def _write(run, name, body):
    (run.dir / name).write_text(body)


def test_rectangle_numeric_case_and_swapped_corners(run):
    _write(run, "a.csv", "skip,me\nid,name,score\n1,ann,10\n2,bob,20\n3,cy,30\n")
    s = run(
        "A = readtable(fullfile(d,'a.csv'), 'Range', 'B2:C4');"
        "B = readtable(fullfile(d,'a.csv'), 'Range', 'c4:b2');"
        "C = readtable(fullfile(d,'a.csv'), 'Range', [2 2 4 3]);"
        "va = A.score'; vb = B.score'; vc = C.score';"
        "na = strjoin(A.Properties.VariableNames, ',');"
    )
    assert _num(s, "va") == _num(s, "vb") == _num(s, "vc") == [10, 20]
    assert _txt(s, "na") == "name,score"
    assert [s.workspace.get("A").cols[0].rows[i][0].text for i in range(2)] == ["ann", "bob"]


def test_start_cell_reads_to_the_end_and_trims_a_trailing_empty_column(run):
    _write(run, "a.csv", "id,name,score,\n1,ann,10,\n2,bob,20,\n3,cy,30,\n")
    s = run(
        "F = readtable(fullfile(d,'a.csv'));"
        "E = readtable(fullfile(d,'a.csv'), 'Range', '');"
        "S = readtable(fullfile(d,'a.csv'), 'Range', 'C2', 'ReadVariableNames', false);"
        "N = readtable(fullfile(d,'a.csv'), 'Range', [2 3], 'ReadVariableNames', false);"
        "nf = strjoin(F.Properties.VariableNames, ',');"
        "ne = strjoin(E.Properties.VariableNames, ',');"
        "ns = strjoin(S.Properties.VariableNames, ',');"
        "vs = S.Var1'; vn = N.Var1';"
    )
    assert _txt(s, "nf") == _txt(s, "ne") == "id,name,score,Var4"
    assert s.workspace.get("F").nrows == s.workspace.get("E").nrows == 3
    assert _txt(s, "ns") == "Var1"
    assert _num(s, "vs") == _num(s, "vn") == [10, 20, 30]


def test_explicit_rectangle_keeps_an_empty_field(run):
    _write(run, "a.csv", "a,b,\n1,,\n")
    s = run(
        "T = readtable(fullfile(d,'a.csv'), 'Range', 'A1:C2');"
        "n = strjoin(T.Properties.VariableNames, ',');"
        "a = T.a'; b = T.b'; c = T.Var3'; h = height(T);"
    )
    assert _txt(s, "n") == "a,b,Var3"
    assert _num(s, "h") == [1]
    assert _num(s, "a") == [1]
    assert np.isnan(_num(s, "b")[0]) and np.isnan(_num(s, "c")[0])


def test_row_range_trims_leading_and_trailing_empty_columns(run):
    _write(run, "a.csv", ",name,score,\n,ann,10,\n,bob,20,\n")
    s = run(
        "T = readtable(fullfile(d,'a.csv'), 'Range', '1:3');"
        "n = strjoin(T.Properties.VariableNames, ','); v = T.score';"
    )
    assert _txt(s, "n") == "name,score"
    assert _num(s, "v") == [10, 20]


def test_column_range_header_lines_and_column_aa(run):
    _write(run, "a.csv", "# c\nid,name,score\n1,ann,10\n2,bob,20\n")
    _write(run, "wide.csv", ",".join(f"h{i}" for i in range(1, 28)) + "\n" + ",".join(str(i) for i in range(1, 28)) + "\n")
    _write(run, "blank.csv", "\nid,name,score\n1,ann,10\n")
    s = run(
        "T = readtable(fullfile(d,'a.csv'), 'Range', 'B:C', 'NumHeaderLines', 1);"
        "U = readtable(fullfile(d,'a.csv'), 'Range', 'b:c', 'HeaderLines', 1);"
        "W = readtable(fullfile(d,'wide.csv'), 'Range', 'AA:AA');"
        "B = readtable(fullfile(d,'blank.csv'), 'Range', 'B:C');"
        "n = strjoin(T.Properties.VariableNames, ',');"
        "v = T.score'; u = U.score'; w = W.h27'; b = B.score';"
    )
    assert _txt(s, "n") == "name,score"
    assert _num(s, "v") == _num(s, "u") == [10, 20]
    assert _num(s, "w") == [27]
    assert _num(s, "b") == [10]
    assert [s.workspace.get("B").cols[0].rows[i][0].text for i in range(1)] == ["ann"]


def test_header_lines_only_with_a_column_range(run):
    _write(run, "a.csv", "id,score\n1,2\n")
    for code in (
        "readtable(fullfile(d,'a.csv'), 'Range', '1:2', 'NumHeaderLines', 1)",
        "readtable(fullfile(d,'a.csv'), 'Range', 'A1:B2', 'HeaderLines', 1)",
    ):
        with pytest.raises(EvalError) as ei:
            run(code)
        assert ei.value.identifier == "MATLAB:textio:textio:InvalidRange"
        assert "column-select" in str(ei.value)
        assert "Traceback" not in str(ei.value)


def test_readvariable_names_false_and_callers_names(run):
    _write(run, "a.csv", "a,b,c\n1,2,3\n4,5,6\n")
    s = run(
        "T = readtable(fullfile(d,'a.csv'), 'Range', 'B2:C3', 'ReadVariableNames', false);"
        "U = readtable(fullfile(d,'a.csv'), 'Range', 'B:C', 'VariableNames', {'left','right'});"
        "t1 = T.Var1'; t2 = T.Var2'; u = U.right'; n = strjoin(U.Properties.VariableNames, ',');"
    )
    assert _num(s, "t1") == [2, 5]
    assert _num(s, "t2") == [3, 6]
    assert _txt(s, "n") == "left,right"
    assert _num(s, "u") == [3, 6]


def test_blank_line_inside_the_window_is_skipped(run):
    _write(run, "a.csv", "a,b\n1,2\n\n3,4\n")
    s = run("T = readtable(fullfile(d,'a.csv'), 'Range', '1:4'); v = T.a'; h = height(T);")
    assert _num(s, "h") == [2]
    assert _num(s, "v") == [1, 3]


def test_treat_as_missing_texttype_delimiter_and_quotes(run):
    _write(run, "m.csv", "id,name,score\n1,ann,NA\n2,bob,4\n")
    _write(run, "semi.txt", "a;b;c\n1;2;3\n4;5;6\n")
    _write(run, "q.csv", '"a,b",c,d\n"1,2",3,4\n')
    s = run(
        "M = readtable(fullfile(d,'m.csv'), 'Range', 'B:C', 'TreatAsMissing', 'NA', 'TextType', 'string');"
        "S = readtable(fullfile(d,'semi.txt'), 'Range', 'B:C', 'Delimiter', 'semi');"
        "Q = readtable(fullfile(d,'q.csv'), 'Range', 'B:C');"
        "ms = M.score'; sv = S.c'; qn = strjoin(Q.Properties.VariableNames, ','); qv = Q.d';"
    )
    got = _num(s, "ms")
    assert np.isnan(got[0]) and got[1] == 4
    assert s.workspace.get("M").cols[0].matlab_class() == "string"
    assert _num(s, "sv") == [3, 6]
    assert _txt(s, "qn") == "c,d"
    assert _num(s, "qv") == [4]


def test_detect_range_is_honored_by_readtable_and_setvaropts(run):
    _write(run, "a.csv", "skip,me\nid,name,score\n1,ann,10\n2,bob,NA\n3,cy,30\n")
    s = run(
        "opts = detectImportOptions(fullfile(d,'a.csv'), 'Range', 'B2:C4');"
        "opts = setvaropts(opts, 'score', 'Type', 'double', 'TreatAsMissing', 'NA');"
        "T = readtable(fullfile(d,'a.csv'), opts);"
        "U = readtable(fullfile(d,'a.csv'), opts, 'ReadVariableNames', false);"
        "opts2 = detectImportOptions(fullfile(d,'a.csv'), 'Range', 'B2:C4', 'ReadVariableNames', false);"
        "T2 = readtable(fullfile(d,'a.csv'), opts2);"
        "n = strjoin(opts.VariableNames, ','); line = opts.VariableNamesLine;"
        "v = T.score'; h = height(T); uh = height(U); uv = U.score';"
        "n2 = strjoin(T2.Properties.VariableNames, ','); h2 = height(T2);"
    )
    assert _txt(s, "n") == "name,score"
    assert _num(s, "line") == [2]
    assert _num(s, "h") == [2]
    got = _num(s, "v")
    assert got[0] == 10 and np.isnan(got[1])
    assert _num(s, "uh") == [3]
    u = _num(s, "uv")
    assert np.isnan(u[0]) and u[1] == 10 and np.isnan(u[2])
    assert _txt(s, "n2") == "Var1,Var2" and _num(s, "h2") == [3]
    assert [s.workspace.get("T2").cols[0].rows[i][0].text for i in range(3)] == ["name", "ann", "bob"]
    assert "Range" not in s.workspace.get("opts").display_text()
    with pytest.raises(EvalError) as ei:
        run("x = opts.Range;")
    assert ei.value.identifier == "MATLAB:noPublicFieldForClass"


def test_spreadsheet_range_raises_before_any_parse(run):
    _write(run, "a.xlsx", "not a workbook")
    for code in (
        "readtable(fullfile(d,'a.xlsx'), 'Range', 'A1:B2')",
        "readtable(fullfile(d,'a.xlsx'), 'Range', 'nope')",
        "detectImportOptions(fullfile(d,'a.xlsx'), 'Range', 'A1')",
    ):
        with pytest.raises(EvalError) as ei:
            run(code)
        assert ei.value.identifier.endswith("UnsupportedFileType")
        assert "spreadsheet" in str(ei.value)
        assert "Traceback" not in str(ei.value)


@pytest.mark.parametrize("code, needle", [
    ("readtable(fullfile(d,'a.csv'), 'Range', 'myTable')", "spreadsheet"),
    ("readtable(fullfile(d,'a.csv'), 'Range', 'A1:B')", "A1"),
    ("readtable(fullfile(d,'a.csv'), 'Range', [0 1])", "Range"),
    ("readtable(fullfile(d,'a.csv'), 'Range', 'A9')", "past the end"),
    ("detectImportOptions(fullfile(d,'a.csv'), 'Range', 'A1', 'VariableNamesLine', 1)", "VariableNamesLine"),
    ("readtable(fullfile(d,'a.csv'), 'Range', 'A:A', 'ExpectedNumVariables', 1)", "ExpectedNumVariables"),
    ("readcell(fullfile(d,'a.csv'), 'Range', 'A1:A2')", "Range"),
])
def test_rejected_ranges(run, code, needle):
    _write(run, "a.csv", "id,score\n1,2\n")
    with pytest.raises(EvalError) as ei:
        run(code)
    assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)
    assert needle in str(ei.value)
    if "ExpectedNumVariables" in code or "readcell" in code:
        assert ei.value.identifier == "MATLAB:textio:textio:UnknownParameter"
    elif "VariableNamesLine" in code:
        assert ei.value.identifier == "MATLAB:detectImportOptions:InconsistentOptions"
    else:
        assert ei.value.identifier == "MATLAB:textio:textio:InvalidRange"

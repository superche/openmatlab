"""detectImportOptions, setvaropts, and readtable(file, opts) for delimited text (#1040)."""

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


def _cell_row(v):
    return [v.rows[0][i].text for i in range(v.shape[1])]


def _snap(col):
    kind = col.matlab_class()
    if kind == "cell":
        return kind, [col.rows[i][0].text for i in range(len(col.rows))]
    if getattr(col, "is_string", False):
        if hasattr(col, "data"):
            return kind, col.data.reshape(-1, order="F").tolist()
        return kind, [col.text]
    if hasattr(col, "v"):
        return kind, col.fmt, np.asarray(col.v).reshape(-1).tolist()
    return kind, np.asarray(col.backend_buffer()).reshape(-1).tolist()


def _equal_snap(a, b):
    assert a[0] == b[0]
    if a[0] == "datetime":
        assert a[1] == b[1]
        left, right = a[2], b[2]
    else:
        left, right = a[1], b[1]
    assert len(left) == len(right)
    for x, y in zip(left, right):
        if isinstance(x, float) and np.isnan(x):
            assert isinstance(y, float) and np.isnan(y)
        else:
            assert x == y


@pytest.mark.parametrize("name, body, extra", [
    ("a.csv", "id,name,when,score\n1,ann,2020-01-02,3.5\n2,bob,,\n", ""),
    ("q.csv", 'first name,2nd\n"a, b",1\n', ""),
    ("m.csv", "id,score,note\n1,10,ok\n2,NA,NA\n3,,\n", ", 'TreatAsMissing', {'NA',''}"),
    ("s.csv", "id,name\n1,ann\n2,bob\n", ", 'TextType', 'string'"),
    ("b.csv", "\nid,score\n1,2\n", ""),
    ("t.txt", "a\tb\n1\t2\n3\t4\n", ""),
    ("semi.txt", "a;b\n1;2\n", ", 'Delimiter', 'semi'"),
    ("h.csv", "# c\nid,score\n1,2\n3,4\n", ", 'NumHeaderLines', 1"),
    ("h2.csv", "# c\nid,score\n1,2\n", ", 'HeaderLines', 1"),
    ("n.txt", "1\t2\n3\t4\n", ", 'ReadVariableNames', false"),
    ("only.csv", "id,score\n", ""),
    ("sp.txt", "a b\n1 2\n3 4\n", ""),
])
def test_detect_then_read_matches_readtable(run, name, body, extra):
    (run.dir / name).write_text(body)
    s = run(
        f"T = readtable(fullfile(d,'{name}'){extra});"
        f"opts = detectImportOptions(fullfile(d,'{name}'){extra});"
        f"U = readtable(fullfile(d,'{name}'), opts);"
    )
    t, u = s.workspace.get("T"), s.workspace.get("U")
    assert t.names == u.names and t.nrows == u.nrows
    assert len(t.cols) == len(u.cols)
    for a, b in zip(t.cols, u.cols):
        _equal_snap(_snap(a), _snap(b))


def test_setvaropts_type_tokens_subset_and_copy(run):
    (run.dir / "m.csv").write_text("id,score,note\n1,10,ok\n2,NA,NA\n3,4,TBD\n")
    s = run(
        "opts = detectImportOptions(fullfile(d,'m.csv'));"
        "b = setvaropts(opts, 'score', 'Type', 'double', 'TreatAsMissing', 'NA');"
        "b = setvaropts(b, {'note'}, 'TreatAsMissing', {'NA','TBD'});"
        "b.SelectedVariableNames = {'note','score'};"
        "T = readtable(fullfile(d,'m.csv'), b);"
        "ot = opts.VariableTypes; bt = b.VariableTypes; on = opts.SelectedVariableNames;"
        "nm = strjoin(T.Properties.VariableNames, ',');"
        "sc = T.score';"
    )
    assert _cell_row(s.workspace.get("ot")) == ["double", "char", "char"]
    assert _cell_row(s.workspace.get("bt")) == ["double", "double", "char"]
    assert _cell_row(s.workspace.get("on")) == ["id", "score", "note"]
    assert _txt(s, "nm") == "note,score"
    got = _num(s, "sc")
    assert got[0] == 10 and got[2] == 4 and np.isnan(got[1])
    note = s.workspace.get("T").cols[0]
    assert [note.rows[i][0].text for i in range(len(note.rows))] == ["ok", "", ""]


def test_setvaropts_on_every_variable_by_index_and_logical(run):
    (run.dir / "a.csv").write_text("x,y\n1,2\n3,4\n")
    s = run(
        "opts = detectImportOptions(fullfile(d,'a.csv'));"
        "a = setvaropts(opts, 'Type', 'char');"
        "b = setvaropts(opts, 2, 'Type', 'string');"
        "c = setvaropts(opts, [false true], 'TreatAsMissing', '2');"
        "ta = a.VariableTypes; tb = b.VariableTypes;"
        "A = readtable(fullfile(d,'a.csv'), a); B = readtable(fullfile(d,'a.csv'), b);"
        "C = readtable(fullfile(d,'a.csv'), c); cx = C.x'; cy = C.y';"
    )
    assert _cell_row(s.workspace.get("ta")) == ["char", "char"]
    assert _cell_row(s.workspace.get("tb")) == ["double", "string"]
    assert s.workspace.get("A").cols[0].matlab_class() == "cell"
    assert s.workspace.get("B").cols[1].matlab_class() == "string"
    assert _num(s, "cx") == [1, 3]
    got = _num(s, "cy")
    assert np.isnan(got[0]) and got[1] == 4


def test_property_rename_delimiter_and_names_line(run):
    (run.dir / "a.txt").write_text("a,b\n1,2\n3,4\n")
    (run.dir / "semi.txt").write_text("a;b\n5;6\n")
    s = run(
        "opts = detectImportOptions(fullfile(d,'a.txt'), 'Delimiter', ',');"
        "opts.VariableNames = {'left','right'};"
        "opts.SelectedVariableNames = {'right'};"
        "opts.Delimiter = ';';"
        "T = readtable(fullfile(d,'semi.txt'), opts); v = T.right';"
        "n = opts.VariableNamesLine;"
    )
    assert _num(s, "v") == [6]
    assert _num(s, "n") == [1]
    assert s.workspace.get("T").names == ["right"]


def test_variable_names_line_and_readvariablenames_false(run):
    (run.dir / "a.csv").write_text("skip\nid,score\n1,10\n2,20\n")
    s = run(
        "opts = detectImportOptions(fullfile(d,'a.csv'), 'VariableNamesLine', 2);"
        "T = readtable(fullfile(d,'a.csv'), opts); v = T.score';"
        "U = readtable(fullfile(d,'a.csv'), opts, 'ReadVariableNames', false); h = height(U); u = U.score';"
    )
    assert _num(s, "v") == [10, 20]
    assert _num(s, "h") == [3]
    got = _num(s, "u")
    assert np.isnan(got[0]) and got[1] == 10 and got[2] == 20


def test_variable_names_line_zero_reads_header_as_data(run):
    (run.dir / "a.csv").write_text("id,score\n1,10\n")
    s = run(
        "opts = detectImportOptions(fullfile(d,'a.csv'));"
        "opts.VariableNamesLine = 0;"
        "T = readtable(fullfile(d,'a.csv'), opts); h = height(T);"
    )
    assert _num(s, "h") == [2]


def test_modified_names_warn_once(run):
    (run.dir / "q.csv").write_text('first name,2nd\n"a, b",1\n')
    s = run(
        "opts = detectImportOptions(fullfile(d,'q.csv'));"
        "n = strjoin(opts.VariableNames, ',');"
        "[w, id] = lastwarn;"
        "lastwarn('','');"
        "T = readtable(fullfile(d,'q.csv'), opts);"
        "[w2, id2] = lastwarn;"
    )
    assert _txt(s, "n") == "firstName,x2nd"
    assert _txt(s, "id") == "MATLAB:table:ModifiedAndSavedVarnames"
    assert "modified" in _txt(s, "w")
    assert _txt(s, "id2") == ""
    assert s.workspace.get("T").names == ["firstName", "x2nd"]


def test_class_and_display(run):
    (run.dir / "a.csv").write_text("id,score\n1,2\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv')); c = class(opts);")
    assert _txt(s, "c") == "DelimitedTextImportOptions"
    shown = s.workspace.get("opts").display_text()
    assert "Delimiter" in shown and "'id'" in shown and "VariableNamesLine" in shown


def test_extra_columns_are_an_error(run):
    (run.dir / "a.csv").write_text("id,score\n1,2\n")
    (run.dir / "wide.csv").write_text("id,score\n1,2,3\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'));")
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'wide.csv'), opts)")
    assert ei.value.identifier == "MATLAB:readtable:ExtraColumns"
    assert s.workspace.get("opts").matlab_class() == "DelimitedTextImportOptions"


def test_spreadsheet_is_rejected(run):
    (run.dir / "a.csv").write_text("id,score\n1,2\n")
    (run.dir / "a.xlsx").write_text("not a workbook")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'));")
    with pytest.raises(EvalError) as ei:
        run("detectImportOptions(fullfile(d,'a.xlsx'))")
    assert ei.value.identifier == "MATLAB:detectImportOptions:UnsupportedFileType"
    assert "spreadsheet" in str(ei.value) and "Traceback" not in str(ei.value)
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.xlsx'), opts)")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("detectImportOptions(fullfile(d,'a.csv'), 'FileType', 'spreadsheet')")
    assert ei.value.identifier == "MATLAB:detectImportOptions:UnsupportedFileType"
    assert s.workspace.get("opts").names == ["id", "score"]


@pytest.mark.parametrize("code, ident", [
    ("detectImportOptions(fullfile(d,'missing.csv'))", "MATLAB:textio:textio:FileNotFound"),
    ("detectImportOptions(fullfile(d,'a.csv'), 'Format', 'auto')", "MATLAB:textio:textio:UnknownParameter"),
    ("detectImportOptions(fullfile(d,'a.csv'), 'VariableNamingRule', 'preserve')", "MATLAB:textio:textio:UnknownParameter"),
    ("detectImportOptions(5)", "MATLAB:detectImportOptions:InvalidFileName"),
    ("detectImportOptions(fullfile(d,'empty.csv'))", "MATLAB:detectImportOptions:NoData"),
    ("setvaropts(opts, 'FillValue', 0)", "MATLAB:setvaropts:UnknownParameter"),
    ("setvaropts(opts, 'score', 'QuoteRule', 'keep')", "MATLAB:setvaropts:UnknownParameter"),
    ("setvaropts(opts, 'Type', 'categorical')", "MATLAB:setvaropts:InvalidType"),
    ("setvaropts(opts, 'Type', 'duration')", "MATLAB:setvaropts:InvalidType"),
    ("setvaropts(opts, 'Type', 'logical')", "MATLAB:setvaropts:InvalidType"),
    ("setvaropts(opts, 'nope', 'Type', 'char')", "MATLAB:setvaropts:UnknownVariable"),
    ("setvaropts(opts, 9, 'Type', 'char')", "MATLAB:setvaropts:InvalidSelection"),
    ("readtable(fullfile(d,'a.csv'), opts, 'Range', 'A1')", "MATLAB:textio:textio:UnknownParameter"),
    ("readtable(fullfile(d,'a.csv'), opts, 'TreatAsMissing', 'NA')", "MATLAB:textio:textio:UnknownParameter"),
    ("opts.DataLines = [1 2]", "MATLAB:noPublicFieldForClass"),
    ("opts.SelectedVariableNames = {'id','id'}", "MATLAB:setvaropts:InvalidSelection"),
    ("opts.VariableNames = {'a b','score'}", "MATLAB:table:InvalidVarNames"),
])
def test_errors_are_eval_errors(run, code, ident):
    (run.dir / "a.csv").write_text("id,score\n1,2\n")
    (run.dir / "empty.csv").write_text("\n")
    run("opts = detectImportOptions(fullfile(d,'a.csv'));")
    with pytest.raises(EvalError) as ei:
        run(code)
    assert ei.value.identifier == ident
    assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)

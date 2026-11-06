"""readtable and detectImportOptions DatetimeType for delimited text (#1043)."""

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


def _write(run, name, body):
    (run.dir / name).write_text(body)


def _col(s, table, i):
    return s.workspace.get(table).cols[i]


def _cell(col):
    return [col.rows[i][0].text for i in range(len(col.rows))]


def _strings(col):
    from openmatlab.runtime import string_array as sa

    return [None if x is None else str(x) for x in sa.to_grid(col).reshape(-1)]


def test_text_keeps_date_characters_and_leaves_other_columns(run):
    _write(run, "a.csv",
           "id,when,note\n"
           "1,2020-01-02,ok\n"
           "2,NA,x\n"
           "3,,y\n"
           "4,2020-03-04,z\n")
    _write(run, "t.csv", "when\n2020-03-04 01:02:03\n2020-05-06 07:08:09\n")
    s = run("A = readtable(fullfile(d,'a.csv'), 'DatetimeType', 'text', 'TreatAsMissing', 'NA');"
            "B = readtable(fullfile(d,'a.csv'), 'DatetimeType', 'datetime', 'TreatAsMissing', 'NA');"
            "C = readtable(fullfile(d,'a.csv'), 'TreatAsMissing', 'NA');"
            "H = readtable(fullfile(d,'t.csv'), 'DatetimeType', 'text');"
            "P = readtable(fullfile(d,'t.csv'));"
            "e = datetime(2020,1,2); f = datetime(2020,3,4);")
    assert _col(s, "A", 0).matlab_class() == "double"
    assert np.asarray(_col(s, "A", 0).backend_buffer()).reshape(-1).tolist() == [1, 2, 3, 4]
    assert _col(s, "A", 1).matlab_class() == "cell"
    assert _cell(_col(s, "A", 1)) == ["2020-01-02", "", "", "2020-03-04"]
    assert _cell(_col(s, "A", 2)) == ["ok", "x", "y", "z"]
    assert _col(s, "P", 0).matlab_class() == "datetime"
    assert _cell(_col(s, "H", 0)) == ["2020-03-04 01:02:03", "2020-05-06 07:08:09"]
    assert _col(s, "B", 1).matlab_class() == _col(s, "C", 1).matlab_class() == "datetime"
    got = np.asarray(_col(s, "B", 1).v).reshape(-1)
    same = np.asarray(_col(s, "C", 1).v).reshape(-1)
    assert got[0] == np.asarray(s.workspace.get("e").v).reshape(-1)[0]
    assert np.isnan(got[1]) and np.isnan(got[2])
    assert got[3] == np.asarray(s.workspace.get("f").v).reshape(-1)[0]
    assert np.allclose(got, same, equal_nan=True)


def test_string_texttype_and_case(run):
    _write(run, "a.csv", "when,id\n2020-01-02,1\nNA,2\n,3\n")
    s = run("T = readtable(fullfile(d,'a.csv'), 'DatetimeType', 'TEXT', 'TextType', 'string',"
            " 'TreatAsMissing', {'NA',''});"
            'U = readtable(fullfile(d,\'a.csv\'), "DatetimeType", "text");')
    assert _col(s, "T", 0).is_string
    assert _strings(_col(s, "T", 0)) == ["2020-01-02", None, None]
    assert _col(s, "U", 0).matlab_class() == "cell"
    assert _cell(_col(s, "U", 0)) == ["2020-01-02", "NA", ""]


def test_detect_records_the_choice_in_variable_types(run):
    _write(run, "a.csv", "id,when\n1,02-Jan-2020\n2,03-Jan-2020\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'), 'DatetimeType', 'text');"
            "plain = detectImportOptions(fullfile(d,'a.csv'));"
            "T = readtable(fullfile(d,'a.csv'), opts);"
            "D = readtable(fullfile(d,'a.csv'), plain);"
            "back = setvaropts(opts, 'when', 'Type', 'datetime');"
            "R = readtable(fullfile(d,'a.csv'), back);")
    types = s.workspace.get("opts")
    assert [v.type for v in types.variables] == ["double", "char"]
    assert [v.type for v in s.workspace.get("plain").variables] == ["double", "datetime"]
    assert _cell(_col(s, "T", 1)) == ["02-Jan-2020", "03-Jan-2020"]
    assert _col(s, "D", 1).matlab_class() == "datetime"
    assert _col(s, "R", 1).matlab_class() == "datetime"
    assert np.allclose(_col(s, "R", 1).v, _col(s, "D", 1).v)


def test_text_does_not_retype_numbers_mixed_dates_or_placeholders(run):
    _write(run, "a.csv", "n,mix,only,two\n1,2020-01-02,NA,2020-01-02\n2,hello,NA,02-Jan-2020\n")
    s = run("T = readtable(fullfile(d,'a.csv'), 'DatetimeType', 'text', 'TreatAsMissing', 'NA');"
            "U = readtable(fullfile(d,'a.csv'), 'DatetimeType', 'datetime', 'TreatAsMissing', 'NA');")
    assert _col(s, "T", 0).matlab_class() == "double"
    assert _col(s, "T", 1).matlab_class() == "cell"
    assert _cell(_col(s, "T", 1)) == ["2020-01-02", "hello"]
    assert _col(s, "T", 2).matlab_class() == "double"
    assert np.isnan(np.asarray(_col(s, "T", 2).backend_buffer())).all()
    assert _col(s, "T", 3).matlab_class() == _col(s, "U", 3).matlab_class() == "cell"


def test_range_delimiter_and_header_lines(run):
    _write(run, "a.txt", "# skip\nid;when;score\n1;2020-01-02;9\n2;2020-03-04;8\n")
    s = run("T = readtable(fullfile(d,'a.txt'), 'HeaderLines', 1, 'Delimiter', 'semi',"
            " 'DatetimeType', 'text', 'Range', 'B:C');"
            "opts = detectImportOptions(fullfile(d,'a.txt'), 'HeaderLines', 1, 'Delimiter', 'semi',"
            " 'DatetimeType', 'text', 'Range', 'B:C');"
            "U = readtable(fullfile(d,'a.txt'), opts);")
    assert s.workspace.get("T").names == ["when", "score"]
    assert _cell(_col(s, "T", 0)) == ["2020-01-02", "2020-03-04"]
    assert np.asarray(_col(s, "T", 1).backend_buffer()).reshape(-1).tolist() == [9, 8]
    assert [v.type for v in s.workspace.get("opts").variables] == ["char", "double"]
    assert _cell(_col(s, "U", 0)) == ["2020-01-02", "2020-03-04"]


def test_format_datetime_columns_follow_datetimetype(run):
    _write(run, "a.csv", 'when,n\n2020-01-02,1\nhello,2\n')
    _write(run, "c.csv", "when,n\n2020-01-02,1\n2020-03-04,2\n")
    _write(run, "q.csv", 'when\n"2020-01-02"\n"2020-03-04"\n')
    _write(run, "w.csv", "when\n2020-01-02x\n")
    s = run("T = readtable(fullfile(d,'a.csv'), 'Format', '%D%f', 'DatetimeType', 'text');"
            "D = readtable(fullfile(d,'a.csv'), 'Format', '%{yyyy-MM-dd}D%f', 'DatetimeType', 'datetime');"
            "S = readtable(fullfile(d,'a.csv'), 'Format', '%s%f', 'DatetimeType', 'datetime');"
            "A = readtable(fullfile(d,'c.csv'), 'Format', 'auto', 'DatetimeType', 'text');"
            "Q = readtable(fullfile(d,'q.csv'), 'Format', 'auto', 'DatetimeType', 'datetime');"
            "W = readtable(fullfile(d,'w.csv'), 'Format', '%10D', 'DatetimeType', 'text');")
    assert _cell(_col(s, "T", 0)) == ["2020-01-02", "hello"]
    assert np.asarray(_col(s, "T", 1).backend_buffer()).reshape(-1).tolist() == [1, 2]
    assert _col(s, "D", 0).matlab_class() == "datetime"
    assert np.isnan(np.asarray(_col(s, "D", 0).v).reshape(-1)[1])
    assert _cell(_col(s, "S", 0)) == ["2020-01-02", "hello"]
    assert _cell(_col(s, "A", 0)) == ["2020-01-02", "2020-03-04"]
    assert _col(s, "A", 1).matlab_class() == "double"
    assert _col(s, "Q", 0).matlab_class() == "cell"
    assert _cell(_col(s, "Q", 0)) == ["2020-01-02", "2020-03-04"]
    assert _cell(_col(s, "W", 0)) == ["2020-01-02"]


def test_bad_values_are_eval_errors(run):
    _write(run, "a.csv", "when\n2020-01-02\n")
    cases = [
        ("readtable(fullfile(d,'a.csv'), 'DatetimeType', 1)", "MATLAB:readtable:InvalidDatetimeType"),
        ("readtable(fullfile(d,'a.csv'), 'DatetimeType', 'banana')", "MATLAB:readtable:InvalidDatetimeType"),
        ("readtable(fullfile(d,'a.csv'), 'DatetimeType', 'exceldatenum')", "MATLAB:readtable:ExcelDateNumText"),
        ("readtable(fullfile(d,'missing.csv'), 'DatetimeType', 'exceldatenum')",
         "MATLAB:readtable:ExcelDateNumText"),
        ("detectImportOptions(fullfile(d,'a.csv'), 'DatetimeType', 'exceldatenum')",
         "MATLAB:readtable:ExcelDateNumText"),
        ("detectImportOptions(fullfile(d,'missing.csv'), 'DatetimeType', 'nope')",
         "MATLAB:readtable:InvalidDatetimeType"),
    ]
    for code, ident in cases:
        with pytest.raises(EvalError) as ei:
            run(code)
        assert ei.value.identifier == ident
        assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)


def test_spreadsheet_is_rejected_before_the_file_is_opened(run):
    _write(run, "a.csv", "when\n2020-01-02\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'));")
    for ext in (".xlsx", ".xls", ".xlsm", ".xlsb", ".ods"):
        for value in ("text", "exceldatenum"):
            with pytest.raises(EvalError) as ei:
                run(f"readtable(fullfile(d,'missing{ext}'), 'DatetimeType', '{value}')")
            assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
            assert not (run.dir / f"missing{ext}").exists()
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), 'FileType', 'spreadsheet', 'DatetimeType', 'exceldatenum')")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("detectImportOptions(fullfile(d,'missing.xlsx'), 'DatetimeType', 'text')")
    assert ei.value.identifier == "MATLAB:detectImportOptions:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), opts, 'DatetimeType', 'text')")
    assert ei.value.identifier == "MATLAB:textio:textio:UnknownParameter"
    with pytest.raises(EvalError) as ei:
        run("setvaropts(opts, 'DatetimeType', 'text')")
    assert ei.value.identifier == "MATLAB:setvaropts:UnknownParameter"
    with pytest.raises(EvalError) as ei:
        run("setvaropts(opts, 'when', 'DatetimeType', 'text')")
    assert ei.value.identifier == "MATLAB:setvaropts:UnknownParameter"
    with pytest.raises(EvalError) as ei:
        run("opts.DatetimeType = 'text';")
    assert ei.value.identifier == "MATLAB:noPublicFieldForClass"
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), 'VariableNamingRule', 'preserve')")
    assert ei.value.identifier == "MATLAB:textio:textio:UnknownParameter"
    assert s.workspace.get("opts").matlab_class() == "DelimitedTextImportOptions"

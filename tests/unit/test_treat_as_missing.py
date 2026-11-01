"""readtable 'TreatAsMissing' on delimited text (M17 CSV slice of #721).

These tests stay off the four #1039 cases: no ismissing on a char array, no
ismissing/rmmissing/fillmissing of a 0-row table, no rmmissing(A,2) TF check,
and no fillmissing of a single-row table. Columns here are column vectors in
tables of height >= 2.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session
from openmatlab.runtime.string_array import StringArray

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

_CSV = "id,score,note\n1,10,ok\n2,NA,NA\n3,-999,ok\n4,,later\n5,7,\n"


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


def _cell_text(col):
    return [col.rows[i][0].text for i in range(len(col.rows))]


def _strings(v):
    if isinstance(v, StringArray):
        return v.data.reshape(-1).tolist()
    return [v.text]


def test_tokens_flow_into_rmmissing_and_fillmissing(run):
    (run.dir / "m.csv").write_text(_CSV)
    s = run(
        "T = readtable(fullfile(d,'m.csv'), 'TreatAsMissing', {'NA','-999',''});"
        "M = double(ismissing(T)); R = rmmissing(T); h = height(R); rid = R.id';"
        "P = fillmissing(T, 'previous'); ps = P.score';"
        "C = fillmissing(T, 'constant', 0, 'DataVariables', 'score'); cs = C.score';"
    )
    assert np.asarray(s.workspace.get("M").backend_buffer()).tolist() == [
        [0, 0, 0],
        [0, 1, 1],
        [0, 1, 0],
        [0, 1, 0],
        [0, 0, 1],
    ]
    assert _num(s, "h") == [1] and _num(s, "rid") == [1]
    assert _num(s, "ps") == [10, 10, 10, 10, 7]
    assert _num(s, "cs") == [10, 0, 0, 0, 7]
    assert _cell_text(s.workspace.get("T").cols[2]) == ["ok", "", "ok", "later", ""]
    assert _cell_text(s.workspace.get("P").cols[2]) == ["ok", "ok", "ok", "later", "later"]


def test_string_placeholders_are_missing(run):
    (run.dir / "m.csv").write_text(_CSV)
    s = run(
        "T = readtable(fullfile(d,'m.csv'), 'TextType', 'string', 'TreatAsMissing', {'NA','-999',''});"
        "m = double(ismissing(T.note')); P = fillmissing(T, 'previous');"
    )
    assert _num(s, "m") == [0, 1, 0, 0, 1]
    assert _strings(s.workspace.get("T").cols[2]) == ["ok", None, "ok", "later", None]
    assert _strings(s.workspace.get("P").cols[2]) == ["ok", "ok", "ok", "later", "later"]


def test_datetime_placeholder_stays_datetime(run):
    (run.dir / "when.csv").write_text("when\n2020-01-02\nNA\n2020-03-04\n")
    s = run(
        "T = readtable(fullfile(d,'when.csv'), 'TreatAsMissing', {'NA'});"
        "c = class(T.when); n = double(isnat(T.when'));"
    )
    assert _txt(s, "c") == "datetime"
    assert _num(s, "n") == [0, 1, 0]


def test_without_option_sentinel_stays_text(run):
    (run.dir / "m.csv").write_text("score\n1\nNA\n3\n")
    s = run("T = readtable(fullfile(d,'m.csv')); c = class(T.score);")
    assert _txt(s, "c") == "cell"


def test_exact_text_match_is_case_sensitive(run):
    (run.dir / "n.csv").write_text("v\n1\n1.0\n10\n")
    (run.dir / "t.csv").write_text("v\n1\nNULL\nnull\n")
    s = run(
        "N = readtable(fullfile(d,'n.csv'), 'TreatAsMissing', {'1.0'}); nv = N.v';"
        "T = readtable(fullfile(d,'t.csv'), 'TreatAsMissing', {'NULL'});"
    )
    got = _num(s, "nv")
    assert got[0] == 1 and got[2] == 10 and np.isnan(got[1])
    assert _cell_text(s.workspace.get("T").cols[0]) == ["1", "", "null"]


def test_char_string_and_empty_cell_forms(run):
    (run.dir / "a.csv").write_text("v\n1\nNA\n2\n")
    s = run(
        "A = readtable(fullfile(d,'a.csv'), 'TreatAsMissing', ' NA '); a = A.v';"
        "B = readtable(fullfile(d,'a.csv'), 'TreatAsMissing', \"NA\"); b = B.v';"
        "C = readtable(fullfile(d,'a.csv'), 'TreatAsMissing', [\"NA\" \"NA\"]); c = C.v';"
        "D = readtable(fullfile(d,'a.csv'), 'TreatAsMissing', {}); dc = class(D.v);"
    )
    for name in ("a", "b", "c"):
        got = _num(s, name)
        assert got[0] == 1 and got[2] == 2 and np.isnan(got[1])
    assert _txt(s, "dc") == "cell"


def test_blank_text_field_matches_empty_token(run):
    (run.dir / "b.csv").write_text('note\nok\n" "\nNA\n')
    s = run("T = readtable(fullfile(d,'b.csv'), 'TreatAsMissing', {'NA',''}); m = double(ismissing(T.note'));")
    assert _num(s, "m") == [0, 1, 1]
    assert _cell_text(s.workspace.get("T").cols[0]) == ["ok", "", ""]


def test_all_placeholder_column_is_double_nan(run):
    (run.dir / "z.csv").write_text("v\nNA\n-999\n")
    s = run(
        "T = readtable(fullfile(d,'z.csv'), 'TreatAsMissing', {'NA','-999'});"
        "c = class(T.v); n = double(isnan(T.v'));"
    )
    assert _txt(s, "c") == "double"
    assert _num(s, "n") == [1, 1]


def test_spreadsheet_still_errors(run):
    (run.dir / "a.xlsx").write_text("not a workbook")
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.xlsx'), 'TreatAsMissing', {'NA'})")
    assert "spreadsheet" in str(ei.value)
    assert "Traceback" not in str(ei.value)
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"


@pytest.mark.parametrize("code", [
    "readtable(fullfile(d,'a.csv'), 'TreatAsMissing', 1)",
    "readtable(fullfile(d,'a.csv'), 'TreatAsMissing', {'NA', 1})",
    "readtable(fullfile(d,'a.csv'), 'TreatAsMissing', [missing])",
])
def test_bad_treat_as_missing_is_eval_error(run, code):
    (run.dir / "a.csv").write_text("v\n1\n")
    with pytest.raises(EvalError) as ei:
        run(code)
    assert ei.value.identifier == "MATLAB:readtable:InvalidTreatAsMissing"
    assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)


@pytest.mark.parametrize("name", ["Range", "Format", "DatetimeType", "VariableNamingRule"])
def test_unsupported_option_is_eval_error(run, name):
    (run.dir / "a.csv").write_text("v\n1\n")
    with pytest.raises(EvalError) as ei:
        run(f"readtable(fullfile(d,'a.csv'), '{name}', 'x')")
    assert name in str(ei.value)
    assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)
    assert ei.value.identifier == "MATLAB:textio:textio:UnknownParameter"

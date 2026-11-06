"""writetable and writecell QuoteStrings for delimited text (#1047)."""

from __future__ import annotations

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

_ALL = [
    "Var1,Var2,Var3,Var4",
    '"M",45,"New York, NY",1',
    '"F",41,"San Diego, CA",0',
    '"M",36,"Boston, MA",0',
]
_MINIMAL = [
    "Var1,Var2,Var3,Var4",
    'M,45,"New York, NY",1',
    'F,41,"San Diego, CA",0',
    'M,36,"Boston, MA",0',
]
_NONE = [
    "Var1,Var2,Var3,Var4",
    "M,45,New York, NY,1",
    "F,41,San Diego, CA,0",
    "M,36,Boston, MA,0",
]


@pytest.fixture
def run(tmp_path):
    s = Session.create_default()
    r = ReplSession(s)

    def go(code):
        r.run_line(f"d = '{tmp_path.as_posix()}'; " + code)
        return s

    go.dir = tmp_path
    return go


def _txt(s, name):
    return s.workspace.get(name).text


def _example(mode):
    return ("T = table(['M';'F';'M'],[45;41;36], "
            "{'New York, NY';'San Diego, CA';'Boston, MA'},[true;false;false]); "
            f"writetable(T, fullfile(d,'a.csv'), 'Delimiter', ',', 'QuoteStrings', {mode}); "
            "txt = fileread(fullfile(d,'a.csv'));")


def test_public_example_all_minimal_and_none(run):
    s = run(_example("'all'"))
    assert _txt(s, "txt").splitlines() == _ALL
    s = run(_example("'minimal'"))
    assert _txt(s, "txt").splitlines() == _MINIMAL
    s = run(_example("'none'"))
    assert _txt(s, "txt").splitlines() == _NONE
    s = run("writetable(T, fullfile(d,'a.csv')); txt = fileread(fullfile(d,'a.csv'));")
    assert _txt(s, "txt").splitlines() == _MINIMAL
    s = run("writetable(T, fullfile(d,'a.csv'), 'QuoteStrings', \"ALL\"); txt = fileread(fullfile(d,'a.csv'));")
    assert _txt(s, "txt").splitlines() == _ALL


def test_embedded_quote_newline_header_and_row_names(run):
    s = run("writetable(table({'say \"hi\"';'plain'}), fullfile(d,'q.csv')); txt = fileread(fullfile(d,'q.csv')); "
            "R = readtable(fullfile(d,'q.csv')); back = R.Var1{1};")
    assert _txt(s, "txt").splitlines() == ["Var1", '"say ""hi"""', "plain"]
    assert _txt(s, "back") == 'say "hi"'
    s = run("writetable(table({'say \"hi\"'}), fullfile(d,'q.csv'), 'QuoteStrings', 'none'); "
            "txt = fileread(fullfile(d,'q.csv'));")
    assert _txt(s, "txt").splitlines() == ["Var1", 'say "hi"']
    s = run("writecell({sprintf('a\\nb')}, fullfile(d,'n.csv')); txt = fileread(fullfile(d,'n.csv'));")
    assert _txt(s, "txt") == '"a\nb"\n'
    s = run("writetable(table({'NY';'CA'}, 'VariableNames', {'a,b'}), fullfile(d,'h.csv'), 'QuoteStrings', 'all'); "
            "txt = fileread(fullfile(d,'h.csv'));")
    assert _txt(s, "txt").splitlines() == ["a,b", '"NY"', '"CA"']
    s = run("R = table([1;2], 'RowNames', {'r1','r 2'}); "
            "writetable(R, fullfile(d,'r.csv'), 'WriteRowNames', true, 'Delimiter', ' '); "
            "mini = fileread(fullfile(d,'r.csv')); "
            "writetable(R, fullfile(d,'r.csv'), 'WriteRowNames', true, 'Delimiter', ' ', 'QuoteStrings', 'none'); "
            "none = fileread(fullfile(d,'r.csv')); "
            "writetable(R, fullfile(d,'r.csv'), 'WriteRowNames', true, 'QuoteStrings', 'all'); "
            "all = fileread(fullfile(d,'r.csv'));")
    assert _txt(s, "mini").splitlines() == ["Row Var1", "r1 1", '"r 2" 2']
    assert _txt(s, "none").splitlines() == ["Row Var1", "r1 1", "r 2 2"]
    assert _txt(s, "all").splitlines() == ["Row,Var1", '"r1",1', '"r 2",2']


def test_typed_columns_and_writecell(run):
    s = run("U = table(datetime(2020,1,[2;NaN]), duration([1;NaN],2,3), categorical({'NY';''}), "
            "[\"p\"; missing], 'VariableNames', {'when','elapsed','g','s'}); "
            "writetable(U, fullfile(d,'u.csv'), 'QuoteStrings', 'all'); txt = fileread(fullfile(d,'u.csv')); "
            "writetable(table(datetime(2020,1,2,3,4,5)), fullfile(d,'s.csv'), 'Delimiter', ' '); "
            "space = fileread(fullfile(d,'s.csv')); "
            "writetable(table(datetime(2020,1,2,3,4,5)), fullfile(d,'s.csv'), 'Delimiter', ' ', 'QuoteStrings', 'none'); "
            "bare = fileread(fullfile(d,'s.csv')); "
            "writecell({'NY', 45; 'a,b', false; '', string(missing)}, fullfile(d,'w.csv'), 'QuoteStrings', 'all'); "
            "cell = fileread(fullfile(d,'w.csv')); "
            "writecell({datetime(2020,1,2), duration(1,2,3)}, fullfile(d,'w.csv'), 'QuoteStrings', 'all'); "
            "timed = fileread(fullfile(d,'w.csv'));")
    assert _txt(s, "txt").splitlines() == [
        "when,elapsed,g,s",
        '"02-Jan-2020","01:02:03","NY","p"',
        ',"NaN",,',
    ]
    assert _txt(s, "space").splitlines() == ["Var1", '"02-Jan-2020 03:04:05"']
    assert _txt(s, "bare").splitlines() == ["Var1", "02-Jan-2020 03:04:05"]
    assert _txt(s, "cell").splitlines() == ['"NY",45', '"a,b",0', '"",']
    assert _txt(s, "timed").splitlines() == ['"02-Jan-2020","01:02:03"']


@pytest.mark.parametrize("code,ident", [
    ("writetable(T, fullfile(d,'a.csv'), 'QuoteStrings', true)", "MATLAB:writetable:InvalidQuoteStrings"),
    ("writetable(T, fullfile(d,'a.csv'), 'QuoteStrings', false)", "MATLAB:writetable:InvalidQuoteStrings"),
    ("writetable(T, fullfile(d,'a.csv'), 'QuoteStrings', 'true')", "MATLAB:writetable:InvalidQuoteStrings"),
    ("writetable(T, fullfile(d,'a.csv'), 'QuoteStrings', 'false')", "MATLAB:writetable:InvalidQuoteStrings"),
    ("writetable(T, fullfile(d,'a.csv'), 'QuoteStrings', 'nope')", "MATLAB:writetable:InvalidQuoteStrings"),
    ("writetable(T, fullfile(d,'a.csv'), 'QuoteStrings', 1)", "MATLAB:writetable:InvalidQuoteStrings"),
    ("writecell({'a'}, fullfile(d,'a.csv'), 'QuoteStrings', false)", "MATLAB:writecell:InvalidQuoteStrings"),
])
def test_rejected_values_write_no_file(run, code, ident):
    run("T = table({'NY';'CA'});")
    with pytest.raises(EvalError) as ei:
        run(code)
    assert ei.value.identifier == ident
    assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)
    assert not (run.dir / "a.csv").exists()


@pytest.mark.parametrize("ext", [".xlsx", ".xls", ".xlsm", ".xlsb", ".ods"])
def test_spreadsheet_extension_still_rejects_before_bytes(run, ext):
    run("T = table({'NY'});")
    for value in ("'all'", "'nope'"):
        with pytest.raises(EvalError) as ei:
            run(f"writetable(T, fullfile(d,'a{ext}'), 'QuoteStrings', {value})")
        assert ei.value.identifier == "MATLAB:writetable:UnsupportedFileType"
        assert not (run.dir / f"a{ext}").exists()
        with pytest.raises(EvalError) as ei:
            run(f"writecell({{'NY'}}, fullfile(d,'c{ext}'), 'QuoteStrings', {value})")
        assert ei.value.identifier == "MATLAB:writecell:UnsupportedFileType"
        assert not (run.dir / f"c{ext}").exists()

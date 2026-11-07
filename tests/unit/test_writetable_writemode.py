"""writetable WriteMode for delimited text (#1048)."""

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


def _txt(s, name):
    return s.workspace.get(name).text


def _raises(run, code):
    with pytest.raises(EvalError) as ei:
        run(code)
    assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)
    return ei.value.identifier


def test_public_append_example_keeps_the_header(run):
    s = run(
        "T = table({'Monarch Butterfly';'Seven-spot Ladybird'},"
        "{'Lepidoptera';'Coleoptera'},{'Nymphalidae';'Coccinellidae'},[false;true],"
        "'VariableNames', {'InsectSpecies','InsectOrder','InsectFamily','PredatoryInsect'});"
        "writetable(T, fullfile(d,'InsectCollection.txt'), 'WriteRowNames', true);"
        "newInsect = table({'Red-banded leafhopper'},{'Hemiptera'},{'Cicadellidae'},false);"
        "writetable(newInsect, fullfile(d,'InsectCollection.txt'), 'WriteMode', 'Append',"
        "'WriteVariableNames', false, 'WriteRowNames', true);"
        "txt = fileread(fullfile(d,'InsectCollection.txt'));"
        "R = readtable(fullfile(d,'InsectCollection.txt'));"
        "names = strjoin(R.Properties.VariableNames, ',');"
        "species = R.InsectSpecies{3}; pred = R.PredatoryInsect';"
    )
    assert _txt(s, "txt").splitlines() == [
        "InsectSpecies,InsectOrder,InsectFamily,PredatoryInsect",
        "Monarch Butterfly,Lepidoptera,Nymphalidae,0",
        "Seven-spot Ladybird,Coleoptera,Coccinellidae,1",
        "Red-banded leafhopper,Hemiptera,Cicadellidae,0",
    ]
    assert _txt(s, "names") == "InsectSpecies,InsectOrder,InsectFamily,PredatoryInsect"
    assert _txt(s, "species") == "Red-banded leafhopper"
    assert np.asarray(s.workspace.get("pred").backend_buffer()).reshape(-1).tolist() == [0, 1, 0]


def test_append_creates_a_headerless_file_and_overwrite_replaces(run):
    s = run(
        "writetable(table([1;2]), fullfile(d,'a.csv'), 'WriteMode', 'append', 'WriteVariableNames', false);"
        "made = fileread(fullfile(d,'a.csv'));"
        "writetable(table([1;2]), fullfile(d,'b.csv'));"
        "writetable(table([9]), fullfile(d,'b.csv'), 'WriteMode', 'OVERWRITE');"
        "over = fileread(fullfile(d,'b.csv'));"
        "writetable(table([8]), fullfile(d,'b.csv'));"
        "plain = fileread(fullfile(d,'b.csv'));"
        "writetable(table([3]), fullfile(d,'a.csv'), \"WriteMode\", \"append\", \"WriteVariableNames\", false);"
        "again = fileread(fullfile(d,'a.csv'));"
    )
    assert _txt(s, "made").splitlines() == ["1", "2"]
    assert _txt(s, "over").splitlines() == ["Var1", "9"]
    assert _txt(s, "plain").splitlines() == ["Var1", "8"]
    assert _txt(s, "again").splitlines() == ["1", "2", "3"]


def test_append_keeps_existing_bytes_and_starts_a_new_line(run):
    (run.dir / "glued.csv").write_bytes(b"a,b\n1,2")
    (run.dir / "lined.csv").write_bytes(b"a,b\n1,2\n")
    (run.dir / "empty.csv").write_bytes(b"")
    (run.dir / "stay.csv").write_bytes(b"stay\n")
    s = run(
        "writetable(table([3 4]), fullfile(d,'glued.csv'),"
        "'WriteMode', 'append', 'WriteVariableNames', false, 'Delimiter', ';');"
        "glued = fileread(fullfile(d,'glued.csv'));"
        "writetable(table([3 4]), fullfile(d,'lined.csv'), 'WriteMode', 'append', 'WriteVariableNames', false);"
        "lined = fileread(fullfile(d,'lined.csv'));"
        "writetable(table([7;8], {'p';'q'}, [NaN;4], 'VariableNames', {'n','t','x'}), fullfile(d,'empty.csv'),"
        "'WriteMode', 'append', 'WriteVariableNames', false);"
        "empty = fileread(fullfile(d,'empty.csv'));"
        "writetable(table(), fullfile(d,'stay.csv'), 'WriteMode', 'append', 'WriteVariableNames', false);"
        "stay = fileread(fullfile(d,'stay.csv'));"
    )
    assert _txt(s, "glued") == "a,b\n1,2\n3;4\n"
    assert _txt(s, "lined") == "a,b\n1,2\n3,4\n"
    assert _txt(s, "empty").splitlines() == ["7,p,", "8,q,4"]
    assert _txt(s, "stay") == "stay\n"


def test_append_row_names_and_quotes_only_the_new_rows(run):
    s = run(
        "T = table([1;2], 'RowNames', {'r1','r 2'});"
        "writetable(T, fullfile(d,'r.csv'), 'WriteRowNames', true);"
        "writetable(table([3], 'RowNames', {'r3'}), fullfile(d,'r.csv'),"
        "'WriteMode', 'append', 'WriteVariableNames', false, 'WriteRowNames', true);"
        "rows = fileread(fullfile(d,'r.csv'));"
        "writetable(table({'NY, NY';'LA'}), fullfile(d,'q.csv'));"
        "writetable(table({'CA'}), fullfile(d,'q.csv'), 'WriteMode', 'append',"
        "'WriteVariableNames', false, 'QuoteStrings', 'all');"
        "quoted = fileread(fullfile(d,'q.csv'));"
    )
    assert _txt(s, "rows").splitlines() == ["Row,Var1", "r1,1", "r 2,2", "r3,3"]
    assert _txt(s, "quoted").splitlines() == ["Var1", '"NY, NY"', "LA", '"CA"']


def test_filetype_spreadsheet_on_csv_stays_delimited_text(run):
    s = run(
        "writetable(table([1;2]), fullfile(d,'a.csv'), 'FileType', 'spreadsheet');"
        "writetable(table([3]), fullfile(d,'a.csv'), 'FileType', 'spreadsheet',"
        "'WriteMode', 'append', 'WriteVariableNames', false);"
        "txt = fileread(fullfile(d,'a.csv'));"
    )
    assert _txt(s, "txt").splitlines() == ["Var1", "1", "2", "3"]
    assert not (run.dir / "a.xlsx").exists()
    assert _raises(
        run,
        "writetable(table([4]), fullfile(d,'a.csv'), 'FileType', 'spreadsheet', 'WriteMode', 'inplace')",
    ) == "MATLAB:writetable:InvalidWriteMode"
    assert (run.dir / "a.csv").read_text(encoding="latin-1") == "Var1\n1\n2\n3\n"


@pytest.mark.parametrize("code,ident", [
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 'append')", "MATLAB:writetable:AppendNotSupported"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 'Append', 'WriteVariableNames', true)",
     "MATLAB:writetable:AppendNotSupported"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 'append', 'QuoteStrings', 'nope')",
     "MATLAB:writetable:AppendNotSupported"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 'inplace')", "MATLAB:writetable:InvalidWriteMode"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 'overwritesheet')", "MATLAB:writetable:InvalidWriteMode"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 'replacefile')", "MATLAB:writetable:InvalidWriteMode"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 'nope')", "MATLAB:writetable:InvalidWriteMode"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', true)", "MATLAB:writetable:InvalidWriteMode"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 1)", "MATLAB:writetable:InvalidWriteMode"),
    ("writetable(T, fullfile(d,'a.csv'), 'WriteMode', 'append', 'WriteVariableNames', false, 'QuoteStrings', 'nope')",
     "MATLAB:writetable:InvalidQuoteStrings"),
])
def test_rejected_writemode_leaves_the_file_alone(run, code, ident):
    (run.dir / "a.csv").write_text("keep\n", encoding="latin-1")
    run("T = table({'NY';'CA'});")
    assert _raises(run, code) == ident
    assert (run.dir / "a.csv").read_text(encoding="latin-1") == "keep\n"


def test_append_rejected_before_a_missing_file_is_created(run):
    run("T = table({'NY';'CA'});")
    assert _raises(run, "writetable(T, fullfile(d,'new.csv'), 'WriteMode', 'append')") == \
        "MATLAB:writetable:AppendNotSupported"
    assert not (run.dir / "new.csv").exists()


@pytest.mark.parametrize("ext", [".xlsx", ".xls", ".xlsm", ".xlsb", ".ods"])
@pytest.mark.parametrize("mode", ["'append'", "'inplace'", "'nope'"])
def test_spreadsheet_extension_rejects_writemode_before_bytes(run, ext, mode):
    run("T = table({'NY'});")
    assert _raises(run, f"writetable(T, fullfile(d,'a{ext}'), 'WriteMode', {mode})") == \
        "MATLAB:writetable:UnsupportedFileType"
    assert not (run.dir / f"a{ext}").exists()


def test_writecell_does_not_accept_writemode(run):
    assert _raises(run, "writecell({'a'}, fullfile(d,'c.csv'), 'WriteMode', 'append')") == \
        "MATLAB:textio:textio:UnknownParameter"
    assert not (run.dir / "c.csv").exists()
    assert _raises(run, "writecell({'a'}, fullfile(d,'c.xlsx'), 'WriteMode', 'append')") == \
        "MATLAB:textio:textio:UnknownParameter"
    assert not (run.dir / "c.xlsx").exists()
    s = run("writecell({'a'}, fullfile(d,'c.csv')); writecell({'b'}, fullfile(d,'c.csv')); "
            "txt = fileread(fullfile(d,'c.csv'));")
    assert _txt(s, "txt") == "b\n"

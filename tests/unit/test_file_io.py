"""Epic #533: fprintf / low-level file I/O / save-load (MAT v5) / text tables."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "mat"


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer()).tolist()


def _t(s, n):
    return s.workspace.get(n).text


def test_fprintf_statement_prints_without_ans(capsys):
    s = _run("fprintf('x=%d\\n', 4)")
    assert capsys.readouterr().out == "x=4\n" and "ans" not in s.workspace


def test_fprintf_count_and_matrix_cycling(capsys):
    s = _run("n = fprintf('%d-%d|', [1 2; 3 4]);")
    assert capsys.readouterr().out == "1-3|2-4|" and _v(s, "n") == [[8]]


def test_fprintf_invalid_fid():
    with pytest.raises(EvalError, match="Invalid file identifier"):
        _run("fprintf(99, 'x');")


def test_fopen_modes_and_append(tmp_path):
    f = tmp_path / "a.txt"
    _run(f"fid = fopen('{f}', 'w'); fprintf(fid, 'one\\n'); fclose(fid); fid = fopen('{f}', 'a'); fprintf(fid, 'two\\n'); fclose(fid);")
    assert f.read_text() == "one\ntwo\n"


def test_fopen_failure_message():
    s = _run("[fid, msg] = fopen('/no/such/q.txt');")
    assert _v(s, "fid") == [[-1]] and _t(s, "msg") != ""


def test_fgetl_fgets_eof(tmp_path):
    f = tmp_path / "l.txt"
    f.write_text("a\nbb\n")
    s = _run(f"fid = fopen('{f}'); x = fgetl(fid); y = fgets(fid); e = feof(fid); z = fgetl(fid); fclose(fid);")
    assert _t(s, "x") == "a" and _t(s, "y") == "bb\n" and _v(s, "e") == [[True]] and _v(s, "z") == [[-1]]


def test_fseek_ftell_frewind(tmp_path):
    f = tmp_path / "s.txt"
    f.write_text("abcdef")
    s = _run(f"fid = fopen('{f}'); fseek(fid, 2, 'bof'); p = ftell(fid); c = fread(fid, 2, 'char=>char')'; frewind(fid); q = ftell(fid); fclose(fid);")
    assert _v(s, "p") == [[2]] and _t(s, "c") == "cd" and _v(s, "q") == [[0]]


def test_sscanf_forms():
    s = _run("a = sscanf('10 20 30', '%d', 2)'; b = sscanf('x=3.5', 'x=%f'); [c, n] = sscanf('1 2 3 4', '%d', [2 2]); d = sscanf('abc', '%c');")
    assert _v(s, "a") == [[10, 20]] and _v(s, "b") == [[3.5]] and _v(s, "c") == [[1, 3], [2, 4]]
    assert _v(s, "n") == [[4]] and _t(s, "d") == "abc"


def test_sscanf_stops_at_mismatch_and_inf_nan():
    s = _run("a = sscanf('1 2 x 3', '%f')'; b = sscanf('Inf NaN -2', '%f')';")
    assert _v(s, "a") == [[1, 2]]
    b = _v(s, "b")[0]
    assert np.isinf(b[0]) and np.isnan(b[1]) and b[2] == -2


def test_fwrite_fread_precisions(tmp_path):
    g = tmp_path / "b.bin"
    s = _run(f"fid = fopen('{g}', 'w'); n = fwrite(fid, [1.5 -2], 'double'); fwrite(fid, [300 -5], 'uint8'); fclose(fid); fid = fopen('{g}'); a = fread(fid, 2, 'double')'; b = fread(fid, Inf, '*uint8')'; fclose(fid); cb = class(b);")
    assert _v(s, "n") == [[2]] and _v(s, "a") == [[1.5, -2]] and _v(s, "b") == [[255, 0]] and _t(s, "cb") == "uint8"


def test_fileread_delete_tempname_fileparts_fullfile(tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("hi\nthere")
    s = _run(f"t = fileread('{f}'); delete('{f}'); e = isfile('{f}'); [p, n, x] = fileparts('/a/b/c.tar.gz'); ff = fullfile('a', 'b/', 'c.m'); tn = tempname;")
    assert _t(s, "t") == "hi\nthere" and _v(s, "e") == [[False]]
    assert (_t(s, "p"), _t(s, "n"), _t(s, "x")) == ("/a/b", "c.tar", ".gz") and _t(s, "ff") == "a/b/c.m"
    assert not Path(_t(s, "tn")).exists()


def test_mat_roundtrip_all_classes(tmp_path):
    m = tmp_path / "all.mat"
    s = _run(
        f"A = int16([1 -2; 3 4]); B = logical([1 0]); C = single(2.5); D = [1+2i 3]; E = 'abc'; F = ['ab'; 'cd'];"
        f" G = sparse([1 0 2; 0 3 0]); H = struct('a', {{1, 'x'}}); K = {{1, 'two'; [1 2 3], {{4}}}}; Q = zeros(0, 3);"
        f" save('{m}'); clear; load('{m}');"
        f" ca = class(A); cb = class(B); cc = class(C); sg = issparse(G); g = full(G); h2 = H(2).a; k4 = K{{2,2}}{{1}}; qs = size(Q); f2 = F(2,:);"
    )
    assert _t(s, "ca") == "int16" and _v(s, "A") == [[1, -2], [3, 4]]
    assert _t(s, "cb") == "logical" and _t(s, "cc") == "single" and _v(s, "D") == [[1 + 2j, 3 + 0j]]
    assert _t(s, "E") == "abc" and _t(s, "f2") == "cd" and _v(s, "sg") == [[True]]
    assert _v(s, "g") == [[1, 0, 2], [0, 3, 0]] and _t(s, "h2") == "x" and _v(s, "k4") == [[4]]
    assert _v(s, "qs") == [[0, 3]]


def test_mat_header_and_layout(tmp_path):
    m = tmp_path / "h.mat"
    _run(f"x = 7; save('{m}', 'x');")
    b = m.read_bytes()
    assert b[:10] == b"MATLAB 5.0" and b[126:128] == b"IM" and struct.unpack("<H", b[124:126])[0] == 0x0100
    assert struct.unpack("<I", b[128:132])[0] == 14  # miMATRIX


@pytest.mark.parametrize("name", ["scipy_v5_compressed.mat", "scipy_v5_plain.mat"])
def test_reads_third_party_mat(name):
    s = _run(f"S = load('{FIX / name}'); x = S.X;")
    x = _v(s, "x")
    assert x in ([[0, 1, 2], [3, 4, 5]], [[1, 0], [0, 1]])


def test_compressed_fixture_contents():
    s = _run(f"load('{FIX / 'scipy_v5_compressed.mat'}'); g = s.g; f = s.f; c2 = c{{2}}; ci = class(I); z = Z;")
    assert _t(s, "g") == "txt" and _v(s, "f") == [[1, 2]] and _t(s, "c2") == "a" and _t(s, "ci") == "uint8"
    assert _v(s, "z") == [[1 + 1j]]


def test_save_options(tmp_path):
    m = tmp_path / "o.mat"
    s = _run(f"a = 1; b = 2; save('{m}', 'a'); save('{m}', 'b', '-append'); S = load('{m}'); n = numel(fieldnames(S));"
             f" st.p = 5; st.q = 6; save('{m}', '-struct', 'st', 'q'); T = load('{m}'); tq = T.q; tp = isfield(T, 'p');")
    assert _v(s, "n") == [[2]] and _v(s, "tq") == [[6]] and _v(s, "tp") == [[False]]


def test_save_wildcards_and_default_ext(tmp_path):
    s = _run(f"cd('{tmp_path}'); x1 = 1; x2 = 2; y = 3; save data x*; S = load('data'); n = numel(fieldnames(S)); cd('{Path.cwd()}');")
    assert _v(s, "n") == [[2]] and (tmp_path / "data.mat").exists()


def test_save_missing_variable_errors(tmp_path):
    with pytest.raises(EvalError, match="not found"):
        _run(f"save('{tmp_path / 'z.mat'}', 'nope');")


def test_load_errors_and_ascii(tmp_path):
    with pytest.raises(EvalError, match="Unable to find file"):
        _run("load('/no/such/file_533.mat')")
    t = tmp_path / "nums.txt"
    t.write_text("1 2\n3 4\n")
    s = _run(f"load('{t}'); v = nums;")
    assert _v(s, "v") == [[1, 2], [3, 4]]


def test_save_string_rejected(tmp_path):
    with pytest.raises(EvalError, match="string"):
        _run(f"z = \"s\"; save('{tmp_path / 'q.mat'}', 'z');")


def test_text_tables(tmp_path):
    c = tmp_path / "t.csv"
    s = _run(f"A = [1 2.5; -3 4]; writematrix(A, '{c}'); B = readmatrix('{c}'); csvwrite('{c}', [1 2; 3 4]); C = csvread('{c}'); D = dlmread('{c}', ',', 1, 0);")
    assert _v(s, "B") == [[1, 2.5], [-3, 4]] and _v(s, "C") == [[1, 2], [3, 4]] and _v(s, "D") == [[3, 4]]
    h = tmp_path / "h.csv"
    h.write_text("x,y\n1,\n3,4\n")
    s = _run(f"M = readmatrix('{h}'); n = M(1,2) ~= M(1,2); r = M(2,:);")
    assert _v(s, "n") == [[True]] and _v(s, "r") == [[3, 4]]


def test_textscan(tmp_path):
    f = tmp_path / "ts.txt"
    f.write_text("name,val\nab,1.5\ncd,2\n")
    s = _run(f"fid = fopen('{f}'); C = textscan(fid, '%s %f', 'Delimiter', ',', 'HeaderLines', 1); fclose(fid); v = C{{2}}'; n1 = C{{1}}{{2}};")
    assert _v(s, "v") == [[1.5, 2]] and _t(s, "n1") == "cd"

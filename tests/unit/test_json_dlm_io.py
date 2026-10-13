"""jsonencode/jsondecode and delimited numeric I/O (M3-E5, Epic #629)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return lambda n: s.workspace.get(n)


def _n(v):
    return np.asarray(v.backend_buffer())


def test_jsonencode_types_and_options():
    g = _ws("a = jsonencode(struct('a', {1, 2})); b = jsonencode([NaN 1 Inf]); c = jsonencode([NaN 1], 'ConvertInfAndNaN', false);"
            " d = jsonencode(zeros(2, 2, 2)); e = jsonencode({}); f = jsonencode(''); h = jsonencode([true false]);"
            " k = jsonencode(struct('s', \"hi\", 'c', {{1, 'x'}})); m = jsonencode(0.1); p = jsonencode(sprintf('a\\nb'));"
            " q = jsonencode(struct('x', 1), 'PrettyPrint', true);")
    t = lambda n: g(n).text
    assert t("a") == '[{"a":1},{"a":2}]' and t("b") == "[null,1,null]" and t("c") == "[NaN,1]"
    assert t("d") == "[[[0,0],[0,0]],[[0,0],[0,0]]]" and t("e") == "[]" and t("f") == '""'
    assert t("h") == "[true,false]" and t("k") == '{"s":"hi","c":[1,"x"]}' and t("m") == "0.1"
    assert t("p") == '"a\\nb"' and t("q") == '{\n  "x": 1\n}'


def test_jsondecode_consolidation_and_names():
    g = _ws("v = jsondecode('{\"1a\":[1,null],\"b c\":[true,false],\"m\":[1,\"x\"],\"e\":{},\"if\":2}');"
            " a = v.x1a; b = v.b_c; c = class(v.m); n = numel(fieldnames(v.e)); k = v.xIf;"
            " s = jsondecode('[{\"x\":1},{\"y\":2}]'); cs = class(s); z = jsondecode('null'); w = jsondecode('[[[1,2]],[[3,4]]]');"
            " try, jsondecode('{bad'); err = ''; catch ex, err = ex.identifier; end")
    a = _n(g("a"))
    assert a.shape == (2, 1) and a[0, 0] == 1 and np.isnan(a[1, 0])
    assert _n(g("b")).dtype == bool and g("c").text == "cell" and _n(g("n"))[0, 0] == 0 and _n(g("k"))[0, 0] == 2
    assert g("cs").text == "cell" and _n(g("z")).shape == (0, 0) and _n(g("w")).shape == (2, 1, 2)
    assert g("err").text == "MATLAB:json:SyntaxError"


def test_dlmwrite_offsets_newline_append(tmp_path):
    f = (tmp_path / "d.txt").as_posix()
    g = _ws(f"dlmwrite('{f}', [1 2], ',', 1, 1); a = fileread('{f}'); dlmwrite('{f}', [3 4], 'newline', 'pc');"
            f" b = fileread('{f}'); dlmwrite('{f}', 7, '-append', 'precision', '%.2f'); c = fileread('{f}'); m = dlmread('{f}');")
    assert g("a").text == ",,\n,1,2\n" and g("b").text == "3,4\r\n" and g("c").text == "3,4\r\n7.00\n"
    assert np.allclose(_n(g("m")), [[3, 4], [7, 0]])

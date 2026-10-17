"""Epic #773 (M13 G-E6): own .fig format (savefig/openfig/hgsave/hgload), exportgraphics, print."""

from __future__ import annotations

import json
import zipfile

import numpy as np
import pytest

from openmatlab.graphics.handle_model import GObj
from openmatlab.host.repl import ReplSession

pytestmark = [pytest.mark.unit]


def _session(code):
    s = ReplSession()
    s.run_line(code)
    return s


def _v(s, k):
    return np.asarray(s.session.workspace.get(k).backend_buffer())


def _t(s, k):
    return s.session.workspace.get(k).text


def _model(s):
    from openmatlab.libs import graphics_builtins as gb

    return gb.model(s.session.evaluator if hasattr(s.session, "evaluator") else s.session)


def _tree(o: GObj, ids):
    """Canonical property tree (handles replaced by tree paths)."""
    def val(v):
        if isinstance(v, float) and v != v:
            return "NaN"  # NaN != NaN; compare it as a marker
        if isinstance(v, GObj):
            return ("ref", ids.get(v.id))
        if isinstance(v, dict):
            return {k: val(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [val(x) for x in v]
        if hasattr(v, "backend_buffer"):
            return val(np.asarray(v.backend_buffer()).tolist())
        if hasattr(v, "text"):
            return v.text
        return v
    props = {k: val(v) for k, v in o.props.items() if k not in ("Number", "_rendered", "FileName", "Visible")}
    return {"type": o.type, "props": props, "children": [_tree(c, ids) for c in o.children if c.alive]}


def _ids(f: GObj):
    out, n = {}, [0]

    def walk(o):
        out[o.id] = n[0]
        n[0] += 1
        for k in sorted(o.props):
            v = o.props[k]
            if isinstance(v, GObj) and v.id not in out:
                walk(v)
        for c in o.children:
            walk(c)
    walk(f)
    return out


SCENE = ("f = figure('Visible','off'); subplot(2,1,1); h = plot(1:3, [4 NaN 6], 'r--o', 'LineWidth', 2, 'Tag', 'k', "
         "'DisplayName', 'd'); hold on; bar([1 2], [3 4]); title('T'); xlabel('x_1'); legend('show'); "
         "ax = gca; ax.XTick = [1 2 3]; ax.XAxis.TickLabelFormat = '%.1f'; ax.UserData = [1 2; 3 4]; "
         "subplot(2,1,2); yyaxis left; plot(1:3); yyaxis right; plot([10 20 30]); ylim([0 50]); "
         "text(0.5, 0.5, 'n', 'Units', 'normalized'); colormap(jet(8)); ")


def test_round_trip_has_zero_property_tree_diff(tmp_path):
    p = (tmp_path / "s.fig").as_posix()
    s = _session(SCENE + f"savefig(f, '{p}'); g = openfig('{p}', 'invisible');")
    from openmatlab.libs import graphics_builtins as gb

    w = s.session.workspace
    m = w.get("f")._model
    f, g = m.get(_v(s, "f").item()), m.get(_v(s, "g").item())
    assert f is not g and g.type == "figure" and int(g.id) != int(f.id)
    assert _tree(f, _ids(f)) == _tree(g, _ids(g))
    assert gb is not None


def test_openfig_handles_and_properties(tmp_path):
    p = (tmp_path / "a").as_posix()
    s = _session(f"f = figure('Visible','off'); plot(1:3, 'LineWidth', 2, 'Tag', 'k'); title('T'); savefig(f, '{p}'); "
                 f"close(f); g = openfig('{p}.fig', 'invisible'); l = findobj(g, 'Tag', 'k'); lw = l.LineWidth; "
                 "t = get(get(gca, 'Title'), 'String'); v = g.Visible; fn = g.FileName; c = class(g); "
                 f"g2 = openfig('{p}', 'reuse'); same = isequal(g, g2); n = numel(findobj(groot, 'Type', 'figure'));"
                 f"g3 = openfig('{p}'); n2 = numel(findobj(groot, 'Type', 'figure')); close all")
    assert _v(s, "lw").item() == 2 and _t(s, "t") == "T" and _t(s, "v") == "off"
    assert _t(s, "fn").endswith("a.fig") and _t(s, "c") == "matlab.ui.Figure"
    assert _v(s, "same").item() and _v(s, "n").item() == 1 and _v(s, "n2").item() == 2


def test_file_is_own_documented_zip_format(tmp_path):
    p = tmp_path / "z.fig"
    _session(f"f = figure('Visible','off'); plot(1:3); s = struct('a', 1); set(gca, 'UserData', s); "
             f"savefig(f, '{p.as_posix()}'); close all")
    with zipfile.ZipFile(p) as z:
        head = json.loads(z.read("openmatlab-fig.json"))
        doc = json.loads(z.read("figure.json"))
    assert head == {"format": "openmatlab-fig", "version": 1}
    assert doc["figures"][0]["type"] == "figure" and "axes.UserData" in doc["dropped"]


def test_hgsave_hgload_and_multiple_figures(tmp_path):
    p = (tmp_path / "m.fig").as_posix()
    s = _session(f"a = figure('Visible','off'); plot(1:2); b = figure('Visible','off'); bar(1:3); "
                 f"savefig([a b], '{p}'); close all; h = openfig('{p}'); n = numel(h); "
                 f"t = get(findobj(h(2), 'Type', 'bar'), 'Type'); hgsave(h(1), '{p}'); k = hgload('{p}'); "
                 "kt = k.Type; close all")
    assert _v(s, "n").item() == 2 and _t(s, "t") == "bar" and _t(s, "kt") == "figure"


def test_export_sizes(tmp_path):
    from PIL import Image

    d = tmp_path.as_posix()
    _session(f"f = figure('Visible','off'); plot(1:3); print(f, '{d}/p', '-dpng', '-r48'); "
             f"print('-dpdf', '{d}/q'); exportgraphics(gca, '{d}/e.png', 'Resolution', 96); "
             f"exportgraphics(f, '{d}/e.jpg'); exportgraphics(f, '{d}/e.svg', 'BackgroundColor', 'none'); "
             f"exportgraphics(f, '{d}/e.gif'); exportgraphics(f, '{d}/e.pdf', 'ContentType', 'vector'); close all")
    assert Image.open(f"{d}/p.png").size == (280, 210)  # 560x420 px figure at 48 of 96 ppi
    assert (tmp_path / "q.pdf").read_bytes()[:4] == b"%PDF"
    for n in ("e.png", "e.jpg", "e.svg", "e.gif", "e.pdf"):
        assert (tmp_path / n).stat().st_size > 0


@pytest.mark.parametrize("code,ident", [
    ("openfig('/nonexistent/x.fig')", "MATLAB:openfig:FileNotFound"),
    ("savefig(42, [tempname '.fig'])", "MATLAB:savefig:InvalidHandle"),
    ("f = figure('Visible','off'); savefig(f, '/nonexistent/dir/x.fig')", "MATLAB:savefig:FileNotWritable"),
    ("f = figure('Visible','off'); exportgraphics(f, [tempname '.xyz'])", "MATLAB:exportgraphics:InvalidFileExtension"),
    ("f = figure('Visible','off'); exportgraphics(f, [tempname '.png'], 'Resolution', -1)",
     "MATLAB:exportgraphics:InvalidResolution"),
    ("f = figure('Visible','off'); exportgraphics(f, [tempname '.png'], 'Bogus', 1)", "MATLAB:exportgraphics:InvalidParameter"),
    ("f = figure('Visible','off'); print(f, '-dbmp', tempname)", "MATLAB:print:InvalidDevice"),
    ("f = figure('Visible','off'); print(f)", "MATLAB:print:NoPrinter"),
    ("openfig(tempname, 'sideways')", "MATLAB:openfig:FileNotFound"),
])
def test_errors(code, ident):
    s = _session(f"try, {code}; id = ''; catch e, id = e.identifier; end; close all")
    assert _t(s, "id") == ident


def test_matlab_fig_and_damaged_files_rejected(tmp_path):
    bad = tmp_path / "mat.fig"
    bad.write_bytes(b"MATLAB 5.0 MAT-file, Platform: GLNXA64" + bytes(100))
    dam = tmp_path / "dam.fig"
    with zipfile.ZipFile(dam, "w") as z:
        z.writestr("openmatlab-fig.json", json.dumps({"format": "openmatlab-fig", "version": 1}))
        z.writestr("figure.json", json.dumps({"figures": [{"type": "figure"}]}))
    s = _session(f"try, openfig('{bad.as_posix()}'); a = ''; catch e, a = e.identifier; m = e.message; end; "
                 f"try, openfig('{dam.as_posix()}'); b = ''; catch e, b = e.identifier; end; "
                 "n = numel(findobj(groot, 'Type', 'figure'));")
    assert _t(s, "a") == "MATLAB:openfig:InvalidFile" and "MATLAB .fig files are not supported" in _t(s, "m")
    assert _t(s, "b") == "MATLAB:openfig:InvalidFile" and _v(s, "n").item() == 0


def test_reopened_figure_renders(tmp_path):
    p = (tmp_path / "r.fig").as_posix()
    png = (tmp_path / "r.png").as_posix()
    s = _session(SCENE + f"savefig(f, '{p}'); close all; g = openfig('{p}'); saveas(g, '{png}'); ok = isfile('{png}'); "
                 "subplot(2,1,1); hold off; plot(1:4); n = numel(get(gca, 'Children')); close all")
    assert _v(s, "ok").item() and _v(s, "n").item() == 1

"""G-E4 #771: ColorBar keeps the hidden XLabel/YLabel/XDir/YDir compatibility properties."""
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session


def test_colorbar_label_and_dir_aliases():
    s = Session.create_default()
    ReplSession(s).run_line(
        "imagesc(magic(3)); hc = colorbar; set(get(hc,'Xlabel'),'String','Multitude');"
        " t = get(get(hc,'Label'),'String'); same = isequal(get(hc,'YLabel'), hc.Label);"
        " set(hc,'YDir','reverse'); d = hc.Direction; y = get(hc,'XDir');")
    assert s.workspace.get("t").text == "Multitude"
    assert s.workspace.get("d").text == "reverse"
    assert s.workspace.get("y").text == "reverse"
    assert bool(s.workspace.get("same").backend_buffer()[0][0])


def test_other_objects_still_reject_unknown_names():
    s = Session.create_default()
    ReplSession(s).run_line("p = plot(1:3); try, get(p,'YDirx'); ok = 0; catch, ok = 1; end")
    assert s.workspace.get("ok").backend_buffer()[0][0] == 1


def test_colorbar_title_is_its_own_text():
    s = Session.create_default()
    ReplSession(s).run_line(
        "imagesc(magic(3)); hc = colorbar; title(hc, 'T'); ylabel(hc, 'L');"
        " t = get(get(hc,'Title'),'String'); l = hc.Label.String;")
    assert s.workspace.get("t").text == "T"
    assert s.workspace.get("l").text == "L"

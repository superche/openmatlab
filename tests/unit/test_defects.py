import pytest

from openmatlab.qa.defects import load_defect_index

pytestmark = pytest.mark.unit


def test_defects_index_loads():
    index = load_defect_index()
    assert any(d.id == "D0001" for d in index.defects)


def test_cli_defects(capsys):
    from openmatlab.host.cli import main

    with pytest.raises(SystemExit) as ei:
        main(["defects", "--status", "open"])
    assert ei.value.code == 0
    assert "D0001" in capsys.readouterr().out

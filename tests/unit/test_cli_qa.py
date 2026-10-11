import pytest

from openmatlab.host.cli import main

pytestmark = pytest.mark.unit


def test_version_flag():
    with pytest.raises(SystemExit) as ei:
        main(["--version"])
    assert ei.value.code == 0


def test_eval_one_liner(capsys):
    pytest.importorskip("numpy")
    with pytest.raises(SystemExit) as ei:
        main(["-e", "1 + 2 * 3"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "7" in out


def test_features_subcommand(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["features", "--layer", "qa"])
    assert ei.value.code == 0
    assert "qa.feature_map" in capsys.readouterr().out

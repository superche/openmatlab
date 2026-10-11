import pytest

from openmatlab.host.cli import main

pytestmark = pytest.mark.unit


def test_version_flag():
    with pytest.raises(SystemExit) as ei:
        main(["--version"])
    assert ei.value.code == 0


def test_eval_reserved_exit_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["-e", "1+1"])
    assert ei.value.code == 2
    err = capsys.readouterr().err
    assert "not wired" in err


def test_features_subcommand(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["features", "--layer", "qa"])
    assert ei.value.code == 0
    assert "qa.feature_map" in capsys.readouterr().out

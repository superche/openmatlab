import pytest

from openmatlab.qa.feature_map import load_feature_map

pytestmark = pytest.mark.unit


def test_feature_map_loads_and_unique_ids(feature_map):
    assert feature_map.product == "openmatlab"
    assert feature_map.features
    ids = [f.id for f in feature_map.features]
    assert len(ids) == len(set(ids))
    assert feature_map.validate() == []


def test_filter_by_layer(feature_map):
    runtime = feature_map.filter(layer="runtime")
    assert runtime
    assert all(f.layer == "runtime" for f in runtime)


def test_cli_features(capsys):
    from openmatlab.host.cli import main

    with pytest.raises(SystemExit) as ei:
        main(["--features"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "runtime.value_array_protocol" in out
    assert "counts:" in out

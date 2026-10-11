import pytest

from openmatlab.qa.catalog import load_test_catalog
from openmatlab.qa.feature_map import load_feature_map

pytestmark = pytest.mark.unit


def test_catalog_loads():
    catalog = load_test_catalog()
    assert catalog.use_cases
    assert catalog.test_cases
    known = {f.id for f in load_feature_map().features}
    assert catalog.validate(known_feature_ids=known) == []


def test_cli_cases(capsys):
    from openmatlab.host.cli import main

    with pytest.raises(SystemExit) as ei:
        main(["cases", "--kind", "unit"])
    assert ei.value.code == 0
    assert "tc.arch_session_composition" in capsys.readouterr().out

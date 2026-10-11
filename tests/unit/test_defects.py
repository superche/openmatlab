import pytest

from openmatlab.qa import defects as defects_mod

pytestmark = pytest.mark.unit


def test_defects_help_mentions_github():
    text = defects_mod.format_help()
    assert "GitHub Issues" in text
    assert "gh issue" in text


def test_cli_defects_without_forcing_yaml_index(capsys, monkeypatch):
    from openmatlab.host.cli import main

    monkeypatch.setattr(defects_mod, "gh_available", lambda: False)
    monkeypatch.setattr(
        defects_mod,
        "list_issues",
        lambda **kwargs: 127,
    )
    # Patch where cli imports from
    import openmatlab.qa.defects as d

    monkeypatch.setattr(d, "gh_available", lambda: False)

    def fake_list(**kwargs):
        print(d.format_help())
        return 127

    monkeypatch.setattr(d, "list_issues", fake_list)
    with pytest.raises(SystemExit) as ei:
        main(["defects"])
    assert ei.value.code == 127
    out = capsys.readouterr().out
    assert "GitHub Issues" in out

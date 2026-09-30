import json

import pytest

from schreibwaechter.cli import main
from schreibwaechter.config import Config, ConfigError, config_from_dict, load_config
from schreibwaechter.fixer import fix_text


def test_fix_eszett_de_ch():
    result = fix_text("Die Straße ist groß.", Config(locale="de-CH"))
    assert result.text == "Die Strasse ist gross."
    assert result.eszett == 2


def test_fix_keeps_eszett_de_de():
    assert fix_text("Die Straße.", Config(locale="de-DE")).text == "Die Straße."


def test_fix_does_not_touch_code():
    text = "Straße und `Straße` und\n```\nStraße\n```\n"
    fixed = fix_text(text, Config(locale="de-CH")).text
    assert fixed == "Strasse und `Straße` und\n```\nStraße\n```\n"


def test_fix_quotes_de_ch():
    text = 'Er sagte „ja“ und dann "nein".'
    assert fix_text(text, Config(locale="de-CH")).text == "Er sagte «ja» und dann «nein»."


def test_fix_quotes_de_de():
    text = 'Er sagte «ja» und dann "nein".'
    assert fix_text(text, Config(locale="de-DE")).text == "Er sagte „ja“ und dann „nein“."


def test_fix_leaves_consistent_reversed_guillemets_in_de_de():
    text = "Er sagte »ja« und »nein«."
    assert fix_text(text, Config(locale="de-DE")).text == text


def test_fix_skips_unbalanced_quotes():
    result = fix_text('Er sagte „ja und dann "nein".', Config(locale="de-CH"))
    assert result.quotes == 0
    assert result.notes


def test_fix_never_touches_dashes():
    text = "Gut — sehr gut."
    assert fix_text(text, Config(locale="de-CH")).text == text


def test_fix_respects_disable_comment():
    text = "<!-- schreibwaechter: disable-next-line eszett -->\nStraße\nStraße\n"
    fixed = fix_text(text, Config(locale="de-CH")).text
    assert fixed.endswith("Straße\nStrasse\n")


def test_config_file(tmp_path):
    path = tmp_path / ".schreibwaechter.toml"
    path.write_text(
        'locale = "de-CH"\ndisable = ["emoji"]\nstrict = true\n[severity]\nfloskel = "error"\n',
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.locale == "de-CH"
    assert not config.rule_active("emoji")
    assert config.severity_of("floskel") == "error"
    assert config.strict


def test_config_rejects_unknown_rule():
    with pytest.raises(ConfigError):
        config_from_dict({"disable": ["gibtsnicht"]})


def test_config_rejects_bad_locale():
    with pytest.raises(ConfigError):
        config_from_dict({"locale": "de-AT"})


def test_enable_only():
    config = config_from_dict({"enable": ["dash"]})
    assert config.rule_active("dash")
    assert not config.rule_active("floskel")


def test_cli_check_exit_codes(tmp_path, capsys):
    bad = tmp_path / "bad.md"
    bad.write_text("Gut — sehr gut.\n", encoding="utf-8")
    good = tmp_path / "good.md"
    good.write_text("Gut, sehr gut.\n", encoding="utf-8")
    assert main(["check", str(good), "--no-config"]) == 0
    assert main(["check", str(bad), "--no-config"]) == 1
    out = capsys.readouterr().out
    assert "[dash]" in out


def test_cli_warnings_only_exit_zero_unless_strict(tmp_path):
    path = tmp_path / "w.md"
    path.write_text("Das läuft nahtlos.\n", encoding="utf-8")
    assert main(["check", str(path), "--no-config"]) == 0
    assert main(["check", str(path), "--no-config", "--strict"]) == 1


def test_cli_json(tmp_path, capsys):
    path = tmp_path / "a.md"
    path.write_text("Die Straße — nahtlos.\n", encoding="utf-8")
    code = main(["check", str(path), "--no-config", "--locale", "de-CH", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 1
    assert data["locale"] == "de-CH"
    assert {f["rule"] for f in data["findings"]} == {"eszett", "dash", "floskel"}
    assert set(data["findings"][0]["message"]) == {"de", "en"}


def test_cli_stdin(monkeypatch, capsys):
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO("Gut — so.".encode())))
    assert main(["check", "-", "--no-config"]) == 1
    assert "<stdin>:1:5" in capsys.readouterr().out


def test_cli_disable_flag(tmp_path):
    path = tmp_path / "a.md"
    path.write_text("Gut — so.\n", encoding="utf-8")
    assert main(["check", str(path), "--no-config", "--disable", "dash"]) == 0


def test_cli_fix_writes_file(tmp_path):
    path = tmp_path / "a.md"
    path.write_bytes("Die Straße.\r\nZeile zwei.\r\n".encode("utf-8"))
    assert main(["fix", str(path), "--no-config", "--locale", "de-CH"]) == 0
    assert path.read_bytes() == "Die Strasse.\r\nZeile zwei.\r\n".encode("utf-8")


def test_cli_fix_diff_does_not_write(tmp_path, capsys):
    path = tmp_path / "a.md"
    path.write_text("Die Straße.\n", encoding="utf-8")
    main(["fix", str(path), "--no-config", "--locale", "de-CH", "--diff"])
    assert "+Die Strasse." in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == "Die Straße.\n"


def test_cli_config_discovery(tmp_path, monkeypatch):
    (tmp_path / ".schreibwaechter.toml").write_text('locale = "de-CH"\n', encoding="utf-8")
    path = tmp_path / "a.md"
    path.write_text("Die Straße.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SCHREIBWAECHTER_CONFIG", raising=False)
    assert main(["check", "a.md"]) == 1


def test_cli_only_german_skips_english(tmp_path):
    path = tmp_path / "en.md"
    path.write_text("This is the text — with a dash, and it is English.\n", encoding="utf-8")
    assert main(["check", str(path), "--no-config", "--only-german"]) == 0


def test_cli_rules_lists_all(capsys):
    main(["rules"])
    out = capsys.readouterr().out
    for rule in ("dash", "eszett", "quotes", "quotes-mixed", "floskel",
                 "negative-parallelism", "emoji", "anglicism"):
        assert rule in out

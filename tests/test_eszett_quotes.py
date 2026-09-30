from conftest import rules_of


def test_eszett_error_in_de_ch(lint):
    found = [f for f in lint("Die Straße ist groß.", "de-CH") if f.rule == "eszett"]
    assert [f.suggestion for f in found] == ["Strasse", "gross"]
    assert all(f.severity == "error" for f in found)


def test_eszett_allowed_in_de_de(lint):
    assert rules_of(lint("Die Straße ist groß.", "de-DE"), "eszett") == []


def test_eszett_in_code_ignored(lint):
    assert rules_of(lint("Variable `maß` bleibt.", "de-CH"), "eszett") == []


def test_capital_eszett(lint):
    found = [f for f in lint("STRAẞE", "de-CH") if f.rule == "eszett"]
    assert found[0].suggestion == "STRASSE"


def test_swiss_quotes_pass_in_de_ch(lint):
    findings = lint("Sie sagte «ja» und ging.", "de-CH")
    assert rules_of(findings, "quotes") == []
    assert rules_of(findings, "quotes-mixed") == []


def test_german_quotes_warn_in_de_ch(lint):
    found = [f for f in lint("Sie sagte „ja“ und ging.", "de-CH") if f.rule == "quotes"]
    assert len(found) == 1
    assert found[0].severity == "warning"
    assert found[0].suggestion == "«ja»"


def test_straight_quotes_warn(lint):
    found = [f for f in lint('Sie sagte "ja" und ging.', "de-CH") if f.rule == "quotes"]
    assert len(found) == 1


def test_german_quotes_pass_in_de_de(lint):
    findings = lint("Sie sagte „ja“ und ging.", "de-DE")
    assert rules_of(findings, "quotes") == []


def test_swiss_quotes_warn_in_de_de(lint):
    found = [f for f in lint("Sie sagte «ja» und ging.", "de-DE") if f.rule == "quotes"]
    assert found and found[0].suggestion == "„ja“"


def test_mixed_quotes_is_error(lint):
    findings = lint('Sie sagte «ja», er sagte "nein".', "de-CH")
    mixed = [f for f in findings if f.rule == "quotes-mixed"]
    assert len(mixed) == 1
    assert mixed[0].severity == "error"


def test_mixed_quotes_in_de_de(lint):
    findings = lint("Sie sagte „ja“, er sagte “nein”.", "de-DE")
    assert rules_of(findings, "quotes-mixed") == ["quotes-mixed"]


def test_quotes_in_code_ignored(lint):
    text = 'Setze `name = "wert"` und dann:\n\n```json\n{"a": "b"}\n```\n'
    findings = lint(text, "de-CH")
    assert rules_of(findings, "quotes") == []
    assert rules_of(findings, "quotes-mixed") == []

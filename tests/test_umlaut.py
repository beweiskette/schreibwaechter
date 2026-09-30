import pytest

from conftest import rules_of
from schreibwaechter.config import Config
from schreibwaechter.fixer import fix_text
from schreibwaechter.rules import restore_umlauts


@pytest.mark.parametrize("word, fixed", [
    ("fuer", "für"),
    ("Fuer", "Für"),
    ("ueber", "über"),
    ("Aenderung", "Änderung"),
    ("koennen", "können"),
    ("groesser", "grösser"),
    ("natuerlich", "natürlich"),
    ("zurueck", "zurück"),
    ("Oeffnungszeiten", "Öffnungszeiten"),
    ("gegenueber", "gegenüber"),
    ("Zuerich", "Zürich"),
    ("aeusserst", "äusserst"),
    ("FUER", "FÜR"),
])
def test_restore(word, fixed):
    assert restore_umlauts(word) == fixed


@pytest.mark.parametrize("word", [
    "aktuell", "eventuell", "zuerst", "Feuer", "Steuer", "Abenteuer", "neue",
    "Mauer", "Frauen", "Israel", "Michael", "Poet", "Queue", "Kongruenz",
    "Duell", "virtuell", "true", "value", "issue", "does", "Aero", "für", "über",
])
def test_legitimate_words_untouched(word):
    assert restore_umlauts(word) is None


def test_rule_flags_as_error_in_both_locales(lint):
    for locale in ("de-CH", "de-DE"):
        found = [f for f in lint("Das ist fuer dich und koennte gehen.", locale)
                 if f.rule == "umlaut"]
        assert [f.suggestion for f in found] == ["für", "könnte"]
        assert all(f.severity == "error" for f in found)


def test_rule_ignores_code_and_urls(lint):
    text = "Siehe `fuer_alle` und https://example.org/ueber-uns sowie ueber-uns.md."
    assert rules_of(lint(text, "de-CH"), "umlaut") == []


def test_fix_restores_umlauts_and_keeps_rest():
    text = "Wir koennen das spaeter pruefen. Der Code `fuer` bleibt.\n"
    result = fix_text(text, Config(locale="de-CH"))
    assert result.text == "Wir können das später prüfen. Der Code `fuer` bleibt.\n"
    assert result.umlaut == 3


def test_fix_respects_disable_directive():
    text = "<!-- schreibwaechter: disable umlaut -->\nfuer immer\n"
    result = fix_text(text, Config(locale="de-CH"))
    assert result.text == text

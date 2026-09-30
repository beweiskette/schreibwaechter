import pytest

from conftest import rules_of
from schreibwaechter.config import Config, config_from_dict
from schreibwaechter.linter import lint_text


@pytest.mark.parametrize(
    "text",
    [
        "Es ist wichtig zu beachten, dass Tests laufen.",
        "Gute Namen spielen eine entscheidende Rolle.",
        "In der heutigen schnelllebigen Welt ändert sich alles.",
        "Das war ein Meilenstein für uns.",
        "Die Integration läuft nahtlos.",
        "Wir verfolgen einen ganzheitlichen Ansatz.",
        "Tauchen wir ein in die Details.",
        "Zusammenfassend lässt sich sagen, dass es geht.",
        "## Fazit\n\nEs geht.",
        "**Fazit:** Es geht.",
        "Es gibt Herausforderungen und Chancen.",
        "Ich hoffe, das hilft!",
        "Darüber hinaus gibt es Tests.",
        "Das ist gemäß Plan ein Meilenstein.",
    ],
)
def test_floskeln_found(lint, text):
    assert "floskel" in rules_of(lint(text, "de-DE")), text


@pytest.mark.parametrize(
    "text",
    [
        "Der Test prüft die Eingabe.",
        "Das Fazitbuch liegt auf dem Tisch.",
        "Die Naht ist los.",
        "Er spielt eine Rolle im Theater.",
    ],
)
def test_floskeln_not_found(lint, text):
    assert rules_of(lint(text, "de-DE"), "floskel") == [], text


def test_floskel_matches_eszett_variant(lint):
    # Pattern is written with ss, text uses ß.
    assert rules_of(lint("Abschließend lässt sich sagen, es läuft.", "de-DE"), "floskel")


def test_floskel_is_warning(lint):
    found = [f for f in lint("Das ist nahtlos.", "de-DE") if f.rule == "floskel"]
    assert found[0].severity == "warning"
    assert found[0].entry == "nahtlos"


def test_floskel_in_code_ignored(lint):
    assert rules_of(lint("Die Funktion `nahtlos()` heisst so.", "de-CH"), "floskel") == []


def test_extra_phrases_and_ignore_from_config():
    config = config_from_dict(
        {"locale": "de-CH", "words": {"floskeln": ["Synergieeffekte heben"],
                                      "ignore": ["nahtlos"]}}
    )
    findings = lint_text("Wir wollen Synergieeffekte  heben, nahtlos.", config)
    entries = [f.entry for f in findings if f.rule == "floskel"]
    assert "synergieeffekte-heben" in entries
    assert "nahtlos" not in entries


def test_extra_phrase_file(tmp_path):
    (tmp_path / "liste.json").write_text(
        '{"entries": [{"id": "eigen", "pattern": "Hebel\\\\w*", "hint_de": "x"}]}',
        encoding="utf-8",
    )
    (tmp_path / ".schreibwaechter.toml").write_text(
        '[words]\nfloskeln_files = ["liste.json"]\n', encoding="utf-8"
    )
    from schreibwaechter.config import load_config

    config = load_config(tmp_path / ".schreibwaechter.toml")
    findings = lint_text("Das ist ein Hebelpunkt.", config)
    assert [f.entry for f in findings if f.rule == "floskel"] == ["eigen"]


@pytest.mark.parametrize(
    "text",
    [
        "Das macht keinen Sinn.",
        "Sinn machen solche Tests nicht.",
        "In 2026 kommt die neue Version.",
        "Am Ende des Tages zählt das Ergebnis.",
        "Das kann einen grossen Unterschied machen.",
        "Das ist nicht wirklich schnell.",
        "Basierend auf den Daten gilt das.",
    ],
)
def test_anglicisms_found(lint, text):
    assert "anglicism" in rules_of(lint(text, "de-CH")), text


@pytest.mark.parametrize(
    "text",
    [
        "Das ergibt Sinn.",
        "Im Jahr 2026 kommt die neue Version.",
        "Wir machen einen Unterschied zwischen A und B.",
        "Das Ende des Liedes ist leise.",
    ],
)
def test_anglicisms_not_found(lint, text):
    assert rules_of(lint(text, "de-CH"), "anglicism") == [], text


@pytest.mark.parametrize(
    "text",
    [
        "Das Tool ist nicht nur schnell, sondern auch sicher.",
        "Es geht nicht um Tempo, sondern um Qualität.",
        "Es geht nicht nur um Tempo, sondern um Qualität.",
        "Das ist kein Fehler, sondern ein Merkmal.",
    ],
)
def test_negative_parallelism_found(lint, text):
    found = [f for f in lint(text, "de-CH") if f.rule == "negative-parallelism"]
    assert len(found) == 1, text
    assert found[0].severity == "warning"


@pytest.mark.parametrize(
    "text",
    [
        "Das Tool ist schnell und sicher.",
        "Nicht nur heute. Sondern auch morgen.",
        "Es gibt keinen Fehler. Sondern?",
    ],
)
def test_negative_parallelism_not_found(lint, text):
    assert rules_of(lint(text, "de-CH"), "negative-parallelism") == [], text


def test_default_config_is_de_de():
    assert Config().locale == "de-DE"

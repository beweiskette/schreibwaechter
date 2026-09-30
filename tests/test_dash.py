import pytest

from conftest import rules_of


def dashes(lint, text, locale="de-CH"):
    return [f for f in lint(text, locale) if f.rule == "dash"]


@pytest.mark.parametrize(
    "text",
    [
        "Das Ergebnis — ehrlich gesagt — war gut.",
        "Das Ergebnis—war gut.",
        "Das Ergebnis – ehrlich gesagt – war gut.",
        "Das Ergebnis - ehrlich gesagt - war gut.",
        "Das Ergebnis -- war gut.",
        "# Titel - Untertitel",
        "`code` - danach Text",
        "Satzende –\nneue Zeile",
    ],
)
def test_dash_as_punctuation_is_error(lint, text):
    found = dashes(lint, text)
    assert found, text
    assert all(f.severity == "error" for f in found)


@pytest.mark.parametrize(
    "text",
    [
        "Die Jahre 2020–2024 waren ruhig.",
        "Wir brauchen 8–10 Tage.",
        "Die Strecke Bern–Genf ist lang.",
        "Schick mir eine E-Mail.",
        "Ein- und Ausgang sind getrennt.",
        "- erster Punkt\n- zweiter Punkt",
        "  - eingerückter Punkt",
        "> - Zitat mit Liste",
        "| a | b |\n|---|---|\n| – | — |",
        "Das kostet Fr. 20.– pro Stück.",
        "Rechnung: 5 - 3 ergibt 2.",
        "---",
        "Text\n\n---\n\nMehr Text",
        "Das Zeichen (—) heisst Geviertstrich, «–» Halbgeviertstrich.",
    ],
)
def test_allowed_dashes(lint, text):
    assert dashes(lint, text) == [], text


def test_dash_in_code_block_ignored(lint):
    text = "Normaler Satz.\n\n```\nwert = a — b – c - d\n```\n\nEnde."
    assert dashes(lint, text) == []


def test_dash_in_inline_code_ignored(lint):
    assert dashes(lint, "Nutze `a - b` hier.") == []


def test_url_with_dashes_ignored(lint):
    text = "Siehe https://example.org/mein-langer-pfad-mit-strichen und fertig."
    assert dashes(lint, text) == []


def test_path_with_dashes_ignored(lint):
    assert dashes(lint, "Die Datei liegt in /opt/mein-tool/config-datei.") == []
    assert dashes(lint, "Siehe docs/mein-leitfaden.md für mehr.") == []


def test_front_matter_ignored(lint):
    text = "---\ntitel: A - B\n---\n\nEin Satz."
    assert dashes(lint, text) == []


def test_range_with_spaces_gets_suggestion(lint):
    found = dashes(lint, "Die Jahre 2020 – 2024 waren ruhig.")
    assert len(found) == 1
    assert found[0].suggestion == "2020–2024"


def test_en_dash_list_marker(lint):
    found = dashes(lint, "– erster Punkt")
    assert found and found[0].suggestion == "-"


def test_dash_rule_also_in_de_de(lint):
    assert rules_of(lint("Gut — sehr gut.", "de-DE"), "dash")


def test_position_is_reported(lint):
    found = dashes(lint, "Zeile eins.\nZeile — zwei.")
    assert (found[0].line, found[0].column) == (2, 7)

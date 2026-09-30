from conftest import rules_of
from schreibwaechter.prose import MASK, mask_text


def test_emoji_in_prose(lint):
    found = [f for f in lint("Das klappt gut 🎉 wirklich.", "de-CH") if f.rule == "emoji"]
    assert len(found) == 1
    assert found[0].severity == "warning"
    assert "Fliesstext" in found[0].message_de


def test_emoji_before_heading_and_list_item(lint):
    text = "## ✅ Erledigt\n\n- 🚀 Start\n1. 🔥 Heiss"
    found = [f for f in lint(text, "de-CH") if f.rule == "emoji"]
    assert len(found) == 3
    assert all("Überschrift oder Listenpunkt" in f.message_de for f in found)


def test_emoji_with_modifiers_is_one_finding(lint):
    found = [f for f in lint("Gut 👍🏽 so.", "de-CH") if f.rule == "emoji"]
    assert len(found) == 1


def test_no_emoji_for_arrows(lint):
    assert rules_of(lint("A → B ist klar.", "de-CH"), "emoji") == []


def test_mask_keeps_length_and_newlines():
    text = "a `b` c\n```\nx\n```\nhttps://example.org/x-y z"
    masked = mask_text(text)
    assert len(masked) == len(text)
    assert masked.count("\n") == text.count("\n")
    assert "x-y" not in masked
    assert masked.startswith("a " + MASK * 3 + " c")


def test_mask_unclosed_fence_masks_to_end():
    masked = mask_text("Satz.\n```\ncode — hier")
    assert "—" not in masked


def test_mask_html_comment_and_windows_path():
    masked = mask_text("Pfad C:\\Programme\\mein-tool\\a.exe <!-- a - b -->")
    assert "mein-tool" not in masked
    assert "a - b" not in masked


def test_mask_email_and_link_target():
    masked = mask_text("Schreib an info-team@example.org oder [hier](./mein-ordner/x-y.md).")
    assert "info-team" not in masked
    assert "mein-ordner" not in masked
    assert "[hier]" in masked


def test_disable_block(lint):
    text = (
        "<!-- schreibwaechter: disable dash -->\n"
        "Das — geht.\n"
        "<!-- schreibwaechter: enable dash -->\n"
        "Das — nicht.\n"
    )
    found = [f for f in lint(text, "de-CH") if f.rule == "dash"]
    assert [f.line for f in found] == [4]


def test_disable_all(lint):
    text = "<!-- schreibwaechter: disable -->\nDie Straße — nahtlos.\n"
    assert lint(text, "de-CH") == []


def test_disable_next_line(lint):
    text = "<!-- schreibwaechter: disable-next-line eszett -->\nStraße\nStraße\n"
    found = [f for f in lint(text, "de-CH") if f.rule == "eszett"]
    assert [f.line for f in found] == [3]


def test_disable_line(lint):
    text = "Straße <!-- schreibwaechter: disable-line eszett -->\nStraße\n"
    found = [f for f in lint(text, "de-CH") if f.rule == "eszett"]
    assert [f.line for f in found] == [2]


def test_disable_does_not_touch_other_rules(lint):
    text = "<!-- schreibwaechter: disable eszett -->\nStraße — da.\n"
    assert rules_of(lint(text, "de-CH")) == ["dash"]

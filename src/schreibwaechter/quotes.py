"""Find double quotation marks in prose, pair them and classify their style."""

from __future__ import annotations

from dataclasses import dataclass

from .prose import MASK

# Style families.
SWISS = "guillemets"            # «so»
GERMAN = "german"               # „so“
GERMAN_REVERSED = "reversed"    # »so«
ENGLISH = "english"             # “so”
STRAIGHT = "straight"           # "so"

EXPECTED = {
    "de-CH": {SWISS},
    "de-DE": {GERMAN, GERMAN_REVERSED},
}
TARGET = {
    "de-CH": ("«", "»"),
    "de-DE": ("„", "“"),
}
STYLE_EXAMPLE = {
    SWISS: "«…»",
    GERMAN: "„…“",
    GERMAN_REVERSED: "»…«",
    ENGLISH: "“…”",
    STRAIGHT: '"…"',
}

QUOTE_CHARS = set('„“”«»"')
_OPEN_CONTEXT = set(" \t\n\r([{/–—-" + MASK)


@dataclass
class Quote:
    offset: int
    char: str
    role: str = ""        # "open" or "close"
    family: str = ""
    partner: int | None = None   # index of the matching quote in the list


def scan(masked: str) -> list[Quote]:
    quotes: list[Quote] = []
    stack: list[int] = []

    def open_quote(q: Quote, family: str) -> None:
        q.role, q.family = "open", family
        stack.append(len(quotes))

    def close_quote(q: Quote, family: str | None = None) -> None:
        opener_index = stack.pop()
        opener = quotes[opener_index]
        q.role = "close"
        q.family = family or opener.family
        opener.family = q.family
        q.partner = opener_index
        opener.partner = len(quotes)

    for offset, char in enumerate(masked):
        if char not in QUOTE_CHARS:
            continue
        q = Quote(offset, char)
        top = quotes[stack[-1]].char if stack else None
        if char == "„":
            open_quote(q, GERMAN)
        elif char == "“":
            if top == "„":
                close_quote(q, GERMAN)
            else:
                open_quote(q, ENGLISH)
        elif char == "”":
            if top in ("“", "„"):
                close_quote(q, ENGLISH if top == "“" else GERMAN)
            else:
                q.role, q.family = "close", ENGLISH
        elif char == "«":
            if top == "»":
                close_quote(q, GERMAN_REVERSED)
            else:
                open_quote(q, SWISS)
        elif char == "»":
            if top == "«":
                close_quote(q, SWISS)
            else:
                open_quote(q, GERMAN_REVERSED)
        else:  # straight quote
            if top == '"':
                close_quote(q, STRAIGHT)
            else:
                before = masked[offset - 1] if offset > 0 else " "
                after = masked[offset + 1] if offset + 1 < len(masked) else " "
                if before in _OPEN_CONTEXT and not after.isspace():
                    open_quote(q, STRAIGHT)
                else:
                    q.role, q.family = "close", STRAIGHT
        quotes.append(q)
    return quotes


def balanced(quotes: list[Quote]) -> bool:
    return all(q.partner is not None for q in quotes)

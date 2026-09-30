"""The individual rules. Each rule yields ``Hit`` objects on the masked text."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import lru_cache

from . import quotes as q
from .config import Config
from .prose import LineIndex, normalize_eszett
from .wordlists import Entry, load_bundled


@dataclass
class Hit:
    rule: str
    offset: int
    length: int
    message_de: str
    message_en: str
    suggestion: str | None = None
    severity: str | None = None
    entry: str | None = None


@dataclass
class Context:
    text: str
    masked: str
    index: LineIndex
    config: Config
    _normalized: tuple[str, list[int]] | None = None

    @property
    def normalized(self) -> tuple[str, list[int]]:
        if self._normalized is None:
            self._normalized = normalize_eszett(self.masked)
        return self._normalized


def _line_prefix(masked: str, offset: int) -> str:
    start = masked.rfind("\n", 0, offset) + 1
    return masked[start:offset]


def _prev_nonspace(masked: str, offset: int) -> str:
    i = offset - 1
    while i >= 0 and masked[i] in " \t":
        i -= 1
    return masked[i] if i >= 0 and masked[i] not in "\r\n" else ""


def _next_nonspace(masked: str, offset: int) -> str:
    i = offset
    while i < len(masked) and masked[i] in " \t":
        i += 1
    return masked[i] if i < len(masked) and masked[i] not in "\r\n" else ""


def _is_list_or_quote_prefix(prefix: str) -> bool:
    return re.fullmatch(r"[\s>]*", prefix) is not None


# --- 1. dashes -------------------------------------------------------------

_DASH_MSG_DE = (
    "Gedankenstrich als Satzzeichen «{d}». Satz umbauen: Komma, Doppelpunkt, "
    "Klammer oder Punkt."
)
_DASH_MSG_EN = (
    "Dash used as punctuation («{d}»). Rewrite the sentence with a comma, colon, "
    "parentheses or a full stop."
)


def rule_dash(ctx: Context) -> Iterator[Hit]:
    masked = ctx.masked
    for match in re.finditer("[—―–]", masked):
        i = match.start()
        dash = match.group(0)
        before = masked[max(0, i - 2):i]
        prev_char = masked[i - 1] if i > 0 else "\n"
        next_char = masked[i + 1] if i + 1 < len(masked) else "\n"
        if re.fullmatch(r"\d\.", before):
            continue  # Swiss price notation such as "Fr. 20.–"
        if prev_char in "(«»\"„“‹›'[" and next_char in ")»«\"“”›‹']":
            continue  # the character itself is being mentioned: (—) or «–»
        prev_ns, next_ns = _prev_nonspace(masked, i), _next_nonspace(masked, i + 1)
        if prev_ns in ("|", "") and next_ns in ("|", "") and "|" in (prev_ns + next_ns):
            continue  # placeholder in an empty table cell
        if dash == "–" and not prev_char.isspace() and not next_char.isspace():
            continue  # range or connection without spaces: 2020–2024, Bern–Genf
        if dash == "–" and prev_ns.isdigit() and next_ns.isdigit():
            j = i + 1
            while j < len(masked) and masked[j] in " \t":
                j += 1
            k = i
            while k > 0 and masked[k - 1] in " \t":
                k -= 1
            left = re.search(r"\d+$", masked[:k])
            right = re.match(r"\d+", masked[j:])
            suggestion = f"{left.group(0)}–{right.group(0)}" if left and right else None
            yield Hit(
                "dash", i, 1,
                "Bis-Strich mit Leerzeichen. Zahlenbereiche ohne Leerzeichen schreiben.",
                "En dash with spaces in a range. Write ranges without spaces.",
                suggestion,
            )
            continue
        if _is_list_or_quote_prefix(_line_prefix(masked, i)):
            yield Hit(
                "dash", i, 1,
                f"Gedankenstrich «{dash}» als Aufzählungszeichen. «-» verwenden.",
                f"Dash «{dash}» used as a list marker. Use «-».",
                "-",
            )
            continue
        yield Hit("dash", i, 1, _DASH_MSG_DE.format(d=dash), _DASH_MSG_EN.format(d=dash))

    for match in re.finditer(r"(?<=\S)[ \t]+(-{1,3})(?=[ \t]+\S)", masked):
        start = match.start(1)
        prev_ns = _prev_nonspace(masked, match.start())
        next_ns = _next_nonspace(masked, match.end(1))
        if prev_ns in "|-+" or next_ns in "|-+":
            continue  # tables, horizontal rules, diff markers
        if prev_ns.isdigit() and next_ns.isdigit():
            continue  # arithmetic
        if _is_list_or_quote_prefix(_line_prefix(masked, start)):
            continue  # Markdown list item
        dash = match.group(1)
        yield Hit("dash", start, len(dash), _DASH_MSG_DE.format(d=f" {dash} "),
                  _DASH_MSG_EN.format(d=f" {dash} "))


# --- 2. Eszett (de-CH) -----------------------------------------------------

def rule_eszett(ctx: Context) -> Iterator[Hit]:
    masked = ctx.masked
    seen: set[int] = set()
    for match in re.finditer("[ßẞ]", masked):
        start = match.start()
        while start > 0 and (masked[start - 1].isalnum() or masked[start - 1] in "ßẞ"):
            start -= 1
        if start in seen:
            continue
        seen.add(start)
        end = match.end()
        while end < len(masked) and (masked[end].isalnum() or masked[end] in "ßẞ"):
            end += 1
        word = masked[start:end]
        fixed = word.replace("ß", "ss").replace("ẞ", "SS")
        yield Hit(
            "eszett", start, end - start,
            f"Eszett in Schweizer Text: «{word}» wird «{fixed}» geschrieben.",
            f"Eszett in Swiss German: write «{fixed}» instead of «{word}».",
            fixed,
        )


# --- 3. quotation marks ----------------------------------------------------

def _quoted_suggestion(ctx: Context, quote: q.Quote, quotes: list[q.Quote]) -> str | None:
    if quote.partner is None:
        return None
    closing = quotes[quote.partner]
    inner = ctx.text[quote.offset + 1:closing.offset]
    if len(inner) > 60 or "\n" in inner:
        return None
    left, right = q.TARGET[ctx.config.locale]
    return f"{left}{inner}{right}"


def rule_quotes(ctx: Context) -> Iterator[Hit]:
    quotes = q.scan(ctx.masked)
    expected = q.EXPECTED[ctx.config.locale]
    left, right = q.TARGET[ctx.config.locale]
    for quote in quotes:
        if quote.family in expected:
            continue
        if quote.role == "close" and quote.partner is not None:
            continue  # reported with its opening mark
        style = q.STYLE_EXAMPLE[quote.family]
        yield Hit(
            "quotes", quote.offset, 1,
            f"Anführungszeichen {style} statt {left}…{right} ({ctx.config.locale}).",
            f"Quotation marks {style} instead of {left}…{right} ({ctx.config.locale}).",
            _quoted_suggestion(ctx, quote, quotes),
        )


def rule_quotes_mixed(ctx: Context) -> Iterator[Hit]:
    quotes = q.scan(ctx.masked)
    if not quotes:
        return
    families: list[str] = []
    for quote in quotes:
        if quote.family not in families:
            families.append(quote.family)
    if len(families) < 2:
        return
    second = next(x for x in quotes if x.family != quotes[0].family)
    styles = ", ".join(q.STYLE_EXAMPLE[f] for f in families)
    left, right = q.TARGET[ctx.config.locale]
    yield Hit(
        "quotes-mixed", second.offset, 1,
        f"Verschiedene Anführungszeichen im selben Text ({styles}). Einheitlich "
        f"{left}…{right} verwenden.",
        f"Mixed quotation mark styles in one text ({styles}). Use {left}…{right} "
        f"throughout.",
    )


# --- 4. and 8. phrase lists ------------------------------------------------

@lru_cache(maxsize=None)
def bundled_entries(name: str) -> tuple[Entry, ...]:
    return tuple(load_bundled(name))


def _list_hits(ctx: Context, rule: str, entries: list[Entry] | tuple[Entry, ...],
               label_de: str, label_en: str) -> Iterator[Hit]:
    normalized, mapping = ctx.normalized
    ignore = ctx.config.ignore
    for entry in entries:
        if entry.id.lower() in ignore:
            continue
        for match in entry.regex.finditer(normalized):
            if not match.group(0).strip():
                continue
            start = mapping[match.start()]
            end = mapping[match.end() - 1] + 1
            original = ctx.text[start:end]
            if original.lower() in ignore or match.group(0).lower() in ignore:
                continue
            shown = " ".join(original.split())
            hint_de = f" {entry.hint_de}" if entry.hint_de else ""
            hint_en = f" {entry.hint_en}" if entry.hint_en else ""
            yield Hit(
                rule, start, end - start,
                f"{label_de} «{shown}».{hint_de}",
                f"{label_en} «{shown}».{hint_en}",
                severity=entry.severity,
                entry=entry.id,
            )


def rule_floskel(ctx: Context) -> Iterator[Hit]:
    entries = list(bundled_entries("floskeln.json")) + ctx.config.extra_floskeln
    yield from _list_hits(ctx, "floskel", entries, "Floskel", "Stock phrase")


def rule_anglicism(ctx: Context) -> Iterator[Hit]:
    entries = list(bundled_entries("anglizismen.json")) + ctx.config.extra_anglicisms
    yield from _list_hits(ctx, "anglicism", entries, "Anglizismus", "Anglicism")


# --- 5. negative parallelism -----------------------------------------------

_CLAUSE = r"[^.!?;:\n\x00]"
_PARALLEL = [
    re.compile(r"\bnicht\s+(?:nur|bloss|bloß|allein|einfach)\b" + _CLAUSE +
               r"{1,200}?\bsondern(?:\s+auch|\s+vor\s+allem|\s+vielmehr)?\b", re.I),
    re.compile(r"\bes\s+geht\s+(?:hier\s+|dabei\s+)?nicht\s+(?:nur\s+|bloss\s+|bloß\s+|"
               r"allein\s+|einfach\s+)?(?:um|darum)\b" + _CLAUSE + r"{1,200}?\bsondern\b",
               re.I),
    re.compile(r"\bkein(?:e|en|em|er|es)?\b" + _CLAUSE +
               r"{1,120}?,\s*sondern\s+(?:ein|eine|einen|einem|einer|eines)\b", re.I),
    re.compile(r"\bweniger\b" + _CLAUSE + r"{1,120}?\bals\s+vielmehr\b", re.I),
]


def rule_negative_parallelism(ctx: Context) -> Iterator[Hit]:
    taken: list[tuple[int, int]] = []
    for pattern in _PARALLEL:
        for match in pattern.finditer(ctx.masked):
            if any(match.start() < end and start < match.end() for start, end in taken):
                continue
            taken.append((match.start(), match.end()))
            shown = " ".join(match.group(0).split())
            if len(shown) > 70:
                shown = shown[:30] + " … " + shown[-30:]
            yield Hit(
                "negative-parallelism", match.start(), match.end() - match.start(),
                f"Negativer Parallelismus «{shown}». Die Aussage direkt machen, "
                f"ohne Gegenfigur.",
                f"Negative parallelism «{shown}». Make the point directly, without "
                f"the contrast figure.",
            )


# --- 7. emoji ----------------------------------------------------------------

_EMOJI_BASE = (
    "\U0001F000-\U0001FAFF"
    "☀-➿"
    "⌚⌛⌨⏏⏩-⏳⏸-⏺"
    "⬅-⬇⬛⬜⭐⭕"
)
_EMOJI = re.compile(
    "[" + _EMOJI_BASE + "][️‍\U0001F3FB-\U0001F3FF⃣" + _EMOJI_BASE + "]*"
)
_HEADING_OR_ITEM = re.compile(r"^[ \t]*(?:>[ \t]*)*(?:#{1,6}[ \t]*|[-*+][ \t]+|\d+[.)][ \t]+)?$")


def rule_emoji(ctx: Context) -> Iterator[Hit]:
    for match in _EMOJI.finditer(ctx.masked):
        prefix = _line_prefix(ctx.masked, match.start())
        emoji = match.group(0)
        if prefix.strip() and _HEADING_OR_ITEM.match(prefix):
            yield Hit("emoji", match.start(), len(emoji),
                      f"Emoji «{emoji}» vor Überschrift oder Listenpunkt. Entfernen.",
                      f"Emoji «{emoji}» before a heading or list item. Remove it.")
        else:
            yield Hit("emoji", match.start(), len(emoji),
                      f"Emoji «{emoji}» im Fliesstext. Entfernen oder in Worten sagen.",
                      f"Emoji «{emoji}» in prose. Remove it or say it in words.")


RULE_FUNCTIONS: dict[str, Callable[[Context], Iterator[Hit]]] = {
    "dash": rule_dash,
    "eszett": rule_eszett,
    "quotes": rule_quotes,
    "quotes-mixed": rule_quotes_mixed,
    "floskel": rule_floskel,
    "negative-parallelism": rule_negative_parallelism,
    "emoji": rule_emoji,
    "anglicism": rule_anglicism,
}

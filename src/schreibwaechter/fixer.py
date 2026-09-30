"""Safe mechanical fixes: ß to ss in de-CH, and quotation mark style.

Dashes, phrases and everything else need a rewritten sentence, so they are
never touched here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import quotes as q
from .config import Config
from .directives import Directives
from .prose import LineIndex, mask_text


@dataclass
class FixResult:
    text: str
    eszett: int = 0
    quotes: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def changed(self) -> int:
        return self.eszett + self.quotes


def fix_text(text: str, config: Config | None = None) -> FixResult:
    config = config or Config()
    bom = text.startswith("﻿")
    body = text[1:] if bom else text
    index = LineIndex(body)
    masked = mask_text(body)
    directives = Directives(body, index)
    replacements: dict[int, str] = {}
    result = FixResult(text=text)

    def allowed(rule: str, offset: int) -> bool:
        line, _ = index.position(offset)
        return not directives.is_disabled(rule, line)

    if config.rule_active("eszett"):
        for offset, char in enumerate(masked):
            if char in "ßẞ" and allowed("eszett", offset):
                replacements[offset] = "ss" if char == "ß" else "SS"
                result.eszett += 1

    if config.rule_active("quotes") or config.rule_active("quotes-mixed"):
        found = q.scan(masked)
        families = {x.family for x in found}
        expected = q.EXPECTED[config.locale]
        needs_fix = bool(found) and (len(families) > 1 or not families <= expected)
        if needs_fix and not q.balanced(found):
            result.notes.append(
                "quotes: not converted, the text contains unpaired quotation marks"
            )
        elif needs_fix:
            left, right = q.TARGET[config.locale]
            for quote in found:
                if quote.role != "open" or quote.partner is None:
                    continue
                closing = found[quote.partner]
                if quote.char == left and closing.char == right:
                    continue
                if not (
                    allowed("quotes", quote.offset) and allowed("quotes", closing.offset)
                    and allowed("quotes-mixed", quote.offset)
                ):
                    continue
                replacements[quote.offset] = left
                replacements[closing.offset] = right
                result.quotes += 1

    if replacements:
        parts = []
        for offset, char in enumerate(body):
            parts.append(replacements.get(offset, char))
        result.text = ("﻿" if bom else "") + "".join(parts)
    return result

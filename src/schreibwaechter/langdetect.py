"""Very small language check: is this prose German?

It counts common German and English function words. That is enough to tell
an agent's German answer from an English one, which is all the hooks need.
"""

from __future__ import annotations

import re

from .prose import mask_text, prose_only

GERMAN = frozenset(
    """
    der die das den dem des und ist nicht ein eine einen einem einer eines zu mit
    auf für von sich auch es ich wir sie im dass wird werden kann können oder aber
    wie bei nach noch nur schon hat haben sind als aus über unter wenn weil dann
    diese dieser dieses diesem diesen jetzt hier mehr sehr kein keine du dir dich
    mich mir uns euch ihr ihre sein seine wurde wurden habe gibt bitte ja nein zum
    zur vom beim ins doch mal damit dafür ob oft wo warum weshalb welche welcher
    muss müssen soll sollte würde bereits gerade immer etwas nichts alle alles
    """.split()
)
ENGLISH = frozenset(
    """
    the and is are was were to of that it for on with as this be by not or but you
    we they have has from at which will can would should there their if what when
    your our do does did my me been being these those than then into just about
    """.split()
)
_WORD = re.compile(r"[A-Za-zÄÖÜäöüßẞéèàç]+")
_UMLAUT = re.compile(r"[äöüÄÖÜß]")


def german_score(text: str) -> tuple[int, int, int]:
    """Return (german hits, english hits, word count) for the prose in text."""
    prose = prose_only(mask_text(text))
    words = [w.lower() for w in _WORD.findall(prose)]
    german = sum(1 for w in words if w in GERMAN)
    english = sum(1 for w in words if w in ENGLISH)
    if _UMLAUT.search(prose):
        german += 1
    return german, english, len(words)


def is_german(text: str) -> bool:
    german, english, total = german_score(text)
    if total == 0 or german == 0:
        return False
    if total < 8:
        return german > english
    return german > english and german / total >= 0.08

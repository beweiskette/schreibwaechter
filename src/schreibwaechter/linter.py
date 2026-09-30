"""Run all active rules on a text and return findings."""

from __future__ import annotations

from .config import Config
from .directives import Directives
from .findings import ERROR, RULES, WARNING, Finding
from .prose import LineIndex, mask_text
from .rules import RULE_FUNCTIONS, Context


def lint_text(text: str, config: Config | None = None, path: str | None = None) -> list[Finding]:
    config = config or Config()
    text = text.lstrip("﻿") if text.startswith("﻿") else text
    index = LineIndex(text)
    masked = mask_text(text)
    directives = Directives(text, index)
    ctx = Context(text=text, masked=masked, index=index, config=config)
    findings: list[Finding] = []
    for rule_id in RULES:
        if not config.rule_active(rule_id):
            continue
        for hit in RULE_FUNCTIONS[rule_id](ctx):
            line, column = index.position(hit.offset)
            if directives.is_disabled(rule_id, line):
                continue
            findings.append(
                Finding(
                    rule=rule_id,
                    severity=config.severity_of(rule_id, hit.severity),
                    offset=hit.offset,
                    length=hit.length,
                    line=line,
                    column=column,
                    text=text[hit.offset:hit.offset + hit.length],
                    message_de=hit.message_de,
                    message_en=hit.message_en,
                    suggestion=hit.suggestion,
                    entry=hit.entry,
                    path=path,
                )
            )
    findings.sort(key=lambda f: (f.offset, f.rule))
    return findings


def count(findings: list[Finding]) -> tuple[int, int]:
    errors = sum(1 for f in findings if f.severity == ERROR)
    warnings = sum(1 for f in findings if f.severity == WARNING)
    return errors, warnings


def summary(errors: int, warnings: int, lang: str = "de") -> str:
    if lang == "en":
        return (f"{errors} error{'' if errors == 1 else 's'}, "
                f"{warnings} warning{'' if warnings == 1 else 's'}")
    return f"{errors} Fehler, {warnings} Warnung{'' if warnings == 1 else 'en'}"


def is_failure(findings: list[Finding], strict: bool) -> bool:
    errors, warnings = count(findings)
    return errors > 0 or (strict and warnings > 0)

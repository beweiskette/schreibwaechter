"""Inline disable comments.

Supported forms (rule lists are optional and comma or space separated)::

    <!-- schreibwaechter: disable -->
    <!-- schreibwaechter: disable dash, floskel -->
    <!-- schreibwaechter: enable dash -->
    <!-- schreibwaechter: disable-next-line eszett -->
    <!-- schreibwaechter: disable-line -->
"""

from __future__ import annotations

import re

from .prose import LineIndex

_DIRECTIVE = re.compile(
    r"<!--\s*schreibwaechter\s*:\s*(disable-next-line|disable-line|disable|enable)\b"
    r"(.*?)-->",
    re.S | re.I,
)
ALL = "*"


class Directives:
    def __init__(self, text: str, index: LineIndex | None = None) -> None:
        index = index or LineIndex(text)
        self.line_count = len(index.starts)
        # Per line: set of disabled rule ids, ALL meaning every rule.
        self.disabled: list[set[str]] = [set() for _ in range(self.line_count + 2)]
        ranges: list[tuple[int, str, set[str]]] = []
        for match in _DIRECTIVE.finditer(text):
            action = match.group(1).lower()
            rules = {r for r in re.split(r"[\s,]+", match.group(2).strip()) if r}
            rules = rules or {ALL}
            line, _ = index.position(match.start())
            end_line, _ = index.position(match.end())
            if action == "disable-line":
                for number in range(line, end_line + 1):
                    self.disabled[number] |= rules
            elif action == "disable-next-line":
                target = end_line + 1
                if target <= self.line_count:
                    self.disabled[target] |= rules
            else:
                ranges.append((line, action, rules))
        active: set[str] = set()
        pending = iter(sorted(ranges, key=lambda item: item[0]))
        upcoming = next(pending, None)
        for number in range(1, self.line_count + 1):
            while upcoming is not None and upcoming[0] == number:
                _, action, rules = upcoming
                if action == "disable":
                    active |= rules
                elif ALL in rules:
                    active = set()
                else:
                    active -= rules
                upcoming = next(pending, None)
            self.disabled[number] |= active

    def is_disabled(self, rule: str, line: int) -> bool:
        if line < 1 or line > self.line_count:
            return False
        rules = self.disabled[line]
        return ALL in rules or rule in rules

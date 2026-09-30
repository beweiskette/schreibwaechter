"""Load and compile the phrase lists (bundled JSON files plus user extras)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path


class WordlistError(ValueError):
    """Raised when a phrase list file or pattern is invalid."""


@dataclass(frozen=True)
class Entry:
    id: str
    regex: re.Pattern[str]
    hint_de: str = ""
    hint_en: str = ""
    category: str = ""
    severity: str | None = None


def _spaces_to_whitespace(pattern: str) -> str:
    """Turn literal spaces outside character classes into ``\\s+``."""
    out: list[str] = []
    in_class = False
    escaped = False
    for char in pattern:
        if escaped:
            out.append(char)
            escaped = False
        elif char == "\\":
            out.append(char)
            escaped = True
        elif in_class:
            out.append(char)
            if char == "]":
                in_class = False
        elif char == "[":
            out.append(char)
            in_class = True
        elif char == " ":
            out.append(r"\s+")
        else:
            out.append(char)
    return "".join(out).replace(r"\s+\s+", r"\s+")


def compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a list pattern with the conventions described in the README."""
    body = _spaces_to_whitespace(pattern.replace("ß", "ss").replace("ẞ", "SS"))
    try:
        return re.compile(r"(?<!\w)(?:" + body + r")(?!\w)", re.I | re.M)
    except re.error as exc:
        raise WordlistError(f"invalid pattern {pattern!r}: {exc}") from exc


def phrase_to_pattern(phrase: str) -> str:
    """Escape a plain phrase so it can be used as a list pattern."""
    parts = phrase.split()
    return " ".join(re.escape(part) for part in parts)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9äöü]+", "-", text.lower()).strip("-") or "eintrag"


def entries_from_data(data: dict | list, source: str) -> list[Entry]:
    entries: list[Entry] = []
    raw_entries = data if isinstance(data, list) else data.get("entries")
    if not isinstance(raw_entries, list):
        raise WordlistError(f"{source}: expected a list under 'entries'")
    for raw in raw_entries:
        if isinstance(raw, str):
            raw = {"phrase": raw}
        if not isinstance(raw, dict):
            raise WordlistError(f"{source}: entries must be objects or strings")
        if "pattern" in raw:
            pattern = str(raw["pattern"])
        elif "phrase" in raw:
            pattern = phrase_to_pattern(str(raw["phrase"]))
        else:
            raise WordlistError(f"{source}: entry without 'pattern' or 'phrase'")
        entry_id = str(raw.get("id") or _slug(str(raw.get("phrase", pattern))))
        severity = raw.get("severity")
        if severity not in (None, "error", "warning"):
            raise WordlistError(f"{source}: entry {entry_id}: bad severity {severity!r}")
        entries.append(
            Entry(
                id=entry_id,
                regex=compile_pattern(pattern),
                hint_de=str(raw.get("hint_de", "")),
                hint_en=str(raw.get("hint_en", "")),
                category=str(raw.get("category", "")),
                severity=severity,
            )
        )
    return entries


def load_bundled(name: str) -> list[Entry]:
    text = resources.files("schreibwaechter").joinpath("data", name).read_text("utf-8")
    return entries_from_data(json.loads(text), name)


def load_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WordlistError(f"cannot read word list {path}: {exc}") from exc
    if not isinstance(data, (dict, list)):
        raise WordlistError(f"{path}: expected an object or a list")
    return data


def phrases_to_entries(phrases: list[str], source: str) -> list[Entry]:
    return entries_from_data({"entries": [{"phrase": p} for p in phrases]}, source)

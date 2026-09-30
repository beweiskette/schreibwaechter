"""Separate prose from everything that must not be linted.

``mask_text`` returns a string of the same length as the input in which code,
URLs, paths, front matter, HTML comments and similar regions are replaced by
``MASK`` characters. Newlines are kept, so offsets, line numbers and columns
stay valid. Rules then run on the masked text only.
"""

from __future__ import annotations

import bisect
import re

MASK = "\x00"

_FENCE_OPEN = re.compile(r"^[ \t]*(?:>[ \t]*)*(`{3,}|~{3,})")
_HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
_HTML_BLOCKS = re.compile(
    r"<(pre|code|script|style|kbd|samp)\b[^>]*>.*?(?:</\1\s*>|\Z)", re.S | re.I
)
_INLINE_CODE = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)", re.S)
_HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>\n]*)?/?>")
_LINK_TARGET = re.compile(r"(?<=\])\((?:[^()\s]|\([^()\s]*\))*(?:\s+\"[^\"\n]*\")?\)")
_REF_DEFINITION = re.compile(r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*\S.*$", re.M)
_URL = re.compile(
    r"(?:\b(?:https?|ftp|file|ssh|git)://|\bmailto:|\bwww\.)[^\s<>«»\"'`\x00]+",
    re.I,
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_WIN_PATH = re.compile(r"(?<![\w])[A-Za-z]:[\\/][^\s<>\"«»|*?\x00]*")
_UNC_PATH = re.compile(r"(?<![\w\\])\\\\[^\s<>\"«»|\x00]+")
_ABS_PATH = re.compile(r"(?<![\w/.~-])(?:~|\.{1,2})?/[\w.~@+-]+(?:/[\w.~@+-]*)*")
_REL_PATH = re.compile(r"(?<![\w/.~-])[\w.@+-]+(?:/[\w.@+-]+)+/?")
_EXTENSIONS = (
    "md|markdown|mdx|txt|rst|py|pyi|js|mjs|cjs|ts|tsx|jsx|json|jsonl|toml|yaml|yml|"
    "ini|cfg|conf|lock|xml|html|htm|css|scss|sh|bash|zsh|ps1|psm1|bat|cmd|exe|dll|"
    "rs|go|java|kt|c|h|cpp|hpp|cs|rb|php|swift|lua|sql|csv|tsv|log|env|pdf|png|jpg|"
    "jpeg|gif|svg|webp|zip|gz|tar|whl|gd|tscn|tres|uasset|umap"
)
_FILENAME = re.compile(
    r"(?<![\w.-])[\w-]+(?:\.[\w-]+)*\.(?:" + _EXTENSIONS + r")(?![\w-])", re.I
)
_CLI_FLAG = re.compile(r"(?<!\S)--?[A-Za-z][\w-]*(?:=\S+)?")
_ESCAPED = re.compile(r"\\[\\`*_{}\[\]()#+\-.!|\"]")


def _apply(chars: list[str], start: int, end: int) -> None:
    for i in range(start, end):
        if chars[i] != "\n":
            chars[i] = MASK


def _mask_front_matter(text: str, chars: list[str]) -> None:
    offset = 1 if text.startswith("﻿") else 0
    for fence in ("---", "+++"):
        if text.startswith(fence + "\n", offset) or text.startswith(fence + "\r\n", offset):
            pattern = re.compile(
                r"^(?:" + re.escape(fence) + r"|\.\.\.)[ \t]*\r?$", re.M
            )
            first_newline = text.index("\n", offset)
            match = pattern.search(text, first_newline + 1)
            end = match.end() if match else len(text)
            _apply(chars, 0, end)
            return


def _mask_fences(text: str, chars: list[str]) -> None:
    pos = 0
    open_char = ""
    open_len = 0
    block_start = 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if not open_char:
            match = _FENCE_OPEN.match(stripped)
            if match:
                open_char = match.group(1)[0]
                open_len = len(match.group(1))
                block_start = pos
        else:
            match = _FENCE_OPEN.match(stripped)
            if (
                match
                and match.group(1)[0] == open_char
                and len(match.group(1)) >= open_len
                and stripped[match.end():].strip() == ""
            ):
                _apply(chars, block_start, pos + len(line))
                open_char = ""
        pos += len(line)
    if open_char:
        _apply(chars, block_start, len(text))


def _mask_regex(chars: list[str], pattern: re.Pattern[str], group: int = 0) -> None:
    current = "".join(chars)
    for match in pattern.finditer(current):
        _apply(chars, match.start(group), match.end(group))


def _mask_urls(chars: list[str]) -> None:
    current = "".join(chars)
    for match in _URL.finditer(current):
        url = match.group(0)
        # Trailing sentence punctuation is not part of the URL.
        trimmed = url.rstrip(".,;:!?")
        while trimmed.endswith(")") and trimmed.count(")") > trimmed.count("("):
            trimmed = trimmed[:-1].rstrip(".,;:!?")
        _apply(chars, match.start(), match.start() + len(trimmed))


def _mask_relative_paths(chars: list[str]) -> None:
    current = "".join(chars)
    for match in _REL_PATH.finditer(current):
        value = match.group(0)
        segments = [s for s in value.split("/") if s]
        looks_like_path = (
            value.count("/") >= 2
            or "." in segments[-1]
            or value.startswith(("./", "../"))
        )
        if looks_like_path:
            _apply(chars, match.start(), match.end())


def mask_text(text: str) -> str:
    """Return ``text`` with all non-prose regions replaced by ``MASK``."""
    chars = list(text)
    _mask_front_matter(text, chars)
    _mask_fences("".join(chars), chars)
    _mask_regex(chars, _HTML_COMMENT)
    _mask_regex(chars, _HTML_BLOCKS)
    _mask_regex(chars, _INLINE_CODE)
    _mask_regex(chars, _HTML_TAG)
    _mask_regex(chars, _LINK_TARGET)
    _mask_regex(chars, _REF_DEFINITION)
    _mask_urls(chars)
    _mask_regex(chars, _EMAIL)
    _mask_regex(chars, _WIN_PATH)
    _mask_regex(chars, _UNC_PATH)
    _mask_regex(chars, _ABS_PATH)
    _mask_relative_paths(chars)
    _mask_regex(chars, _FILENAME)
    _mask_regex(chars, _CLI_FLAG)
    _mask_regex(chars, _ESCAPED)
    return "".join(chars)


def prose_only(masked: str) -> str:
    """Drop mask characters, for statistics such as language detection."""
    return masked.replace(MASK, " ")


class LineIndex:
    """Map string offsets to 1-based line and column numbers."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.starts = [0]
        for match in re.finditer("\n", text):
            self.starts.append(match.end())

    def position(self, offset: int) -> tuple[int, int]:
        line = bisect.bisect_right(self.starts, offset) - 1
        return line + 1, offset - self.starts[line] + 1

    def line_text(self, line: int) -> str:
        start = self.starts[line - 1]
        end = self.starts[line] - 1 if line < len(self.starts) else len(self.text)
        return self.text[start:end].rstrip("\r")


def normalize_eszett(text: str) -> tuple[str, list[int]]:
    """Replace ß with ss and return the new text plus an offset map.

    ``mapping[i]`` is the offset in the original text for index ``i`` of the
    normalized text; the map has one extra entry for the end position.
    """
    out: list[str] = []
    mapping: list[int] = []
    for index, char in enumerate(text):
        if char == "ß":
            out.append("ss")
            mapping.extend((index, index))
        elif char == "ẞ":
            out.append("SS")
            mapping.extend((index, index))
        else:
            out.append(char)
            mapping.append(index)
    mapping.append(len(text))
    return "".join(out), mapping

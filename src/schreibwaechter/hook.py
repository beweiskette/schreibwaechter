"""Stop hook for Claude Code and Codex.

Both agents call the hook command with a JSON object on stdin when the agent
wants to end its turn. If the last assistant message is German prose with
errors, the hook answers ``{"decision": "block", "reason": ...}`` and the
agent continues with the reason as instruction. ``stop_hook_active`` is set
when the agent is already continuing because of a Stop hook; the hook then
always allows the stop, so there is at most one rewrite round.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .config import Config, check_locale, resolve_config
from .findings import Finding
from .langdetect import is_german
from .linter import count, is_failure, lint_text, summary

MAX_ITEMS = 25


def _text_blocks(content: object, kinds: tuple[str, ...]) -> list[str]:
    if isinstance(content, str):
        return [content]
    blocks: list[str] = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") in kinds:
                value = item.get("text")
                if isinstance(value, str):
                    blocks.append(value)
    return blocks


def last_assistant_text(transcript_path: str | os.PathLike[str]) -> str | None:
    """Read the text of the last assistant message from a JSONL transcript.

    Understands the Claude Code transcript format (one line per content block,
    blocks of one message share ``message.id``) and the Codex rollout format
    (``response_item`` lines with ``payload.role == "assistant"``).
    """
    try:
        handle = open(transcript_path, encoding="utf-8", errors="replace")
    except OSError:
        return None
    last_id: object = None
    last_blocks: list[str] = []
    with handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            # Claude Code
            if entry.get("type") == "assistant" and not entry.get("isSidechain"):
                message = entry.get("message")
                if not isinstance(message, dict) or message.get("role") != "assistant":
                    continue
                blocks = _text_blocks(message.get("content"), ("text",))
                if not blocks:
                    continue
                message_id = message.get("id") or entry.get("uuid")
                if message_id != last_id:
                    last_id, last_blocks = message_id, []
                last_blocks.extend(blocks)
                continue
            # Codex
            payload = entry.get("payload")
            if entry.get("type") == "response_item" and isinstance(payload, dict):
                if payload.get("type") == "message" and payload.get("role") == "assistant":
                    blocks = _text_blocks(payload.get("content"), ("output_text", "text"))
                    if blocks:
                        last_id, last_blocks = object(), blocks
    if not last_blocks:
        return None
    return "\n\n".join(last_blocks)


def _context(text: str, finding: Finding, width: int = 30) -> str:
    start = max(0, finding.offset - width)
    end = min(len(text), finding.offset + finding.length + width)
    snippet = " ".join(text[start:end].split())
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


def build_reason(text: str, findings: list[Finding], config: Config) -> str:
    lang = config.lang
    totals = summary(*count(findings), lang)
    if lang == "en":
        head = (
            f"schreibwaechter: your last answer breaks the writing rules for "
            f"{config.locale} ({totals}). Write the answer again and fix these "
            f"places. Leave code, paths and URLs unchanged."
        )
        where, hint, more = "line", "context", "more findings not shown"
    else:
        head = (
            f"schreibwaechter: Deine letzte Antwort verletzt die Schreibregeln für "
            f"{config.locale} ({totals}). Schreib die Antwort neu und behebe diese "
            f"Stellen. Code, Pfade und URLs bleiben unverändert."
        )
        where, hint, more = "Zeile", "Stelle", "weitere Befunde nicht gezeigt"
    lines = [head]
    for finding in findings[:MAX_ITEMS]:
        item = (
            f"- {where} {finding.line} [{finding.rule}, {finding.severity}] "
            f"{finding.message(lang)} {hint}: «{_context(text, finding)}»"
        )
        if finding.suggestion:
            item += f" -> {finding.suggestion}"
        lines.append(item)
    if len(findings) > MAX_ITEMS:
        lines.append(f"- ({len(findings) - MAX_ITEMS} {more})")
    return "\n".join(lines)


def run_hook(
    agent: str,
    stdin_text: str,
    locale: str | None = None,
    strict: bool | None = None,
    config_path: str | None = None,
    no_config: bool = False,
) -> str:
    """Return the JSON the hook should print (empty string means: allow)."""
    try:
        data = json.loads(stdin_text) if stdin_text.strip() else {}
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict) or data.get("stop_hook_active"):
        return ""
    text = data.get("last_assistant_message")
    if not isinstance(text, str) or not text.strip():
        transcript = data.get("transcript_path")
        text = last_assistant_text(transcript) if transcript else None
    if not text or not is_german(text):
        return ""
    start = Path(data["cwd"]) if isinstance(data.get("cwd"), str) else None
    config = resolve_config(config_path, no_config, start)
    if locale:
        config.locale = check_locale(locale)
    if strict is not None:
        config.strict = strict
    findings = lint_text(text, config)
    if not is_failure(findings, config.strict):
        return ""
    return json.dumps(
        {"decision": "block", "reason": build_reason(text, findings, config)},
        ensure_ascii=True,
    )

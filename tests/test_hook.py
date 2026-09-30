"""Tests for the Stop hook with synthetic transcripts."""

import json
import subprocess
import sys

from schreibwaechter.hook import last_assistant_text, run_hook
from schreibwaechter.langdetect import is_german

GERMAN_BAD = "Das Ergebnis ist gut — die Tests laufen und die Straße ist frei."
GERMAN_GOOD = "Das Ergebnis ist gut. Die Tests laufen, und die Strasse ist frei."
ENGLISH_BAD = "The result is good — the tests pass and the build is green."


def claude_line(role, content, message_id=None, sidechain=False, entry_type=None):
    message = {"role": role, "content": content}
    if message_id:
        message["id"] = message_id
    return {
        "type": entry_type or role,
        "isSidechain": sidechain,
        "uuid": f"u-{message_id or role}",
        "message": message,
    }


def write_jsonl(path, entries):
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    return path


def claude_transcript(tmp_path, final_text):
    entries = [
        {"type": "queue-operation", "operation": "enqueue"},
        claude_line("user", "Bitte prüfe den Build."),
        claude_line("assistant", [{"type": "thinking", "thinking": "..."}], "m1"),
        claude_line("assistant", [{"type": "text", "text": "Ich schaue nach."}], "m1"),
        claude_line("assistant", [{"type": "tool_use", "id": "t1", "name": "Bash",
                                   "input": {"command": "echo a - b"}}], "m1"),
        claude_line("user", [{"type": "tool_result", "tool_use_id": "t1",
                              "content": "a - b"}]),
        claude_line("assistant", [{"type": "text", "text": "Ein Seitenagent — egal."}],
                    "side", sidechain=True),
        claude_line("assistant", [{"type": "text", "text": final_text}], "m2"),
        {"type": "system", "subtype": "stop_hook_summary"},
    ]
    return write_jsonl(tmp_path / "session.jsonl", entries)


def hook_input(transcript, **extra):
    data = {
        "session_id": "test-session",
        "transcript_path": str(transcript),
        "cwd": str(transcript.parent),
        "hook_event_name": "Stop",
        "stop_hook_active": False,
    }
    data.update(extra)
    return json.dumps(data)


def test_reads_last_assistant_message(tmp_path):
    transcript = claude_transcript(tmp_path, GERMAN_BAD)
    assert last_assistant_text(transcript) == GERMAN_BAD


def test_joins_text_blocks_of_same_message(tmp_path):
    entries = [
        claude_line("assistant", [{"type": "text", "text": "Teil eins."}], "m9"),
        claude_line("assistant", [{"type": "text", "text": "Teil zwei."}], "m9"),
    ]
    transcript = write_jsonl(tmp_path / "t.jsonl", entries)
    assert last_assistant_text(transcript) == "Teil eins.\n\nTeil zwei."


def test_reads_codex_rollout(tmp_path):
    entries = [
        {"type": "session_meta", "payload": {"id": "x"}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
                                              "content": [{"type": "input_text", "text": "Hallo"}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant",
                                              "content": [{"type": "output_text", "text": GERMAN_BAD}]}},
    ]
    transcript = write_jsonl(tmp_path / "rollout.jsonl", entries)
    assert last_assistant_text(transcript) == GERMAN_BAD


def test_blocks_german_message_with_errors(tmp_path):
    transcript = claude_transcript(tmp_path, GERMAN_BAD)
    output = run_hook("claude", hook_input(transcript), locale="de-CH", no_config=True)
    data = json.loads(output)
    assert data["decision"] == "block"
    assert "[dash, error]" in data["reason"]
    assert "[eszett, error]" in data["reason"]
    assert "Strasse" in data["reason"]


def test_allows_clean_german_message(tmp_path):
    transcript = claude_transcript(tmp_path, GERMAN_GOOD)
    assert run_hook("claude", hook_input(transcript), locale="de-CH", no_config=True) == ""


def test_allows_when_stop_hook_active(tmp_path):
    transcript = claude_transcript(tmp_path, GERMAN_BAD)
    data = hook_input(transcript, stop_hook_active=True)
    assert run_hook("claude", data, locale="de-CH", no_config=True) == ""


def test_non_german_message_passes(tmp_path):
    transcript = claude_transcript(tmp_path, ENGLISH_BAD)
    assert run_hook("claude", hook_input(transcript), locale="de-CH", no_config=True) == ""


def test_prefers_last_assistant_message_field(tmp_path):
    transcript = claude_transcript(tmp_path, GERMAN_GOOD)
    data = hook_input(transcript, last_assistant_message=GERMAN_BAD)
    assert run_hook("codex", data, locale="de-CH", no_config=True)


def test_warnings_only_do_not_block_unless_strict(tmp_path):
    text = "Die Lösung arbeitet nahtlos mit allen Teilen zusammen und ist fertig."
    transcript = claude_transcript(tmp_path, text)
    assert run_hook("claude", hook_input(transcript), locale="de-CH", no_config=True) == ""
    assert run_hook("claude", hook_input(transcript), locale="de-CH", strict=True,
                    no_config=True)


def test_code_in_message_is_ignored(tmp_path):
    text = "Hier ist der Befehl, der die Tests startet:\n\n```\nnpm test -- --watch — ok\n```\n"
    transcript = claude_transcript(tmp_path, text)
    assert run_hook("claude", hook_input(transcript), locale="de-CH", no_config=True) == ""


def test_missing_transcript_allows(tmp_path):
    data = hook_input(tmp_path / "fehlt.jsonl")
    assert run_hook("claude", data, no_config=True) == ""


def test_empty_or_invalid_stdin_allows():
    assert run_hook("claude", "", no_config=True) == ""
    assert run_hook("claude", "kein json", no_config=True) == ""


def test_hook_uses_config_from_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("SCHREIBWAECHTER_CONFIG", raising=False)
    (tmp_path / ".schreibwaechter.toml").write_text('locale = "de-CH"\n', encoding="utf-8")
    transcript = claude_transcript(tmp_path, "Die Straße ist frei und die Tests laufen.")
    assert run_hook("claude", hook_input(transcript))


def test_hook_subprocess_end_to_end(tmp_path):
    transcript = claude_transcript(tmp_path, GERMAN_BAD)
    proc = subprocess.run(
        [sys.executable, "-m", "schreibwaechter", "hook", "claude", "--locale", "de-CH",
         "--no-config"],
        input=hook_input(transcript).encode("utf-8"),
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout.decode("utf-8"))
    assert data["decision"] == "block"


def test_language_detection():
    assert is_german(GERMAN_BAD)
    assert is_german("Fertig, alles läuft.")
    assert not is_german(ENGLISH_BAD)
    assert not is_german("Done.")
    assert not is_german("```\nder die das und ist\n```")

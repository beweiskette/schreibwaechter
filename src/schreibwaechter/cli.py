"""Command line interface."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from . import __version__
from .config import LANGS, LOCALES, Config, ConfigError, check_locale, resolve_config
from .findings import RULES, Finding
from .fixer import fix_text
from .hook import run_hook
from .langdetect import is_german
from .linter import count, is_failure, lint_text, summary
from .wordlists import WordlistError

TEXT_SUFFIXES = {".md", ".markdown", ".mdx", ".txt", ".text", ".rst"}
STDIN_NAME = "<stdin>"


def _utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def _read_stdin() -> str:
    return sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")


def _expand(paths: list[str]) -> list[str]:
    result: list[str] = []
    for raw in paths or ["-"]:
        if raw == "-":
            result.append("-")
            continue
        path = Path(raw)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                parts = set(child.parts)
                if child.is_file() and child.suffix.lower() in TEXT_SUFFIXES and not (
                    parts & {".git", ".venv", "node_modules", "__pycache__"}
                ):
                    result.append(str(child))
        else:
            result.append(raw)
    return result


def _read(name: str) -> str:
    if name == "-":
        return _read_stdin()
    with open(name, encoding="utf-8-sig", newline="") as handle:
        return handle.read()


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--locale", choices=LOCALES, help="de-CH or de-DE (default: config or de-DE)")
    parser.add_argument("--config", metavar="PATH", help="use this config file")
    parser.add_argument("--no-config", action="store_true", help="ignore .schreibwaechter.toml")


def _load_config(args: argparse.Namespace) -> Config:
    config = resolve_config(args.config, args.no_config)
    if args.locale:
        config.locale = check_locale(args.locale)
    if getattr(args, "lang", None):
        config.lang = args.lang
    if getattr(args, "strict", False):
        config.strict = True
    for item in getattr(args, "disable", None) or []:
        for rule in filter(None, (r.strip() for r in item.split(","))):
            if rule not in RULES:
                raise ConfigError(f"unknown rule {rule!r}")
            config.disabled.add(rule)
    return config


def _format_text(finding: Finding, lang: str) -> str:
    line = (
        f"{finding.path}:{finding.line}:{finding.column}: {finding.severity} "
        f"[{finding.rule}] {finding.message(lang)}"
    )
    if finding.suggestion:
        line += f" -> {finding.suggestion}"
    return line


def cmd_check(args: argparse.Namespace) -> int:
    config = _load_config(args)
    all_findings: list[Finding] = []
    skipped: list[str] = []
    failed_read = False
    for name in _expand(args.files):
        shown = (args.stdin_name or STDIN_NAME) if name == "-" else name
        try:
            text = _read(name)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"schreibwaechter: cannot read {shown}: {exc}", file=sys.stderr)
            failed_read = True
            continue
        if args.only_german and not is_german(text):
            skipped.append(shown)
            continue
        all_findings.extend(lint_text(text, config, path=shown))
    errors, warnings = count(all_findings)
    if args.format == "json":
        payload = {
            "version": 1,
            "locale": config.locale,
            "errors": errors,
            "warnings": warnings,
            "skipped": skipped,
            "findings": [f.to_dict() for f in all_findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for finding in all_findings:
            print(_format_text(finding, config.lang))
        if not args.quiet:
            print(f"{summary(errors, warnings, config.lang)} ({config.locale})",
                  file=sys.stderr)
    if failed_read:
        return 2
    return 1 if is_failure(all_findings, config.strict) else 0


def cmd_fix(args: argparse.Namespace) -> int:
    config = _load_config(args)
    status = 0
    for name in _expand(args.files):
        shown = STDIN_NAME if name == "-" else name
        try:
            text = _read(name)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"schreibwaechter: cannot read {shown}: {exc}", file=sys.stderr)
            status = 2
            continue
        result = fix_text(text, config)
        for note in result.notes:
            print(f"{shown}: {note}", file=sys.stderr)
        if name == "-":
            sys.stdout.write(result.text)
            continue
        if args.diff:
            diff = difflib.unified_diff(
                text.splitlines(keepends=True), result.text.splitlines(keepends=True),
                fromfile=shown, tofile=shown,
            )
            sys.stdout.writelines(diff)
        elif result.changed:
            with open(name, "w", encoding="utf-8", newline="") as handle:
                handle.write(result.text)
        if result.changed:
            print(
                f"{shown}: {result.eszett} ß -> ss, {result.umlaut} words ae/oe/ue -> ä/ö/ü, "
                f"{result.quotes} quote pairs converted",
                file=sys.stderr,
            )
    return status


def cmd_hook(args: argparse.Namespace) -> int:
    try:
        output = run_hook(
            args.agent, _read_stdin(), locale=args.locale,
            strict=True if args.strict else None,
            config_path=args.config, no_config=args.no_config,
        )
    except Exception as exc:  # never break the agent because of the linter
        print(f"schreibwaechter hook: {exc}", file=sys.stderr)
        return 0
    if output:
        sys.stdout.write(output + "\n")
    return 0


def cmd_rules(args: argparse.Namespace) -> int:
    for info in RULES.values():
        title = info.title_en if args.lang == "en" else info.title_de
        fix = " fix" if info.fixable else ""
        print(f"{info.id:<22} {info.severity:<8} {'/'.join(info.locales):<12}{fix:<5} {title}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schreibwaechter",
        description="Lint German prose for AI writing patterns (de-CH and de-DE).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="lint files or stdin")
    check.add_argument("files", nargs="*", help="files or directories, '-' for stdin")
    _add_common(check)
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.add_argument("--lang", choices=LANGS, help="language of the messages")
    check.add_argument("--strict", action="store_true", help="warnings also fail")
    check.add_argument("--disable", action="append", metavar="RULES",
                       help="comma separated rule ids to switch off")
    check.add_argument("--only-german", action="store_true",
                       help="skip inputs that are not detected as German")
    check.add_argument("--stdin-name", metavar="NAME", help="file name to show for stdin input")
    check.add_argument("-q", "--quiet", action="store_true", help="no summary line")
    check.set_defaults(func=cmd_check)

    fix = sub.add_parser("fix", help="apply safe mechanical fixes (ß, quotes)")
    fix.add_argument("files", nargs="*", help="files or directories, '-' for stdin")
    _add_common(fix)
    fix.add_argument("--diff", action="store_true", help="print a diff, do not write")
    fix.set_defaults(func=cmd_fix)

    hook = sub.add_parser("hook", help="Stop hook for Claude Code or Codex")
    hook.add_argument("agent", choices=("claude", "codex"))
    _add_common(hook)
    hook.add_argument("--strict", action="store_true", help="block on warnings too")
    hook.set_defaults(func=cmd_hook)

    rules = sub.add_parser("rules", help="list the rules")
    rules.add_argument("--lang", choices=LANGS, default="de")
    rules.set_defaults(func=cmd_rules)
    return parser


def main(argv: list[str] | None = None) -> int:
    _utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, WordlistError) as exc:
        print(f"schreibwaechter: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

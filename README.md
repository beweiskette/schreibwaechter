# schreibwaechter

[Deutsche Fassung](README.de.md)

A deterministic linter for German prose written by AI agents. It knows two
locales: Swiss German (`de-CH`: `ss` instead of `ß`, «guillemets») and
German German (`de-DE`: `ß` allowed, „German quotes“). It runs as a normal
command line tool, as a git pre-commit hook, and as a Stop hook for Claude
Code and Codex, so an agent has to rewrite a German answer that breaks the
rules before its turn ends.

## Why

Agents writing German show the same tells again and again: dashes as
punctuation, inflated phrases such as `spielt eine entscheidende Rolle`,
`nicht nur … sondern auch`, emoji in headings, anglicisms like `macht Sinn`
or `in 2026`. Swiss users additionally get `ß` and „German“ quotation marks
they did not ask for. You can put rules into a prompt, but the agent forgets
them. Existing slop linters (AntiSlop, defluff, ai-slop-linter) are
English-first, know nothing about Swiss spelling and have no hook loop that
sends the text back to the agent.

schreibwaechter uses no model and no network. The same input always gives
the same findings.

## Rules

| id | severity | locale | what it finds | `fix` |
|---|---|---|---|---|
| `dash` | error | both | em dash `—`, en dash `–` with spaces, ` - ` and ` -- ` between words, `–` as list marker | no |
| `eszett` | error | de-CH | `ß` and `ẞ` | yes |
| `quotes` | warning | both | quotation marks in the wrong style (`"…"`, `“…”`, and „…“ in de-CH or «…» in de-DE) | yes |
| `quotes-mixed` | error | both | more than one quotation mark style in one text | yes |
| `floskel` | warning | both | stock phrases and inflated significance from a data file | no |
| `negative-parallelism` | warning | both | `nicht nur … sondern (auch)`, `es geht nicht (nur) um … sondern`, `kein …, sondern ein …` | no |
| `emoji` | warning | both | emoji in prose and before headings or list items | no |
| `anglicism` | warning | both | anglicisms and literal translations from a data file | no |

Allowed on purpose: hyphens inside words (`E-Mail`, `Ein- und Ausgang`),
en dashes without spaces in ranges and connections (`2020–2024`, `8–10`,
`Bern–Genf`), Swiss prices (`Fr. 20.–`), dashes in empty table cells,
Markdown list markers, horizontal rules, and a dash character that is only
mentioned, as in `(—)`.

A rule-of-three check was left out because a deterministic version produced
too many false positives.

Ignored everywhere: fenced code blocks, inline code, `<pre>`/`<code>` blocks,
HTML comments and tags, URLs, e-mail addresses, file paths and file names,
Markdown link targets, command line flags, and YAML or TOML front matter.

`schreibwaechter rules` prints the list.

## Install

Python 3.11 or newer, no dependencies.

```bash
pipx install git+https://github.com/beweiskette/schreibwaechter
# or, from a clone:
git clone https://github.com/beweiskette/schreibwaechter
cd schreibwaechter
python -m pip install .
```

## Quick start

```bash
schreibwaechter check README.md docs/ --locale de-CH
cat antwort.md | schreibwaechter check - --locale de-DE --format json
schreibwaechter fix text.md --locale de-CH --diff   # show the safe fixes
schreibwaechter fix text.md --locale de-CH          # apply them
```

`check` exits with 0 when there are no errors, 1 when there are errors (or
warnings with `--strict`), and 2 for unreadable files or bad configuration.
Directories are searched for `.md`, `.markdown`, `.mdx`, `.txt` and `.rst`.

`fix` only does mechanical changes that cannot change the meaning: `ß` to
`ss` in de-CH, and quotation marks to the locale style. Quotes are converted
only when every mark in the text has a partner. Dashes are never fixed
automatically; the sentence has to be rewritten.

Other options: `--lang en` for English messages, `--disable dash,emoji`,
`--only-german` to skip files that are not German, `--stdin-name` to name
stdin input in the output, `--no-config`, `--config PATH`.

## Example output

For [examples/beispiel.md](examples/beispiel.md) with `--locale de-CH --lang en`:

```text
examples/beispiel.md:6:3: warning [emoji] Emoji «🚀» before a heading or list item. Remove it.
examples/beispiel.md:8:1: warning [floskel] Stock phrase «In der heutigen schnelllebigen Welt». Drop the opener and start with the subject.
examples/beispiel.md:8:88: error [dash] Dash used as punctuation («—»). Rewrite the sentence with a comma, colon, parentheses or a full stop.
examples/beispiel.md:10:18: warning [negative-parallelism] Negative parallelism «nicht nur schnell, sondern auch». Make the point directly, without the contrast figure.
examples/beispiel.md:12:10: warning [quotes] Quotation marks „…“ instead of «…» (de-CH). -> «Das macht Sinn»
examples/beispiel.md:12:46: error [quotes-mixed] Mixed quotation mark styles in one text („…“, "…"). Use «…» throughout.
examples/beispiel.md:12:56: warning [anglicism] Anglicism «In 2026». Use «im Jahr 2026» or just «2026» (from «in 2026»).
examples/beispiel.md:14:28: error [eszett] Eszett in Swiss German: write «gemäss» instead of «gemäß». -> gemäss
examples/beispiel.md:20:48: error [dash] Dash used as punctuation (« - »). Rewrite the sentence with a comma, colon, parentheses or a full stop.
examples/beispiel.md:22:1: warning [floskel] Stock phrase «## Fazit». No conclusion section; put the key point first.
...
4 errors, 12 warnings (de-CH)
```

The dash in the code block and the dashes in the URL and in the front matter
of that file are not reported. `--format json` gives the same findings with
offset, line, column, matched text, German and English message, suggestion
and the id of the list entry.

## Configuration

schreibwaechter reads `.schreibwaechter.toml` from the current directory or
the nearest parent directory. `SCHREIBWAECHTER_CONFIG` points to a specific
file. Command line flags win over the file. A commented template is in
[examples/schreibwaechter.toml](examples/schreibwaechter.toml).

```toml
locale = "de-CH"        # or "de-DE" (default)
lang = "de"             # message language: "de" or "en"
strict = false          # true: warnings also fail and block
disable = ["anglicism"]
# enable = ["dash", "eszett"]   # run only these

[severity]
floskel = "error"

[words]
floskeln = ["Synergieeffekte heben"]
anglicisms = []
floskeln_files = ["team-floskeln.json"]
anglicisms_files = []
ignore = ["nahtlos", "fuellwort-verbindung"]   # entry ids or exact phrases
```

### Inline comments

```markdown
<!-- schreibwaechter: disable dash -->
Text in which dashes are fine.
<!-- schreibwaechter: enable dash -->

<!-- schreibwaechter: disable-next-line eszett -->
Straße (a quoted street name)

Some line <!-- schreibwaechter: disable-line -->
```

`disable` and `enable` without rule ids affect all rules. `enable dash`
only undoes an earlier `disable dash`, not a `disable` of all rules.

### Word lists

The lists live in
[src/schreibwaechter/data/floskeln.json](src/schreibwaechter/data/floskeln.json)
and [anglizismen.json](src/schreibwaechter/data/anglizismen.json). Each entry
has an `id`, a `pattern`, and `hint_de`/`hint_en`; `category` and `severity`
are optional. Your own files use the same format; a plain list of strings is
also accepted and treated as literal phrases.

Pattern rules: Python regular expression, case-insensitive, multiline. The
text is matched with `ß` written as `ss`, so write patterns with `ss`. A
literal space matches any run of whitespace (not inside `[...]`). Word
boundaries are added around the whole pattern.

The lists paraphrase patterns described on these pages; no text was copied
from them:

- German Wikipedia, [Wikipedia:Anzeichen für KI-generierte Inhalte](https://de.wikipedia.org/wiki/Wikipedia:Anzeichen_f%C3%BCr_KI-generierte_Inhalte)
- English Wikipedia, [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)

## Claude Code

Add a Stop hook to `~/.claude/settings.json` (all projects) or
`.claude/settings.json` (one project):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "schreibwaechter hook claude --locale de-CH",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

What happens when Claude wants to stop:

1. The hook reads the Stop hook JSON from stdin. If `stop_hook_active` is
   true, Claude is already continuing because of this hook, and the hook
   lets it stop. There is at most one rewrite round, so it cannot loop.
2. It takes the last assistant message from `last_assistant_message` when
   the input has that field, otherwise it reads the JSONL file named in
   `transcript_path` and joins the text blocks of the last assistant
   message (sidechain messages from subagents are skipped).
3. It masks code, paths and URLs and checks whether the rest is German by
   counting common German and English function words. Other languages pass.
4. If there are errors (or warnings with `--strict`), it prints
   `{"decision": "block", "reason": "..."}`. The reason lists line, rule,
   message, a short context and the suggestion. Claude then writes the
   answer again. Otherwise it prints nothing and Claude stops.

Configuration is looked up from the `cwd` in the hook input. If the command
is not on the PATH of the shell Claude Code uses, put the full path to the
installed `schreibwaechter` executable into `command`. On errors inside the
linter the hook prints a note to stderr and lets Claude stop.

## Codex

The Codex CLI has hooks (checked with Codex CLI 0.154.0:
`codex features list` shows `hooks` as `stable`). Codex reads
`~/.codex/hooks.json` or `<repo>/.codex/hooks.json` and sends a Stop event
with `stop_hook_active` and `last_assistant_message`. The same command works:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "schreibwaechter hook codex --locale de-CH",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
```

Notes from the [Codex hooks documentation](https://developers.openai.com/codex/hooks):
Codex asks you to review and trust new hooks (`/hooks` in the CLI), Stop
hooks may run for at most 3 seconds (schreibwaechter needs well under one
second), and `commandWindows` can hold a Windows-specific command.

Without hooks, add an instruction to `AGENTS.md` and use the pre-commit hook
below as the enforcing step:

```markdown
## German text
After changing German Markdown or text files, run
`schreibwaechter check <files> --locale de-CH` and fix every error before
you report the task as done. Do not use dashes as punctuation.
```

## Git pre-commit hook

[examples/pre-commit](examples/pre-commit) checks the staged content of
Markdown and text files and skips files that are not German:

```bash
cp examples/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

With the [pre-commit](https://pre-commit.com) framework:

```yaml
repos:
  - repo: https://github.com/beweiskette/schreibwaechter
    rev: v0.1.0
    hooks:
      - id: schreibwaechter
        args: [--locale, de-CH]
```

## Limitations

- The phrase lists are heuristics. A warning is a hint to reread the
  sentence, not proof of AI text. Warnings do not block unless you use
  `--strict`.
- The negative parallelism patterns only look inside one sentence, and an
  abbreviation such as `z. B.` ends the sentence for them.
- Single quotation marks (‹…›, ‚…‘) are not checked. Straight double quotes
  are paired by position, which can go wrong in unusual texts; `fix` then
  leaves the quotes alone and says so.
- Code blocks indented by four spaces are not recognised as code. Use fenced
  code blocks.
- Language detection is a word count. Very short or mixed-language answers
  may be classified wrongly.
- The hook checks only the final assistant message of a turn, not text the
  agent wrote before tool calls.
- Tested: all rules and the hook logic with pytest, the Claude Code hook in
  one live `claude -p` run (the hook blocked, Claude rewrote the answer, the
  second Stop passed), the pre-commit script in a scratch repository. Not
  tested: the Codex hook in a live Codex session (only with synthetic input
  in the documented format), the pre-commit framework integration.

## License

MIT, see [LICENSE](LICENSE).

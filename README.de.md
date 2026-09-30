# schreibwaechter

[English version](README.md)

Ein deterministischer Linter für deutsche Texte, die KI-Agenten schreiben. Er
kennt zwei Varianten: Schweizer Hochdeutsch (`de-CH`, also `ss` statt Eszett
und «Guillemets») und Deutsch aus Deutschland (`de-DE`, Eszett erlaubt,
`„deutsche Anführungszeichen“`). Er läuft als Kommandozeilenwerkzeug, als
Git-Hook vor dem Commit und als Stop-Hook für Claude Code und Codex. Im
Hook-Betrieb muss der Agent eine deutsche Antwort, die gegen die Regeln
verstösst, neu schreiben, bevor er fertig ist.

## Wozu

Agenten, die Deutsch schreiben, zeigen immer dieselben Muster: Gedankenstriche
als Satzzeichen, aufgeblähte Wendungen wie `spielt eine entscheidende Rolle`,
die Figur `nicht nur … sondern auch`, Emojis in Überschriften, Anglizismen
wie `macht Sinn` oder `in 2026`. Wer in der Schweiz schreibt, bekommt dazu
Eszett und deutsche Anführungszeichen, die er nie wollte. Eine Regel im
Prompt hilft wenig, der Agent vergisst sie. Die vorhandenen Werkzeuge
(AntiSlop, defluff, ai-slop-linter) sind auf Englisch ausgelegt, kennen
keine Schweizer Schreibweise und schicken den Text nicht an den Agenten
zurück.

schreibwaechter braucht kein Modell und kein Netz. Dieselbe Eingabe ergibt
immer dieselben Befunde.

## Regeln

| Kennung | Schwere | Variante | Was gefunden wird | `fix` |
|---|---|---|---|---|
| `dash` | Fehler | beide | Geviertstrich `—`, Halbgeviertstrich `–` mit Leerzeichen, ` - ` und ` -- ` zwischen Wörtern, `–` als Aufzählungszeichen | nein |
| `eszett` | Fehler | de-CH | `ß` und `ẞ` | ja |
| `umlaut` | Fehler | beide | Umlaute als `ae`, `oe`, `ue` umschrieben (`fuer`, `koennen`, `Aenderung`) | ja |
| `quotes` | Warnung | beide | Anführungszeichen im falschen Stil (`"…"`, `“…”`, in de-CH auch `„…“`, in de-DE auch `«…»`) | ja |
| `quotes-mixed` | Fehler | beide | mehrere Stile von Anführungszeichen im selben Text | ja |
| `floskel` | Warnung | beide | Floskeln und aufgeblähte Bedeutung aus einer Datendatei | nein |
| `negative-parallelism` | Warnung | beide | `nicht nur … sondern (auch)`, `es geht nicht (nur) um … sondern`, `kein …, sondern ein …` | nein |
| `emoji` | Warnung | beide | Emojis im Fliesstext und vor Überschriften oder Listenpunkten | nein |
| `anglicism` | Warnung | beide | Anglizismen und wörtliche Übersetzungen aus einer Datendatei | nein |

Absichtlich erlaubt sind Bindestriche in Wörtern (`E-Mail`, `Ein- und
Ausgang`), Bis-Striche ohne Leerzeichen in Spannen und Verbindungen
(`2020–2024`, `8–10`, `Bern–Genf`), Frankenbeträge (`Fr. 20.–`), Striche in
leeren Tabellenzellen, Markdown-Aufzählungen, Trennlinien und ein Strich,
der nur als Zeichen erwähnt wird, etwa `(—)`.

Die Regel `umlaut` arbeitet mit einer Liste von Wortstämmen in
`src/schreibwaechter/data/umlaute.json` (`fuer`, `ueber`, `koenn`, `pruef` und
rund 180 weitere). Gemeldet werden nur Wörter mit einem solchen Stamm.
Gewöhnliche Wörter mit `ae`, `oe` oder `ue` wie `aktuell`, `Feuer`, `Israel`,
`Poet` oder `Queue` bleiben unberührt. Familiennamen, die wirklich mit `oe` oder
`ue` geschrieben werden, lassen sich mit einem Ausschalt-Kommentar ausnehmen.

Eine Prüfung auf Dreierreihen gibt es nicht. Eine deterministische Fassung
meldete zu viele Stellen, die in Ordnung waren.

Nie geprüft werden: Codeblöcke mit Zäunen, Inline-Code, `<pre>`- und
`<code>`-Blöcke, HTML-Kommentare und HTML-Tags, URLs, E-Mail-Adressen,
Datei- und Pfadnamen, Linkziele in Markdown, Kommandozeilenoptionen sowie
YAML- oder TOML-Kopfdaten am Dateianfang.

`schreibwaechter rules` zeigt die Liste an.

## Installation

Python 3.11 oder neuer, keine Abhängigkeiten.

```bash
pipx install git+https://github.com/beweiskette/schreibwaechter
# oder aus einem Klon:
git clone https://github.com/beweiskette/schreibwaechter
cd schreibwaechter
python -m pip install .
```

## Schnellstart

```bash
schreibwaechter check README.md docs/ --locale de-CH
cat antwort.md | schreibwaechter check - --locale de-DE --format json
schreibwaechter fix text.md --locale de-CH --diff   # sichere Korrekturen zeigen
schreibwaechter fix text.md --locale de-CH          # und anwenden
```

`check` endet mit 0 ohne Fehler, mit 1 bei Fehlern (mit `--strict` auch bei
Warnungen) und mit 2 bei unlesbaren Dateien oder falscher Konfiguration. In
Ordnern werden `.md`, `.markdown`, `.mdx`, `.txt` und `.rst` gesucht.

`fix` ändert nur, was den Sinn nicht verändern kann: Eszett zu `ss` in
de-CH, `ae`, `oe` und `ue` zurück zu `ä`, `ö` und `ü` in bekannten Wörtern
und Anführungszeichen in den Stil der Variante. Anführungszeichen
werden nur umgestellt, wenn jedes Zeichen im Text ein Gegenstück hat.
Gedankenstriche korrigiert das Werkzeug nie selbst, weil der Satz neu
gebaut werden muss.

Weitere Optionen: `--lang en` für englische Meldungen, `--disable dash,emoji`,
`--only-german` überspringt Dateien, die nicht deutsch sind, `--stdin-name`
gibt der Eingabe über stdin einen Namen, dazu `--no-config` und
`--config PFAD`.

## Beispielausgabe

Für [examples/beispiel.md](examples/beispiel.md) mit `--locale de-CH`:

```text
examples/beispiel.md:6:3: warning [emoji] Emoji «🚀» vor Überschrift oder Listenpunkt. Entfernen.
examples/beispiel.md:8:1: warning [floskel] Floskel «In der heutigen schnelllebigen Welt». Einstieg streichen und mit der Sache beginnen.
examples/beispiel.md:8:88: error [dash] Gedankenstrich als Satzzeichen «—». Satz umbauen: Komma, Doppelpunkt, Klammer oder Punkt.
examples/beispiel.md:10:18: warning [negative-parallelism] Negativer Parallelismus «nicht nur schnell, sondern auch». Die Aussage direkt machen, ohne Gegenfigur.
examples/beispiel.md:12:10: warning [quotes] Anführungszeichen „…“ statt «…» (de-CH). -> «Das macht Sinn»
examples/beispiel.md:12:46: error [quotes-mixed] Verschiedene Anführungszeichen im selben Text („…“, "…"). Einheitlich «…» verwenden.
examples/beispiel.md:12:56: warning [anglicism] Anglizismus «In 2026». «im Jahr 2026» oder nur «2026».
examples/beispiel.md:14:28: error [eszett] Eszett in Schweizer Text: «gemäß» wird «gemäss» geschrieben. -> gemäss
examples/beispiel.md:20:48: error [dash] Gedankenstrich als Satzzeichen « - ». Satz umbauen: Komma, Doppelpunkt, Klammer oder Punkt.
examples/beispiel.md:22:1: warning [floskel] Floskel «## Fazit». Kein Fazit-Abschnitt; das Wichtigste gehört an den Anfang.
...
4 Fehler, 12 Warnungen (de-CH)
```

Der Strich im Codeblock, die Striche in der URL und in den Kopfdaten der
Datei werden nicht gemeldet. `--format json` liefert dieselben Befunde mit
Position, Zeile, Spalte, Fundstelle, deutscher und englischer Meldung,
Vorschlag und der Kennung des Listeneintrags.

## Konfiguration

schreibwaechter liest `.schreibwaechter.toml` im aktuellen Ordner oder im
nächsten übergeordneten Ordner, der eine hat. `SCHREIBWAECHTER_CONFIG` zeigt
auf eine bestimmte Datei. Optionen auf der Kommandozeile gehen der Datei
vor. Eine kommentierte Vorlage liegt in
[examples/schreibwaechter.toml](examples/schreibwaechter.toml).

```toml
locale = "de-CH"        # oder "de-DE" (Standard)
lang = "de"             # Sprache der Meldungen: "de" oder "en"
strict = false          # true: auch Warnungen lassen check scheitern
disable = ["anglicism"]
# enable = ["dash", "eszett"]   # nur diese Regeln

[severity]
floskel = "error"

[words]
floskeln = ["Synergieeffekte heben"]
anglicisms = []
floskeln_files = ["team-floskeln.json"]
anglicisms_files = []
ignore = ["nahtlos", "fuellwort-verbindung"]   # Kennungen oder genaue Wendungen
```

### Kommentare im Text

```markdown
<!-- schreibwaechter: disable dash -->
Text, in dem Striche erlaubt sind.
<!-- schreibwaechter: enable dash -->

<!-- schreibwaechter: disable-next-line eszett -->
Straße (ein zitierter Strassenname)

Eine Zeile <!-- schreibwaechter: disable-line -->
```

`disable` und `enable` ohne Kennung gelten für alle Regeln. `enable dash`
hebt nur ein früheres `disable dash` auf, kein `disable` für alle Regeln.

### Wortlisten

Die Listen liegen in
[src/schreibwaechter/data/floskeln.json](src/schreibwaechter/data/floskeln.json)
und [anglizismen.json](src/schreibwaechter/data/anglizismen.json). Jeder
Eintrag hat eine `id`, ein `pattern` sowie `hint_de` und `hint_en`;
`category` und `severity` sind freiwillig. Eigene Dateien haben dasselbe
Format. Eine einfache Liste von Zeichenketten geht auch, sie gilt dann als
wörtliche Wendungen.

Regeln für Muster: regulärer Ausdruck von Python, Gross- und Kleinschreibung
egal, mehrzeilig. Der Text wird mit `ss` anstelle von Eszett verglichen,
Muster also mit `ss` schreiben. Ein Leerzeichen passt auf beliebig viel
Leerraum (ausser innerhalb von `[...]`). Wortgrenzen setzt das Werkzeug
selbst um das ganze Muster.

Die Listen geben die Muster dieser Seiten in eigenen Worten wieder, kopiert
wurde nichts:

- Deutsche Wikipedia, [Wikipedia:Anzeichen für KI-generierte Inhalte](https://de.wikipedia.org/wiki/Wikipedia:Anzeichen_f%C3%BCr_KI-generierte_Inhalte)
- Englische Wikipedia, [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)

## Claude Code

Einen Stop-Hook in `~/.claude/settings.json` (alle Projekte) oder in
`.claude/settings.json` (ein Projekt) eintragen:

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

Das passiert, wenn Claude aufhören will:

1. Der Hook liest das JSON des Stop-Hooks von stdin. Steht
   `stop_hook_active` auf true, arbeitet Claude bereits wegen dieses Hooks
   weiter, und der Hook lässt es aufhören. Es gibt höchstens eine Runde zum
   Umschreiben, eine Schleife ist ausgeschlossen.
2. Er nimmt die letzte Antwort aus `last_assistant_message`, falls die
   Eingabe dieses Feld hat. Sonst liest er die JSONL-Datei aus
   `transcript_path` und fügt die Textblöcke der letzten Antwort zusammen.
   Nachrichten von Unteragenten überspringt er.
3. Er blendet Code, Pfade und URLs aus und prüft am Rest, ob er deutsch ist.
   Dazu zählt er häufige deutsche und englische Funktionswörter. Andere
   Sprachen gehen durch.
4. Bei Fehlern (mit `--strict` auch bei Warnungen) gibt er
   `{"decision": "block", "reason": "..."}` aus. Der Grund nennt Zeile,
   Regel, Meldung, einen kurzen Ausschnitt und den Vorschlag. Claude
   schreibt die Antwort dann neu. Sonst gibt er nichts aus, und Claude hört
   auf.

Die Konfiguration sucht der Hook ab dem `cwd` aus der Eingabe. Wenn der
Befehl nicht im Suchpfad der Shell liegt, die Claude Code benutzt, gehört
der volle Pfad zur installierten Programmdatei in `command`. Scheitert der
Linter selbst, schreibt der Hook einen Hinweis auf stderr und lässt Claude
aufhören.

## Codex

Die Codex CLI hat Hooks (geprüft mit Codex CLI 0.154.0: `codex features
list` zeigt `hooks` als `stable`). Codex liest `~/.codex/hooks.json` oder
`<repo>/.codex/hooks.json` und schickt beim Stop-Ereignis unter anderem
`stop_hook_active` und `last_assistant_message`. Derselbe Befehl
funktioniert:

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

Aus der [Codex-Dokumentation zu Hooks](https://developers.openai.com/codex/hooks):
Codex verlangt, dass man neue Hooks prüft und freigibt (`/hooks` in der
CLI). Ein Stop-Hook darf höchstens 3 Sekunden laufen; schreibwaechter
braucht deutlich weniger als eine Sekunde. Im Feld `commandWindows` kann ein
eigener Befehl für Windows stehen.

Ohne Hooks hilft eine Anweisung in `AGENTS.md`, durchgesetzt wird sie dann
mit dem Git-Hook weiter unten:

```markdown
## Deutsche Texte
Nach Änderungen an deutschen Markdown- oder Textdateien
`schreibwaechter check <dateien> --locale de-CH` ausführen und jeden Fehler
beheben, bevor die Aufgabe als erledigt gemeldet wird. Keine Gedankenstriche
als Satzzeichen.
```

## Git-Hook vor dem Commit

[examples/pre-commit](examples/pre-commit) prüft den vorgemerkten Inhalt von
Markdown- und Textdateien und überspringt Dateien, die nicht deutsch sind:

```bash
cp examples/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Mit dem Werkzeug [pre-commit](https://pre-commit.com):

```yaml
repos:
  - repo: https://github.com/beweiskette/schreibwaechter
    rev: v0.2.1
    hooks:
      - id: schreibwaechter
        args: [--locale, de-CH]
```

## Grenzen

- Die Wortlisten sind Heuristiken. Eine Warnung ist ein Anlass, den Satz
  noch einmal zu lesen, kein Beweis für KI-Text. Warnungen blockieren nur
  mit `--strict`.
- Die Muster für negative Parallelismen suchen nur innerhalb eines Satzes,
  und eine Abkürzung wie `z. B.` beendet für sie den Satz.
- Einfache Anführungszeichen (`‹…›`, `‚…‘`) werden nicht geprüft. Gerade
  doppelte Anführungszeichen werden nach ihrer Stellung gepaart, was in
  ungewöhnlichen Texten schiefgehen kann. `fix` lässt die Anführungszeichen
  dann stehen und meldet das.
- Mit vier Leerzeichen eingerückte Codeblöcke erkennt das Werkzeug nicht als
  Code. Codeblöcke mit Zäunen verwenden.
- Die Spracherkennung zählt Wörter. Sehr kurze oder gemischtsprachige
  Antworten können falsch eingeordnet werden.
- Der Hook prüft nur die letzte Antwort eines Durchgangs, keinen Text, den
  der Agent vor Werkzeugaufrufen geschrieben hat.
- Getestet sind alle Regeln und die Hook-Logik mit pytest, der Hook für
  Claude Code in einem echten Lauf mit `claude -p` (der Hook blockierte,
  Claude schrieb die Antwort neu, der zweite Stop ging durch) und das Skript
  für den Git-Hook in einem Testrepository. Nicht getestet sind der Hook in
  einer echten Codex-Sitzung (nur mit nachgebauter Eingabe im dokumentierten
  Format) und die Einbindung über das Werkzeug pre-commit.

## Lizenz

MIT, siehe [LICENSE](LICENSE).

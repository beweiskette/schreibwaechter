"""Finding type and rule metadata shared by all modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

ERROR = "error"
WARNING = "warning"
SEVERITIES = (ERROR, WARNING)


@dataclass(frozen=True)
class RuleInfo:
    id: str
    severity: str
    title_de: str
    title_en: str
    locales: tuple[str, ...] = ("de-CH", "de-DE")
    fixable: bool = False


RULES: dict[str, RuleInfo] = {
    info.id: info
    for info in (
        RuleInfo("dash", ERROR, "Gedankenstrich als Satzzeichen", "Dash used as punctuation"),
        RuleInfo("eszett", ERROR, "Eszett in Schweizer Text", "Eszett in Swiss text",
                 locales=("de-CH",), fixable=True),
        RuleInfo("umlaut", ERROR, "Umlaut als ae, oe oder ue umschrieben",
                 "Umlaut spelled out as ae, oe or ue", fixable=True),
        RuleInfo("quotes", WARNING, "Anführungszeichen im falschen Stil",
                 "Quotation marks in the wrong style", fixable=True),
        RuleInfo("quotes-mixed", ERROR, "Gemischte Anführungszeichen",
                 "Mixed quotation mark styles", fixable=True),
        RuleInfo("floskel", WARNING, "Floskel oder aufgeblähte Bedeutung",
                 "Stock phrase or inflated significance"),
        RuleInfo("negative-parallelism", WARNING, "Negativer Parallelismus",
                 "Negative parallelism"),
        RuleInfo("emoji", WARNING, "Emoji im Fliesstext", "Emoji in prose"),
        RuleInfo("anglicism", WARNING, "Anglizismus oder wörtliche Übersetzung",
                 "Anglicism or literal translation"),
    )
}


@dataclass
class Finding:
    rule: str
    severity: str
    offset: int
    length: int
    line: int
    column: int
    text: str
    message_de: str
    message_en: str
    suggestion: str | None = None
    entry: str | None = None
    path: str | None = field(default=None, compare=False)

    def message(self, lang: str = "de") -> str:
        return self.message_en if lang == "en" else self.message_de

    def to_dict(self) -> dict:
        data = asdict(self)
        data["message"] = {"de": data.pop("message_de"), "en": data.pop("message_en")}
        return data

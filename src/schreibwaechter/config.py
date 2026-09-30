"""Configuration from ``.schreibwaechter.toml`` and command line flags."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .findings import RULES, SEVERITIES
from .wordlists import Entry, entries_from_data, load_file, phrases_to_entries

CONFIG_NAME = ".schreibwaechter.toml"
LOCALES = ("de-CH", "de-DE")
LANGS = ("de", "en")
DEFAULT_LOCALE = "de-DE"


class ConfigError(ValueError):
    """Raised for invalid configuration values."""


@dataclass
class Config:
    locale: str = DEFAULT_LOCALE
    lang: str = "de"
    strict: bool = False
    disabled: set[str] = field(default_factory=set)
    enabled: set[str] | None = None
    severity: dict[str, str] = field(default_factory=dict)
    extra_floskeln: list[Entry] = field(default_factory=list)
    extra_anglicisms: list[Entry] = field(default_factory=list)
    ignore: set[str] = field(default_factory=set)
    source: Path | None = None

    def rule_active(self, rule: str) -> bool:
        info = RULES[rule]
        if self.locale not in info.locales:
            return False
        if rule in self.disabled:
            return False
        if self.enabled is not None and rule not in self.enabled:
            return False
        return True

    def severity_of(self, rule: str, default: str | None = None) -> str:
        return self.severity.get(rule) or default or RULES[rule].severity


def _check_rules(names: list[str], where: str) -> set[str]:
    result = set()
    for name in names:
        if name not in RULES:
            known = ", ".join(RULES)
            raise ConfigError(f"{where}: unknown rule {name!r} (known: {known})")
        result.add(name)
    return result


def check_locale(locale: str) -> str:
    if locale not in LOCALES:
        raise ConfigError(f"unknown locale {locale!r}, use one of {', '.join(LOCALES)}")
    return locale


def find_config(start: Path) -> Path | None:
    env = os.environ.get("SCHREIBWAECHTER_CONFIG")
    if env:
        return Path(env)
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def _string_list(value: object, where: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{where}: expected a list of strings")
    return list(value)


def load_config(path: Path) -> Config:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    return config_from_dict(data, path)


def config_from_dict(data: dict, path: Path | None = None) -> Config:
    where = str(path) if path else "config"
    config = Config(source=path)
    if "locale" in data:
        config.locale = check_locale(str(data["locale"]))
    if "lang" in data:
        if data["lang"] not in LANGS:
            raise ConfigError(f"{where}: lang must be 'de' or 'en'")
        config.lang = data["lang"]
    config.strict = bool(data.get("strict", False))
    config.disabled = _check_rules(_string_list(data.get("disable"), where), where)
    if "enable" in data:
        config.enabled = _check_rules(_string_list(data.get("enable"), where), where)
    for rule, severity in (data.get("severity") or {}).items():
        _check_rules([rule], where)
        if severity not in SEVERITIES:
            raise ConfigError(f"{where}: severity of {rule} must be 'error' or 'warning'")
        config.severity[rule] = severity
    words = data.get("words") or {}
    base = path.parent if path else Path.cwd()
    config.extra_floskeln = phrases_to_entries(
        _string_list(words.get("floskeln"), where), where
    )
    config.extra_anglicisms = phrases_to_entries(
        _string_list(words.get("anglicisms"), where), where
    )
    for name in _string_list(words.get("floskeln_files"), where):
        file_path = base / name
        config.extra_floskeln += entries_from_data(load_file(file_path), str(file_path))
    for name in _string_list(words.get("anglicisms_files"), where):
        file_path = base / name
        config.extra_anglicisms += entries_from_data(load_file(file_path), str(file_path))
    config.ignore = {item.lower() for item in _string_list(words.get("ignore"), where)}
    return config


def resolve_config(
    config_path: str | None, no_config: bool, start: Path | None = None
) -> Config:
    if no_config:
        return Config()
    path = Path(config_path) if config_path else find_config(start or Path.cwd())
    if path is None:
        return Config()
    return load_config(path)

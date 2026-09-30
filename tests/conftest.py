import pytest

from schreibwaechter.config import Config
from schreibwaechter.linter import lint_text


@pytest.fixture
def lint():
    def run(text, locale="de-CH", **kwargs):
        return lint_text(text, Config(locale=locale, **kwargs))

    return run


def rules_of(findings, rule=None):
    ids = [f.rule for f in findings]
    return [r for r in ids if r == rule] if rule else ids

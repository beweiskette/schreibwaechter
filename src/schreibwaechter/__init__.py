"""schreibwaechter: deterministic linter for German prose written by AI agents."""

__version__ = "0.2.1"

from .config import Config  # noqa: E402
from .fixer import fix_text  # noqa: E402
from .linter import lint_text  # noqa: E402

__all__ = ["Config", "fix_text", "lint_text", "__version__"]

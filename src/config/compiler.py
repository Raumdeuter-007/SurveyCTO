"""
Compiler constants: sheet headers and column widths.
"""

from __future__ import annotations
import sys
from pathlib import Path

from openpyxl.styles import Alignment, Font


SETTINGS_HEADERS = [
    "form_title", "form_id", "version", "default_language",
    "public_key", "submission_url",
]

PROJECT_ROOT: Path = Path()
if getattr(sys, 'frozen', False):
    # Running inside PyInstaller bundle
    PROJECT_ROOT = Path(sys.executable).parent
else:
    # Running normally
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

FIXED_ROWS_PATH:  Path = PROJECT_ROOT / "prompts" / "fixed_rows.yaml"

_WRAP        = Alignment(wrap_text=True, vertical="top")
_HEADER_FONT = Font(bold=True, name="Calibri")
_CELL_FONT   = Font(name="Calibri")


# ---------------------------------------------------------------------------
# Column width maps (openpyxl character units, approx px/7)
# ---------------------------------------------------------------------------

SURVEY_WIDTHS: dict[str, float] = {
    "type":          34,
    "name":          34,
    "appearance":    50,
    "relevance":     50,
    "required":      50,
    "constraint":    50,
    "calculation":   36,
    "choice_filter": 36,
    "read only":     36,
    "default":       36,
    "repeat_count":  36,
    "minimum_seconds": 36,
    "publishable":   36,
}
SURVEY_PREFIX_WIDTHS: dict[str, float] = {
    "label:":              71,
    "hint:":               50,
    "constraint message:": 50,
    "media:image:":        36,
}

CHOICES_WIDTHS: dict[str, float] = {
    "list_name": 19,
    "value":     19,
    "filter":    37,
}

CHOICES_PREFIX_WIDTHS: dict[str, float] = {
    "label:": 32,
}
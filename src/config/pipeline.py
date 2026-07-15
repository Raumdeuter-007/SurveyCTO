"""
Pipeline constants: model, paths, and delimiters.
"""

from __future__ import annotations

from pathlib import Path
import re

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

DEFAULT_MODEL:    str  = "gemini-2.5-flash-lite"
MODULE_DELIMITER: str  = "===MODULE==="
PROMPT_PATH:      Path = PROJECT_ROOT / "prompts" / "parse_module.yaml"

_JSON_FENCE_RE: re.Pattern[str] = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
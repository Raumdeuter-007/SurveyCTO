"""
Pipeline constants: model, paths, and delimiters.
"""

from __future__ import annotations

from pathlib import Path
from src.config.compiler import PROJECT_ROOT
import re

DEFAULT_MODEL:    str  = "gemini-3.6-flash"
MODULE_DELIMITER: str  = "===MODULE==="
PROMPT_PATH:      Path = PROJECT_ROOT / "prompts" / "parse_module.yaml"

_JSON_FENCE_RE: re.Pattern[str] = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
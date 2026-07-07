"""
Stage 1: Split a .docx into raw text modules using the ===MODULE=== delimiter.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

DELIMITER = "===MODULE==="


@dataclass
class RawModule:
    index: int
    text: str
    lines: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.lines:
            self.lines = [l for l in self.text.splitlines() if l.strip()]


def _docx_to_text(docx_path: Path) -> str:
    """Convert .docx to plain text via pandoc."""
    result = subprocess.run(
        ["pandoc", "-t", "plain", "--wrap=none", str(docx_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def split_document(docx_path: Path) -> list[RawModule]:
    """
    Parse a .docx file and split it into RawModules on ===MODULE=== delimiters.

    Args:
        docx_path: Path to the .docx file.

    Returns:
        List of RawModule, one per section between delimiters.
        The preamble before the first delimiter (if any) is discarded.

    Raises:
        FileNotFoundError: if docx_path does not exist.
        subprocess.CalledProcessError: if pandoc fails.
        ValueError: if no delimiter found in document.
    """
    if not docx_path.exists():
        raise FileNotFoundError(docx_path)

    raw_text = _docx_to_text(docx_path)
    return split_text(raw_text)


def split_text(text: str) -> list[RawModule]:
    """
    Split plain text on ===MODULE=== delimiters.
    Exposed separately so it can be tested without a real .docx.

    Raises:
        ValueError: if no delimiter found.
    """
    parts = text.split(DELIMITER)

    # parts[0] is the preamble before the first delimiter — discard
    module_parts = parts[1:]

    if not module_parts:
        raise ValueError(f"No '{DELIMITER}' delimiter found in document.")

    modules = []
    for i, part in enumerate(module_parts):
        stripped = part.strip()
        if stripped:
            modules.append(RawModule(index=i, text=stripped))

    return modules
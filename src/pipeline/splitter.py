"""
Stage 1: Split a .docx into raw text modules using the ===MODULE=== delimiter.
Uses python-docx to extract text directly from paragraphs and table cells.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.document import Document as DocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph

DELIMITER = "===MODULE==="


@dataclass
class RawModule:
    index: int
    text: str


def _iter_blocks(doc: DocumentType):
    """Yield top-level paragraphs and tables in document order."""
    for block in doc.element.body:
        tag = block.tag.split("}")[-1]
        if tag == "p":
            yield Paragraph(block, doc)
        elif tag == "tbl":
            yield Table(block, doc)


def _docx_to_text(docx_path: Path) -> str:
    """Extract plain text from paragraphs and table cells in document order."""
    doc = Document(str(docx_path))
    chunks: list[str] = []

    for block in _iter_blocks(doc):
        if isinstance(block, Paragraph):
            t = block.text.strip()
            if t:
                chunks.append(t)
        elif isinstance(block, Table):
            for row in block.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        t = para.text.strip()
                        if t:
                            chunks.append(t)

    return "\n".join(chunks)


def _clean(text: str) -> str:
    """Collapse runs of whitespace into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def split_document(docx_path: Path) -> list[RawModule]:
    if not docx_path.exists():
        raise FileNotFoundError(docx_path)
    return split_text(_docx_to_text(docx_path))


def split_text(text: str) -> list[RawModule]:
    parts = text.split(DELIMITER)
    module_parts = parts

    if not module_parts:
        raise ValueError(f"No '{DELIMITER}' delimiter found in document.")

    return [
        RawModule(index=i, text=_clean(part))
        for i, part in enumerate(module_parts)
        if part.strip()
    ]
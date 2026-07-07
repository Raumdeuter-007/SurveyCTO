"""Tests for pipeline/splitter.py — no .docx required."""

import pytest
from pipeline.splitter import split_text, RawModule, DELIMITER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def doc(*sections: str) -> str:
    """Join sections with the delimiter, with an optional preamble."""
    return DELIMITER.join(["preamble\n"] + list(sections))


# ---------------------------------------------------------------------------
# Basic splitting
# ---------------------------------------------------------------------------

def test_single_module():
    text = doc("Q1. What is your name?")
    modules = split_text(text)
    assert len(modules) == 1
    assert "Q1. What is your name?" in modules[0].text


def test_multiple_modules():
    text = doc("Module A content", "Module B content", "Module C content")
    modules = split_text(text)
    assert len(modules) == 3


def test_module_indices_are_zero_based():
    text = doc("A", "B", "C")
    modules = split_text(text)
    assert [m.index for m in modules] == [0, 1, 2]


def test_preamble_is_discarded():
    text = "This is preamble text\n" + DELIMITER + "\nActual module content"
    modules = split_text(text)
    assert len(modules) == 1
    assert "preamble" not in modules[0].text.lower()


def test_text_is_stripped():
    text = DELIMITER + "\n\n   Some content   \n\n"
    modules = split_text(text)
    assert modules[0].text == "Some content"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_no_delimiter_raises():
    with pytest.raises(ValueError, match="No '===MODULE===' delimiter found"):
        split_text("This document has no delimiter at all.")


def test_empty_modules_are_skipped():
    # Delimiter followed by whitespace only, then a real module
    text = DELIMITER + "\n   \n" + DELIMITER + "\nReal content"
    modules = split_text(text)
    assert len(modules) == 1
    assert modules[0].text == "Real content"


def test_multiline_module_content():
    content = "Q1. Age?\na) Under 18\nb) 18-35\nc) 36+"
    text = DELIMITER + "\n" + content
    modules = split_text(text)
    assert modules[0].text == content


def test_lines_populated():
    text = DELIMITER + "\nLine one\nLine two\n\nLine three"
    modules = split_text(text)
    # blank lines filtered out
    assert modules[0].lines == ["Line one", "Line two", "Line three"]


def test_rawmodule_dataclass():
    m = RawModule(index=0, text="hello\nworld")
    assert m.index == 0
    assert m.lines == ["hello", "world"]
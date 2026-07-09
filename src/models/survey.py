"""
Dataclasses representing parsed SurveyCTO survey and choice rows.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SurveyRow:
    # Language-independent fixed fields
    type: str
    name: str
    appearance: str
    relevance: str
    required: str
    constraint: str
    calculation: str
    choice_filter: str
    read_only: str
    default: str
    repeat_count: str
    minimum_seconds: str
    publishable: str

    # Language-dependent dynamic fields
    labels: dict[str, str] = field(default_factory=dict)              # "label:english" -> "..."
    hints: dict[str, str] = field(default_factory=dict)               # "hint:english" -> "..."
    constraint_messages: dict[str, str] = field(default_factory=dict) # "constraint message:english" -> "..."
    media_images: dict[str, str] = field(default_factory=dict)        # "media:image:english" -> "..."


@dataclass
class ChoiceRow:
    list_name: str
    value: int
    filter: int | None
    labels: dict[str, str] = field(default_factory=dict)              # "label:english" -> "..."


@dataclass
class ModuleOutput:
    index: int
    survey_rows: list[SurveyRow]
    choice_rows: list[ChoiceRow]
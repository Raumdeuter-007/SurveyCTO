"""
Stage 3: Compile all ModuleOutputs into a SurveyCTO-ready .xlsx file.

Sheets produced:
    survey   — all survey rows from all modules, with blank separator rows between modules
    choices  — all choice rows from all modules, with blank separator rows between lists
    settings — header row only, values left blank for manual entry
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from models.survey import ModuleOutput, SurveyRow, ChoiceRow
from utils.logger import get_logger

log = get_logger(__name__)

SETTINGS_HEADERS = [
    "form_title", "form_id", "version", "default_language",
    "public_key", "submission_url",
]


# ---------------------------------------------------------------------------
# Column resolution
# ---------------------------------------------------------------------------

def _resolve_survey_headers(outputs: list[ModuleOutput]) -> list[str]:
    """
    Build the canonical survey sheet column order from the first module
    that has survey rows. Column order follows the prompt spec:
    type, name, label:*, appearance, relevance, required, hint:*,
    constraint, constraint message:*, calculation, choice_filter,
    read only, default, repeat_count, media:image:*, minimum_seconds, publishable
    """
    for output in outputs:
        if output.survey_rows:
            row = output.survey_rows[0]
            headers = (
                ["type", "name"]
                + sorted(row.labels.keys())
                + ["appearance", "relevance", "required"]
                + sorted(row.hints.keys())
                + ["constraint"]
                + sorted(row.constraint_messages.keys())
                + ["calculation", "choice_filter", "read only", "default",
                   "repeat_count"]
                + sorted(row.media_images.keys())
                + ["minimum_seconds", "publishable"]
            )
            return headers
    return ["type", "name", "label:english", "appearance", "relevance",
            "required", "constraint", "calculation", "choice_filter",
            "read only", "default", "repeat_count", "minimum_seconds", "publishable"]


def _resolve_choices_headers(outputs: list[ModuleOutput]) -> list[str]:
    for output in outputs:
        if output.choice_rows:
            row = output.choice_rows[0]
            return ["list_name", "value"] + sorted(row.labels.keys()) + ["filter"]
    return ["list_name", "value", "label:english", "filter"]


# ---------------------------------------------------------------------------
# Row serialization
# ---------------------------------------------------------------------------

def _survey_row_to_list(row: SurveyRow, headers: list[str]) -> list[str]:
    mapping: dict[str, str] = {
        "type": row.type,
        "name": row.name,
        "appearance": row.appearance,
        "relevance": row.relevance,
        "required": row.required,
        "constraint": row.constraint,
        "calculation": row.calculation,
        "choice_filter": row.choice_filter,
        "read only": row.read_only,
        "default": row.default,
        "repeat_count": row.repeat_count,
        "minimum_seconds": row.minimum_seconds,
        "publishable": row.publishable,
        **row.labels,
        **row.hints,
        **row.constraint_messages,
        **row.media_images,
    }
    return [mapping.get(h, "") for h in headers]


def _choice_row_to_list(row: ChoiceRow, headers: list[str]) -> list[str]:
    mapping: dict = {
        "list_name": row.list_name,
        "value": row.value,
        "filter": row.filter if row.filter is not None else "",
        **row.labels,
    }
    return [mapping.get(h, "") for h in headers]


# ---------------------------------------------------------------------------
# Sheet writers
# ---------------------------------------------------------------------------

def _write_survey_sheet(ws, outputs: list[ModuleOutput], headers: list[str]) -> None:
    ws.append(headers)
    _bold_row(ws, 1)

    # for row in fixed.survey_start:
    #     ws.append(_survey_row_to_list(row, headers))
    # ws.append([""] * len(headers))

    for output in outputs:
        for row in output.survey_rows:
            ws.append(_survey_row_to_list(row, headers))
        ws.append([""] * len(headers))  # blank separator between modules

    # for row in fixed.survey_end:
    #     ws.append(_survey_row_to_list(row, headers))


def _deduplicate_choices(outputs: list[ModuleOutput]) -> list[ChoiceRow]:
    """
    Merge choice rows from all modules, deduplicating by (list_name, value).
    First occurrence wins. Order: by list_name first appearance, then value.
    """
    seen: set[tuple[str, int]] = set()
    result: list[ChoiceRow] = []
    for output in outputs:
        for row in output.choice_rows:
            key = (row.list_name, row.value)
            if key not in seen:
                seen.add(key)
                result.append(row)
    return result


def _write_choices_sheet(ws, outputs: list[ModuleOutput], headers: list[str]) -> None:
    ws.append(headers)
    _bold_row(ws, 1)

    # for row in fixed.fixed_choices:
    #     ws.append(_choice_row_to_list(row, headers))
    # ws.append([""] * len(headers))

    all_choices = _deduplicate_choices(outputs)
    current_list: str | None = None
    for row in all_choices:
        if row.list_name != current_list:
            if current_list is not None:
                ws.append([""] * len(headers))  # blank between lists
            current_list = row.list_name
        ws.append(_choice_row_to_list(row, headers))
    if current_list is not None:
        ws.append([""] * len(headers))


def _write_settings_sheet(ws) -> None:
    ws.append(SETTINGS_HEADERS)
    _bold_row(ws, 1)
    ws.append([""] * len(SETTINGS_HEADERS))  # blank row for manual entry


def _bold_row(ws, row_num: int) -> None:
    for cell in ws[row_num]:
        cell.font = Font(bold=True, name="Arial")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def compile_outputs(
    outputs: list[ModuleOutput],
    docx_path: Path,
    out_dir: Path | None = None,
) -> Path:
    """
    Compile all ModuleOutputs into a SurveyCTO .xlsx file.

    Args:
        outputs: List of ModuleOutput from parser.parse_all_modules().
        docx_path: Original .docx path — used to derive the output filename.
        out_dir: Directory to write the .xlsx into. Defaults to docx_path's parent.

    Returns:
        Path to the written .xlsx file.
    """
    out_dir = out_dir or docx_path.parent
    out_path = out_dir / (docx_path.stem + ".xlsx")

    # fixed = load_fixed_rows()
    survey_headers = _resolve_survey_headers(outputs)
    choices_headers = _resolve_choices_headers(outputs)

    wb = Workbook()

    ws_survey = wb.create_sheet("survey")
    _write_survey_sheet(ws_survey, outputs, survey_headers)

    ws_choices = wb.create_sheet("choices")
    _write_choices_sheet(ws_choices, outputs, choices_headers)

    ws_settings = wb.create_sheet("settings")
    _write_settings_sheet(ws_settings)

    wb.save(out_path)
    log.info(f"Compiled {len(outputs)} modules → {out_path}")
    return out_path
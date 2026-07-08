"""
Stage 2: Send each RawModule to the LLM and parse the response
into ModuleOutput dataclasses.

LLM response format (three markdown-headed blocks):
    ### SURVEY
    <CSV>
    ### CHOICES
    <CSV>
    ### CHOICE_LIST_MANIFEST
    <JSON>
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
import yaml

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from models.survey import ChoiceRow, ModuleOutput, SurveyRow
from pipeline.splitter import RawModule
from utils.logger import get_logger

log = get_logger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash-lite"

BLOCK_PATTERN = re.compile(
    r"###\s*SURVEY\s*(.*?)###\s*CHOICES\s*(.*?)###\s*CHOICE_LIST_MANIFEST\s*(.*)",
    re.DOTALL | re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def _load_prompt(prompt_path: Path) -> str:
    import yaml
    data = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    return data["system"]


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_llm(llm: ChatGoogleGenerativeAI, system_prompt: str, user_prompt: str) -> str:
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    return str(response.content)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_blocks(response: str) -> tuple[str, str, str]:
    match = BLOCK_PATTERN.search(response)
    if not match:
        raise ValueError(
            "LLM response did not contain expected "
            "### SURVEY / ### CHOICES / ### CHOICE_LIST_MANIFEST blocks."
        )
    return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()


def _parse_survey_csv(csv_text: str) -> list[SurveyRow]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for raw in reader:
        row = {k.strip(): (v or "").strip() for k, v in raw.items()}

        labels, hints, constraint_messages, media_images = {}, {}, {}, {}
        for key, val in row.items():
            lk = key.lower()
            if lk.startswith("label:"):
                labels[key] = val
            elif lk.startswith("hint:"):
                hints[key] = val
            elif lk.startswith("constraint message:"):
                constraint_messages[key] = val
            elif lk.startswith("media:image:"):
                media_images[key] = val

        rows.append(SurveyRow(
            type=row.get("type", ""),
            name=row.get("name", ""),
            appearance=row.get("appearance", ""),
            relevance=row.get("relevance", ""),
            required=row.get("required", ""),
            constraint=row.get("constraint", ""),
            calculation=row.get("calculation", ""),
            choice_filter=row.get("choice_filter", ""),
            read_only=row.get("read only", ""),
            default=row.get("default", ""),
            repeat_count=row.get("repeat_count", ""),
            minimum_seconds=row.get("minimum_seconds", ""),
            publishable=row.get("publishable", ""),
            labels=labels,
            hints=hints,
            constraint_messages=constraint_messages,
            media_images=media_images,
        ))
    return rows


def _parse_choices_csv(csv_text: str) -> list[ChoiceRow]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for raw in reader:
        row = {k.strip(): (v or "").strip() for k, v in raw.items()}
        if not row.get("list_name") and not row.get("name"):
            continue
        labels = {k: v for k, v in row.items() if k.lower().startswith("label:")}
        rows.append(ChoiceRow(
            list_name=row.get("list_name", ""),
            name=row.get("name", ""),
            labels=labels,
        ))
    return rows


def _parse_manifest(json_text: str) -> dict:
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"CHOICE_LIST_MANIFEST is not valid JSON: {e}") from e


# ---------------------------------------------------------------------------
# Per-module call
# ---------------------------------------------------------------------------

def _build_user_prompt(module: RawModule, manifest: dict) -> str:
    return (
        f"EXISTING CHOICE LISTS:\n{json.dumps(manifest, ensure_ascii=False)}\n\n"
        f"MODULE TEXT:\n{module.text}"
    )


def parse_module(
    module: RawModule,
    llm: ChatGoogleGenerativeAI,
    system_prompt: str,
    manifest: dict,
) -> ModuleOutput:
    """
    Send one RawModule to the LLM and return a parsed ModuleOutput.

    Raises:
        ValueError: On malformed LLM response (halts pipeline).
        To SKIP instead of halting, wrap the call in:

            try:
                output = parse_module(...)
            except (ValueError, Exception) as e:
                log.error(f"Skipping module {module.index}: {e}")
                continue
    """
    log.info(f"Parsing module {module.index}...")
    user_prompt = _build_user_prompt(module, manifest)
    response = _call_llm(llm, system_prompt, user_prompt)

    survey_csv, choices_csv, manifest_json = _parse_blocks(response)
    survey_rows = _parse_survey_csv(survey_csv)
    choice_rows = _parse_choices_csv(choices_csv)
    updated_manifest = _parse_manifest(manifest_json)

    log.info(f"Module {module.index}: {len(survey_rows)} survey rows, {len(choice_rows)} choice rows.")
    return ModuleOutput(
        index=module.index,
        survey_rows=survey_rows,
        choice_rows=choice_rows,
        manifest=updated_manifest,
    )


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def parse_all_modules(
    modules: list[RawModule],
    api_key: str,
    prompt_path: Path,
    model: str = DEFAULT_MODEL,
) -> list[ModuleOutput]:
    """
    Loop over all modules, chaining the manifest between calls.

    Args:
        modules: Output of splitter.split_document().
        api_key: Gemini API key.
        prompt_path: Path to prompts/parse_module.txt.
        model: LLM model string. Defaults to gemini-2.5-flash-lite.

    Returns:
        List of ModuleOutput in module order.

    Raises:
        ValueError: On first module that fails to parse (halts pipeline).
        To skip a failing module instead, see parse_module() docstring.
    """
    llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    system_prompt = _load_prompt(prompt_path)

    manifest: dict = {}
    outputs: list[ModuleOutput] = []

    for module in modules:
        output = parse_module(module, llm, system_prompt, manifest)
        manifest = output.manifest
        outputs.append(output)

    log.info(f"Parsed {len(outputs)} modules successfully.")
    return outputs
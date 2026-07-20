"""
Stage 2: Send each RawModule to the LLM and parse the response
into ModuleOutput dataclasses.

LLM response format (single JSON block):
    ```json
    {
        "survey": [ <SurveyRow>, ... ],
        "choices": [ <ChoiceRow>, ... ]
    }
    ```
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from collections.abc import Callable

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from models.survey import ChoiceRow, ModuleOutput, SurveyRow
from pipeline.splitter import RawModule
from utils.logger import get_logger
from config.pipeline import DEFAULT_MODEL, _JSON_FENCE_RE

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def _load_prompt_template(prompt_path: Path) -> str:
    data = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    return data["system"]


def _render_prompt(
    template: str,
    languages: list[str],
    known_fields: list[str],
    choice_manifest: list[dict],
) -> str:
    return (
        template
        .replace("{languages}", json.dumps(languages))
        .replace("{known_fields}", json.dumps(known_fields))
        .replace("{choice_manifest}", json.dumps(choice_manifest))
    )


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

def _extract_json(response: str) -> dict:
    """
    Extract and parse JSON from LLM response.
    Tries fenced block first, falls back to bare JSON parse.
    Raises ValueError on failure.
    """
    match = _JSON_FENCE_RE.search(response)
    if match:
        candidate = match.group(1)
    else:
        log.warning("No ```json fence found — attempting bare JSON parse.")
        candidate = response.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}\n\nRaw response:\n{response}") from e


def _str(val: Any) -> str:
    """Normalise JSON null / missing to empty string."""
    if val is None:
        return ""
    return str(val).strip()


def _parse_survey_rows(raw_rows: list[dict], languages: list[str]) -> list[SurveyRow]:
    rows = []
    for raw in raw_rows:
        labels: dict[str, str] = {}
        hints: dict[str, str] = {}
        constraint_messages: dict[str, str] = {}
        media_images: dict[str, str] = {}

        for lang in languages:
            labels[f"label:{lang}"]                  = _str(raw.get("labels", {}).get(lang))
            hints[f"hint:{lang}"]                    = _str(raw.get("hints", {}).get(lang))
            constraint_messages[f"constraint message:{lang}"] = _str(raw.get("constraint_messages", {}).get(lang))
            media_images[f"media:image:{lang}"]      = _str(raw.get("media_images", {}).get(lang))

        rows.append(SurveyRow(
            type=_str(raw.get("type")),
            name=_str(raw.get("name")),
            appearance=_str(raw.get("appearance")),
            relevance=_str(raw.get("relevance")),
            required=_str(raw.get("required")),
            constraint=_str(raw.get("constraint")),
            calculation=_str(raw.get("calculation")),
            choice_filter=_str(raw.get("choice_filter")),
            read_only=_str(raw.get("read_only")),
            default=_str(raw.get("default")),
            repeat_count=_str(raw.get("repeat_count")),
            minimum_seconds=_str(raw.get("minimum_seconds")),
            publishable=_str(raw.get("publishable")),
            labels=labels,
            hints=hints,
            constraint_messages=constraint_messages,
            media_images=media_images,
        ))
    return rows


def _parse_choice_rows(raw_rows: list[dict]) -> list[ChoiceRow]:
    rows = []
    for raw in raw_rows:
        list_name = _str(raw.get("list_name"))
        raw_value = raw.get("value")
        raw_filter = raw.get("filter")

        if not list_name and raw_value is None:
            continue

        if raw_value is None:
            log.warning(f"None value in choices for list '{list_name}' — skipping row.")
            continue
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            log.warning(f"Non-numeric value '{raw_value}' in choices for list '{list_name}' — skipping row.")
            continue

        try:
            filter_val = int(raw_filter) if raw_filter is not None else None
        except (TypeError, ValueError):
            log.warning(f"Non-numeric filter '{raw_filter}' in choices — setting to None.")
            filter_val = None

        labels = {f"label:{k}": _str(v) for k, v in raw.get("labels", {}).items()}

        rows.append(ChoiceRow(
            list_name=list_name,
            value=value,
            filter=filter_val,
            labels=labels,
        ))
    return rows


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def _build_fingerprint(rows: list[ChoiceRow], primary_language: str) -> str:
    """Sorted 'value|primary_label' string for a single choice list."""
    label_key = f"label:{primary_language}"
    pairs = sorted(f"{r.value}|{r.labels.get(label_key, '')}" for r in rows)
    return ";".join(pairs)


def _update_manifest(
    choice_manifest: list[dict],
    choice_rows: list[ChoiceRow],
    primary_language: str,
) -> list[dict]:
    """
    Append any new list_names from this module's choice rows to the manifest.
    First occurrence of each list_name wins.
    """
    existing_names = {entry["list_name"] for entry in choice_manifest}
    # Group rows by list_name preserving order
    lists: dict[str, list[ChoiceRow]] = {}
    for row in choice_rows:
        lists.setdefault(row.list_name, []).append(row)

    updated = list(choice_manifest)
    for list_name, rows in lists.items():
        if list_name not in existing_names:
            updated.append({
                "list_name": list_name,
                "fingerprint": _build_fingerprint(rows, primary_language),
            })
    return updated


def _update_known_fields(known_fields: list[str], survey_rows: list[SurveyRow]) -> list[str]:
    """Append non-empty, non-duplicate field names from this module."""
    existing = set(known_fields)
    updated = list(known_fields)
    for row in survey_rows:
        if row.name and row.name not in existing:
            updated.append(row.name)
            existing.add(row.name)
    return updated


# ---------------------------------------------------------------------------
# Per-module call
# ---------------------------------------------------------------------------

def _build_user_prompt(module: RawModule) -> str:
    return f"MODULE TEXT:\n{module.text}"


def parse_module(
    module: RawModule,
    llm: ChatGoogleGenerativeAI,
    prompt_template: str,
    languages: list[str],
    known_fields: list[str],
    choice_manifest: list[dict],
    debug: bool = False,
) -> ModuleOutput:
    """
    Send one RawModule to the LLM and return a parsed ModuleOutput.

    Raises:
        ValueError: On malformed LLM response (halts pipeline by default).
        To SKIP instead of halting, wrap the call in:

            try:
                output = parse_module(...)
            except Exception as e:
                log.error(f"Skipping module {module.index}: {e}")
                continue
    """
    log.info(f"Parsing module {module.index}...")

    system_prompt = _render_prompt(prompt_template, languages, known_fields, choice_manifest)
    user_prompt = _build_user_prompt(module)
    response = _call_llm(llm, system_prompt, user_prompt)

    if debug:
        log.debug("Raw LLM response for module %d:\n%s", module.index, response)

    data = _extract_json(response)

    if not isinstance(data, dict) or "survey" not in data or "choices" not in data:
        raise ValueError(f"JSON response missing 'survey' or 'choices' keys. Got: {list(data.keys())}")

    survey_rows = _parse_survey_rows(data["survey"], languages)
    choice_rows = _parse_choice_rows(data["choices"])

    log.info(f"Module {module.index}: {len(survey_rows)} survey rows, {len(choice_rows)} choice rows.")
    return ModuleOutput(
        index=module.index,
        survey_rows=survey_rows,
        choice_rows=choice_rows,
    )


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def parse_all_modules(
    modules: list[RawModule],
    api_key: str,
    prompt_path: Path,
    languages: list[str],
    model: str = DEFAULT_MODEL,
    debug: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[ModuleOutput]:
    """
    Loop over all modules, accumulating known_fields and choice_manifest
    across calls. Skips modules that fail to parse (no halt).

    Args:
        modules:      Output of splitter.split_document().
        api_key:      Gemini API key.
        prompt_path:  Path to prompts/parse_module.yaml.
        languages:    Ordered list of language keys, e.g. ["english", "urdu"].
                      First entry is the primary language.
        model:        LLM model string. Defaults to gemini-2.5-flash-lite.
        debug:        Log raw LLM responses if True.

    Returns:
        List of ModuleOutput in module order (failed modules omitted).
    """
    llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    prompt_template = _load_prompt_template(prompt_path)
    primary_language = languages[0]

    known_fields: list[str] = []
    choice_manifest: list[dict] = []
    outputs: list[ModuleOutput] = []

    for module in modules:
        try:
            output = parse_module(
                module=module,
                llm=llm,
                prompt_template=prompt_template,
                languages=languages,
                known_fields=known_fields,
                choice_manifest=choice_manifest,
                debug=debug,
            )
        except Exception as e:
            log.error(f"Module {module.index} failed — skipping. Reason: {e}")
            continue

        # Accumulate only on success
        known_fields = _update_known_fields(known_fields, output.survey_rows)
        choice_manifest = _update_manifest(choice_manifest, output.choice_rows, primary_language)

        if debug:
            log.debug("known_fields after module %d: %s", module.index, known_fields)
            log.debug("choice_manifest after module %d: %s", module.index, choice_manifest)

        outputs.append(output)
        if on_progress is not None:
            on_progress(len(outputs), len(modules))

    log.info(f"Parsed {len(outputs)}/{len(modules)} modules successfully.")
    return outputs
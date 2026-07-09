"""
Integration test for parser.py.
Splits a real .docx (one module) and sends it to the Gemini API.
Logs the resulting ModuleOutput as CSV to stdout and app.log.

Required .env:
    DEBUG_PATH="D:\\path\\to\\document.docx"
    GEMINI_API_KEY="your-key-here"
"""

import csv
import io
import os
from pathlib import Path

from pipeline.parser import parse_module, _load_prompt
from pipeline.splitter import split_document
from utils.logger import get_logger, setup_logging
from langchain_google_genai import ChatGoogleGenerativeAI

setup_logging(log_file=Path("app.log"))
log = get_logger("test_parser")


def module_output_to_csv(output) -> tuple[str, str]:
    """Serialize survey_rows and choice_rows to CSV strings."""

    # --- SURVEY ---
    if output.survey_rows:
        # Collect all dynamic column names in order of first appearance
        label_keys = []
        hint_keys = []
        cm_keys = []
        mi_keys = []
        for row in output.survey_rows:
            for k in row.labels:
                if k not in label_keys:
                    label_keys.append(k)
            for k in row.hints:
                if k not in hint_keys:
                    hint_keys.append(k)
            for k in row.constraint_messages:
                if k not in cm_keys:
                    cm_keys.append(k)
            for k in row.media_images:
                if k not in mi_keys:
                    mi_keys.append(k)

        fixed = [
            "type", "name", "appearance", "relevance", "required",
            "constraint", "calculation", "choice_filter", "read only",
            "default", "repeat_count", "minimum_seconds", "publishable",
        ]
        headers = (
            ["type", "name"]
            + label_keys
            + ["appearance", "relevance", "required"]
            + hint_keys
            + ["constraint"]
            + cm_keys
            + ["calculation", "choice_filter", "read only", "default",
               "repeat_count"]
            + mi_keys
            + ["minimum_seconds", "publishable"]
        )

        survey_buf = io.StringIO()
        writer = csv.DictWriter(survey_buf, fieldnames=headers, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in output.survey_rows:
            d = {
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
            }
            d.update(row.labels)
            d.update(row.hints)
            d.update(row.constraint_messages)
            d.update(row.media_images)
            writer.writerow(d)
        survey_csv = survey_buf.getvalue()
    else:
        survey_csv = ""

    # --- CHOICES ---
    if output.choice_rows:
        label_keys_c = []
        for row in output.choice_rows:
            for k in row.labels:
                if k not in label_keys_c:
                    label_keys_c.append(k)

        headers_c = ["list_name", "name"] + label_keys_c
        choices_buf = io.StringIO()
        writer_c = csv.DictWriter(choices_buf, fieldnames=headers_c, quoting=csv.QUOTE_ALL)
        writer_c.writeheader()
        for row in output.choice_rows:
            d = {"list_name": row.list_name, "name": row.name}
            d.update(row.labels)
            writer_c.writerow(d)
        choices_csv = choices_buf.getvalue()
    else:
        choices_csv = ""

    return survey_csv, choices_csv


if __name__ == "__main__":
    debug_path = os.environ.get("DEBUG_PATH")
    api_key = os.environ.get("GOOGLE_API_KEY")

    if not debug_path:
        raise KeyError("DEBUG_PATH not set in environment.")
    if not api_key:
        raise KeyError("GOOGLE_API_KEY not set in environment.")

    prompt_path = Path("prompts/parse_module.yaml")

    log.info(f"Splitting document: {debug_path}")
    modules = split_document(Path(debug_path))
    log.info(f"Using module 0 of {len(modules)} total.")

    module = modules[1]
    log.info(f"Module text preview: {module.text[:200]}...")

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
    system_prompt = _load_prompt(prompt_path)

    output = parse_module(module, llm, system_prompt)

    survey_csv, choices_csv = module_output_to_csv(output)

    log.info("=== SURVEY CSV ===\n" + survey_csv)
    log.info("=== CHOICES CSV ===\n" + choices_csv)
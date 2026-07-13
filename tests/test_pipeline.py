"""
End-to-end pipeline test: splitter → parser → compiler
Reads DEBUG_PATH and GEMINI_API_KEY from environment.
"""

import os
from pathlib import Path

from pipeline.splitter import split_document
from pipeline.parser import parse_all_modules
from pipeline.compiler import compile_outputs
from utils.logger import get_logger, setup_logging

setup_logging(log_file=Path("app.log"))
log = get_logger("debug_pipeline")

if __name__ == "__main__":
    debug_path = os.environ.get("DEBUG_PATH")
    api_key = os.environ.get("GOOGLE_API_KEY")

    if not debug_path:
        raise KeyError("DEBUG_PATH not set.")
    if not api_key:
        raise KeyError("GOOGLE_API_KEY not set.")

    docx_path = Path(debug_path)
    prompt_path = Path("prompts/parse_module.yaml")

    log.info("=== STAGE 1: SPLITTING ===")
    modules = split_document(docx_path)
    log.info(f"Found {len(modules)} module(s).")

    log.info("=== STAGE 2: PARSING ===")
    outputs = parse_all_modules(modules, api_key, prompt_path, model='gemini-2.5-flash', debug=True)

    log.info("=== STAGE 3: COMPILING ===")
    out_path = compile_outputs(outputs, docx_path)
    log.info(f"Done. Output written to: {out_path}")
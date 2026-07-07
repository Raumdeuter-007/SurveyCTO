from pathlib import Path
from pipeline.splitter import split_document
from utils.logger import get_logger, setup_logging
import os

if __name__ == "__main__":
    setup_logging(log_file=Path("app.log"))
    log = get_logger("debug_split")

    if 'DEBUG_PATH' not in os.environ:
        raise KeyError("Environment variable 'DEBUG_PATH' is required but missing.")

    path = Path(os.environ['DEBUG_PATH'])
    
    log.info(f"Loading document: {path}")
    modules = split_document(path)
    log.info(f"Found {len(modules)} module(s)")
    
    for m in modules:
        log.info(f"\n{'='*60}")
        log.info(f"MODULE {m.index}")
        log.info(f"{'='*60}")
        log.info(m.text)
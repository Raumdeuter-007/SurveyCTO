"""Pipeline controller.

Runs the full conversion pipeline (splitter → parser → compiler) in a
background thread. Progress and errors are pushed onto a queue.Queue so
the CTk UI can poll it safely via after().

Usage:
    controller = PipelineController(
        input_path=Path("survey.docx"),
        languages=["English", "French"],
        api_key="...",
        on_event=my_handler,   # called from UI thread via after()
    )
    controller.start()

Events pushed to the handler:
    ("status",   message: str)                        # plain status text
    ("init",     total: int)                          # bar initialised — N+1 steps
    ("progress", current: int, total: int, message: str)
    ("done",     output_path: Path)                   # conversion complete
    ("error",    message: str)                        # fatal — pipeline halted
"""

import queue
import threading
from collections.abc import Callable
from pathlib import Path

from src.pipeline.splitter import split_document
from src.pipeline.parser import parse_all_modules
from src.pipeline.compiler import compile_outputs

# Fixed path relative to project root.
_PROMPT_PATH = Path("prompts/parse_module.yaml")

# Keyring key name — matches what app.py stores on first launch.
API_KEY_NAME = "google_api_key"

Event = tuple  # ("type", *args)


class PipelineController:
    """Orchestrates the pipeline in a daemon thread; emits events via a queue."""

    def __init__(
        self,
        input_path: Path,
        languages: list[str],
        api_key: str,
        on_event: Callable[[Event], None],
        out_dir: Path | None = None,
    ) -> None:
        self._input_path = input_path
        self._languages  = languages
        self._api_key    = api_key
        self._on_event   = on_event
        self._out_dir    = out_dir
        self._queue: queue.Queue[Event] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # -- public -----------------------------------------------------------

    def start(self) -> None:
        """Start the pipeline thread. Call once."""
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    # -- internal ---------------------------------------------------------

    def _emit(self, *event) -> None:
        """Push an event; the UI polls this queue via after()."""
        self._on_event(event)

    def _run(self) -> None:
        try:
            self._emit("status", "Splitting document…")
            modules = split_document(self._input_path)
            n = len(modules)

            if n == 0:
                self._emit("error", "No modules found in document.")
                return

            # Total steps: N parser steps + 1 compiler step.
            total = n + 1
            self._emit("init", total)

            self._emit("status", f"Parsing {n} modules…")
            outputs = parse_all_modules(
                modules=modules,
                api_key=self._api_key,
                prompt_path=_PROMPT_PATH,
                languages=self._languages,
                on_progress=lambda current, _total: self._emit(
                    "progress",
                    current,
                    total,
                    f"Parsed module {current} of {n}",
                ),
            )

            if not outputs:
                self._emit("error", "All modules failed to parse.")
                return

            self._emit("status", "Compiling output…")
            output_path = compile_outputs(
                outputs=outputs,
                docx_path=self._input_path,
                languages=self._languages,
                out_dir=self._out_dir,
                on_progress=lambda: self._emit(
                    "progress",
                    total,
                    total,
                    "Compilation complete",
                ),
            )

            self._emit("done", output_path)

        except FileNotFoundError as e:
            self._emit("error", f"File not found: {e}")
        except Exception as e:
            self._emit("error", str(e))
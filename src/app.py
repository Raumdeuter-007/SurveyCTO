"""Main application window.

Entry point:
    from src.ui.app import App
    App().mainloop()

Layout (top → bottom):
    ┌─────────────────────────────────────┐
    │  Header: title + theme toggle       │
    ├─────────────────────────────────────┤
    │  File selection                     │
    ├─────────────────────────────────────┤
    │  Language input                     │
    ├─────────────────────────────────────┤
    │  Process button                     │
    ├─────────────────────────────────────┤
    │  Progress bar + status label        │
    ├─────────────────────────────────────┤
    │  Log area (scrollable)              │
    └─────────────────────────────────────┘
"""

import logging
import queue
import shutil
import tempfile
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from src.utils.keyring import get_secret, set_secret, has_secret
from src.config.theme import DARK, LIGHT, Theme
from src.ui.controller import API_KEY_NAME, PipelineController
from src.ui.language_input import LanguageInputFrame

# ── logging handler ──────────────────────────────────────────────────────────

class QueueLogHandler(logging.Handler):
    """Forwards log records to the UI event queue as ("log", message) events."""

    def __init__(self, event_queue: queue.Queue) -> None:
        super().__init__()
        self._queue = event_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put(("log", self.format(record)))
        except Exception:
            self.handleError(record)


# ── window constraints ────────────────────────────────────────────────────────
_MIN_W, _MIN_H = 560, 500
_DEF_W, _DEF_H = 620, 740


class _ApiKeyDialog(ctk.CTkToplevel):
    """Modal dialog prompting the user to enter their Google API key."""

    def __init__(self, parent, theme: Theme) -> None:
        super().__init__(parent)
        self._t = theme
        self.title("API Key Required")
        self.resizable(False, False)
        self.grab_set()  # modal
        self.configure(fg_color=theme.BG)

        pad = {"padx": 24, "pady": 10}

        ctk.CTkLabel(
            self,
            text="Google API Key",
            font=(theme.FONT[0], 15, "bold"),
            text_color=theme.FG,
        ).pack(**pad, anchor="w")

        ctk.CTkLabel(
            self,
            text="Enter your Gemini API key. It will be stored\nsecurely in your OS keyring.",
            font=theme.FONT_SM,
            text_color=theme.FG_MUTED,
            justify="left",
        ).pack(padx=24, pady=(0, 8), anchor="w")

        self._entry = ctk.CTkEntry(
            self,
            width=360,
            show="•",
            fg_color=theme.ENTRY_BG,
            border_color=theme.BORDER,
            border_width=1,
            text_color=theme.FG,
            corner_radius=theme.RADIUS,
            font=theme.FONT,
        )
        self._entry.pack(**pad)

        self._status = ctk.CTkLabel(
            self, text="", font=theme.FONT_SM, text_color=theme.DANGER
        )
        self._status.pack(padx=24, pady=(0, 4), anchor="w")

        ctk.CTkButton(
            self,
            text="Save",
            fg_color=theme.FG,
            hover_color=theme.BTN_HOVER,
            text_color=theme.ON_FG,
            corner_radius=theme.RADIUS,
            font=theme.FONT,
            command=self._save,
        ).pack(padx=24, pady=(4, 24), anchor="e")

        self.result: str | None = None
        self._entry.focus_set()
        self.bind("<Return>", lambda _: self._save())

    def _save(self) -> None:
        key = self._entry.get().strip()
        if not key:
            self._status.configure(text="Key cannot be empty.")
            return
        self.result = key
        self.grab_release()
        self.destroy()


class App(ctk.CTk):
    """Root application window."""

    def __init__(self) -> None:
        super().__init__()

        self._theme: list[Theme] = [LIGHT]
        self._queue: queue.Queue = queue.Queue()

        # Attach log handler — captures all pipeline loggers into the UI log box.
        self._log_handler = QueueLogHandler(self._queue)
        self._log_handler.setFormatter(logging.Formatter("%(levelname)s  %(name)s — %(message)s"))
        logging.getLogger().addHandler(self._log_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        self._controller: PipelineController | None = None
        self._tmp_dir: Path | None = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.title("Survey → SurveyCTO")
        self.geometry(f"{_DEF_W}x{_DEF_H}")
        self.minsize(_MIN_W, _MIN_H)
        self.configure(fg_color=self._t.BG)

        self._build_ui()
        self._poll_queue()
        self._prompt_api_key_if_missing()

    # ── convenience ──────────────────────────────────────────────────────────

    @property
    def _t(self) -> Theme:
        return self._theme[0]

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root_pad = {"padx": 28}

        # Header ─────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 16))

        ctk.CTkLabel(
            header,
            text="Survey Converter",
            font=(self._t.FONT[0], 20, "bold"),
            text_color=self._t.FG,
        ).pack(side="left")

        self._theme_btn = ctk.CTkButton(
            header,
            text="☾  Dark",
            width=90,
            height=30,
            fg_color="transparent",
            hover_color=self._t.ENTRY_BG,
            text_color=self._t.FG_MUTED,
            border_width=1,
            border_color=self._t.BORDER,
            corner_radius=self._t.RADIUS,
            font=self._t.FONT_SM,
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right")

        # Divider ────────────────────────────────────────────────────────────
        self._divider(pady=(0, 20))

        # File selection ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Input file",
            font=(self._t.FONT[0], self._t.FONT[1], "bold"),
            text_color=self._t.FG,
        ).pack(**root_pad, anchor="w", pady=(0, 6))

        file_row = ctk.CTkFrame(self, fg_color="transparent")
        file_row.pack(fill="x", padx=28, pady=(0, 20))
        file_row.grid_columnconfigure(0, weight=1)

        self._file_label = ctk.CTkLabel(
            file_row,
            text="No file selected",
            font=self._t.FONT,
            text_color=self._t.FG_MUTED,
            fg_color=self._t.ENTRY_BG,
            corner_radius=self._t.RADIUS,
            anchor="w",
        )
        self._file_label.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=6, ipadx=10)

        self._browse_btn = ctk.CTkButton(
            file_row,
            text="Browse",
            width=88,
            fg_color="transparent",
            hover_color=self._t.ENTRY_BG,
            text_color=self._t.ACCENT,
            border_width=1,
            border_color=self._t.ACCENT,
            corner_radius=self._t.RADIUS,
            font=self._t.FONT,
            command=self._browse,
        )
        self._browse_btn.grid(row=0, column=1)

        # Language input ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Languages",
            font=(self._t.FONT[0], self._t.FONT[1], "bold"),
            text_color=self._t.FG,
        ).pack(**root_pad, anchor="w", pady=(0, 6))

        self._lang_input = LanguageInputFrame(self, theme=self._t, on_change=self._update_process_btn)
        self._lang_input.pack(fill="x", padx=28, pady=(0, 20))

        # Divider ────────────────────────────────────────────────────────────
        self._divider(pady=(0, 20))

        # Process button ─────────────────────────────────────────────────────
        self._process_btn = ctk.CTkButton(
            self,
            text="Process",
            height=40,
            fg_color=self._t.FG,
            hover_color=self._t.BTN_HOVER,
            text_color=self._t.ON_FG,
            corner_radius=self._t.RADIUS,
            font=(self._t.FONT[0], self._t.FONT[1], "bold"),
            command=self._start_processing,
            state="disabled",
        )
        self._process_btn.pack(fill="x", padx=28, pady=(0, 20))

        # Progress area ──────────────────────────────────────────────────────
        self._progress_bar = ctk.CTkProgressBar(
            self,
            mode="determinate",
            progress_color=self._t.ACCENT,
            fg_color=self._t.ENTRY_BG,
            corner_radius=self._t.RADIUS,
            height=6,
        )
        self._progress_bar.set(0)
        self._progress_bar.pack(fill="x", padx=28, pady=(0, 6))

        self._status_label = ctk.CTkLabel(
            self,
            text="",
            font=self._t.FONT_SM,
            text_color=self._t.FG_MUTED,
            anchor="w",
        )
        self._status_label.pack(fill="x", padx=28, pady=(0, 16))

        # Log area ───────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Log",
            font=(self._t.FONT[0], self._t.FONT[1], "bold"),
            text_color=self._t.FG,
        ).pack(padx=28, anchor="w", pady=(0, 6))

        self._log_box = ctk.CTkTextbox(
            self,
            fg_color=self._t.ENTRY_BG,
            border_color=self._t.BORDER,
            border_width=1,
            text_color=self._t.FG,
            font=self._t.FONT_SM,
            corner_radius=self._t.RADIUS,
            state="disabled",
            wrap="word",
        )
        self._log_box.pack(fill="both", expand=True, padx=28, pady=(0, 28))

    def _divider(self, pady=(0, 0)) -> None:
        ctk.CTkFrame(
            self, height=1, fg_color=self._t.BORDER
        ).pack(fill="x", padx=28, pady=pady)

    # ── API key ───────────────────────────────────────────────────────────────

    def _prompt_api_key_if_missing(self) -> None:
        if has_secret(API_KEY_NAME):
            return
        dialog = _ApiKeyDialog(self, self._t)
        self.wait_window(dialog)
        if dialog.result:
            set_secret(API_KEY_NAME, dialog.result)
        else:
            self._set_status("⚠  No API key stored. Processing will fail.", error=True)

    # ── actions ───────────────────────────────────────────────────────────────

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select survey document",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")],
        )
        if not path:
            return
        self._input_path = Path(path)
        # Truncate long paths for display.
        display = self._input_path.name
        self._file_label.configure(text=display, text_color=self._t.FG)
        self._update_process_btn()

    def _update_process_btn(self) -> None:
        if not hasattr(self, "_lang_input"):
            return
        has_file  = hasattr(self, "_input_path")
        has_langs = bool(self._lang_input.get_languages())
        state = "normal" if (has_file and has_langs) else "disabled"
        self._process_btn.configure(state=state)

    def _start_processing(self) -> None:
        api_key = get_secret(API_KEY_NAME)
        if not api_key:
            self._prompt_api_key_if_missing()
            api_key = get_secret(API_KEY_NAME)
        if not api_key:
            self._set_status("No API key — cannot process.", error=True)
            return

        languages = self._lang_input.get_languages()
        if not languages:
            self._set_status("Add at least one language.", error=True)
            return

        # Reset UI state.
        self._log_clear()
        self._progress_bar.set(0)
        self._set_status("Starting…")
        self._process_btn.configure(state="disabled")
        self._browse_btn.configure(state="disabled")

        # Temp dir for pipeline output — moved on save.
        if self._tmp_dir:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        self._tmp_dir = Path(tempfile.mkdtemp())

        self._total_steps = 1  # updated when "init" event arrives

        self._controller = PipelineController(
            input_path=self._input_path,
            languages=languages,
            api_key=api_key,
            on_event=self._queue.put,
            out_dir=self._tmp_dir,
        )
        self._controller.start()

    def _on_done(self, output_path: Path) -> None:
        self._progress_bar.set(1.0)
        self._set_status("✓  Conversion complete.")
        self._process_btn.configure(state="normal")
        self._browse_btn.configure(state="normal")
        self._prompt_save(output_path)

    def _on_error(self, message: str) -> None:
        self._set_status(f"✕  {message}", error=True)
        self._process_btn.configure(state="normal")
        self._browse_btn.configure(state="normal")

    def _prompt_save(self, src: Path) -> None:
        dest = filedialog.asksaveasfilename(
            title="Save output",
            defaultextension=".xlsx",
            initialfile=src.name,
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if not dest:
            self._set_status("Save cancelled — file not written.", error=False)
            return
        shutil.move(str(src), dest)
        self._set_status(f"✓  Saved to {Path(dest).name}")

    # ── queue polling ─────────────────────────────────────────────────────────

    def _poll_queue(self) -> None:
        try:
            while True:
                event = self._queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]

        if kind == "status":
            self._set_status(event[1])

        elif kind == "init":
            self._total_steps = event[1]
            self._progress_bar.set(0)

        elif kind == "progress":
            current, total, message = event[1], event[2], event[3]
            self._progress_bar.set(current / total if total else 0)
            self._set_status(message)

        elif kind == "done":
            self._on_done(event[1])

        elif kind == "log":
            self._log_append(event[1])

        elif kind == "error":
            self._on_error(event[1])

    # ── theme ─────────────────────────────────────────────────────────────────

    def _toggle_theme(self) -> None:
        self._theme[0] = DARK if self._theme[0] is LIGHT else LIGHT
        t = self._t
        ctk.set_appearance_mode("dark" if t is DARK else "light")
        self._apply_theme(t)
        self._lang_input.set_theme(t)
        label = "☀  Light" if t is DARK else "☾  Dark"
        self._theme_btn.configure(text=label)

    def _apply_theme(self, t: Theme) -> None:
        self.configure(fg_color=t.BG)
        self._theme_btn.configure(
            hover_color=t.ENTRY_BG, text_color=t.FG_MUTED,
            border_color=t.BORDER,
        )
        self._file_label.configure(fg_color=t.ENTRY_BG)
        self._browse_btn.configure(
            hover_color=t.ENTRY_BG, text_color=t.ACCENT, border_color=t.ACCENT,
        )
        self._process_btn.configure(
            fg_color=t.FG, hover_color=t.BTN_HOVER, text_color=t.ON_FG,
        )
        self._progress_bar.configure(
            progress_color=t.ACCENT, fg_color=t.ENTRY_BG,
        )
        self._status_label.configure(text_color=t.FG_MUTED)
        self._log_box.configure(
            fg_color=t.ENTRY_BG, border_color=t.BORDER, text_color=t.FG,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, error: bool = False) -> None:
        color = self._t.DANGER if error else self._t.FG_MUTED
        self._status_label.configure(text=text, text_color=color)

    def _log_append(self, line: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", line + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _log_clear(self) -> None:
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
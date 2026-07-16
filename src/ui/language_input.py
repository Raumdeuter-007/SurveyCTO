"""Dynamic language input widget.

Renders a variable number of rows, each with:
  - a text entry (free text allowed)
  - substring-filtered dropdown suggestions (CTkFrame-based, styled)
  - a remove button (all rows except the first)

A "+ Add language" button appends new rows.

Usage:
    from src.config.theme import LIGHT
    widget = LanguageInputFrame(parent, theme=LIGHT)
    widget.pack(...)
    langs = widget.get_languages()  # -> list[str], empty/dup-free

    # Runtime theme switch:
    widget.set_theme(DARK)
"""

import customtkinter as ctk

from src.config.lang import KNOWN_LANGUAGES
from src.config.theme import Theme, LIGHT


class _LanguageRow(ctk.CTkFrame):
    """A single language entry row with autocomplete + optional remove button."""

    def __init__(self, parent, on_remove, theme: Theme, is_first: bool = False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_remove = on_remove
        self._t = theme
        self._suggestions: list[str] = []
        self._dropdown = None
        self._outer = None
        self._is_first = is_first

        self.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text="e.g. French",
            fg_color=self._t.ENTRY_BG,
            border_color=self._t.BORDER,
            border_width=1,
            text_color=self._t.FG,
            placeholder_text_color=self._t.FG_MUTED,
            corner_radius=self._t.RADIUS,
            font=self._t.FONT,
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 6 if not is_first else 0))
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Tab>", self._accept_first_suggestion)
        self.entry.bind("<FocusOut>", self._hide_dropdown_deferred)
        self.entry.bind("<FocusIn>", self._on_key_release)

        self._remove_btn = None
        if not is_first:
            self._remove_btn = ctk.CTkButton(
                self,
                text="✕",
                width=32,
                height=32,
                fg_color="transparent",
                hover_color=self._t.ENTRY_BG,
                text_color=self._t.FG_MUTED,
                border_width=1,
                border_color=self._t.BORDER,
                corner_radius=self._t.RADIUS,
                font=self._t.FONT_SM,
                command=self._remove_self,
            )
            self._remove_btn.grid(row=0, column=1)

    # -- public -------------------------------------------------------

    def get_value(self) -> str:
        return self.entry.get().strip()

    def set_theme(self, theme: Theme) -> None:
        self._t = theme
        self.entry.configure(
            fg_color=theme.ENTRY_BG,
            border_color=theme.BORDER,
            text_color=theme.FG,
            placeholder_text_color=theme.FG_MUTED,
            corner_radius=theme.RADIUS,
            font=theme.FONT,
        )
        if self._remove_btn is not None:
            self._remove_btn.configure(
                hover_color=theme.ENTRY_BG,
                text_color=theme.FG_MUTED,
                border_color=theme.BORDER,
                corner_radius=theme.RADIUS,
                font=theme.FONT_SM,
            )
        # Rebuild dropdown with new theme if currently visible.
        if self._dropdown is not None:
            self._hide_dropdown()
            self._update_dropdown()

    # -- internal -------------------------------------------------------

    def _remove_self(self):
        self._hide_dropdown()
        self._on_remove(self)

    def _matches(self, text: str) -> list[str]:
        if not text:
            return []
        low = text.lower()
        return [lang for lang in KNOWN_LANGUAGES if low in lang.lower()]

    def _accept_first_suggestion(self, event=None):
        if self._suggestions:
            self._select_suggestion(self._suggestions[0])
            return "break"  # prevent Tab from shifting focus

    def _on_key_release(self, event=None):
        text = self.entry.get()
        self._suggestions = self._matches(text)
        self._update_dropdown()

    def _update_dropdown(self):
        if not self._suggestions:
            self._hide_dropdown()
            return

        # Hide if typed text is an exact match (case-insensitive).
        if self.entry.get().strip().lower() in {s.lower() for s in self._suggestions}:
            self._hide_dropdown()
            return

        ROW_H   = 32
        PADDING = 8
        MAX_VIS = 5

        n      = min(len(self._suggestions), MAX_VIS)
        width  = int(self.entry.winfo_width() * 0.55)
        height = n * ROW_H + PADDING
        x      = self.entry.winfo_rootx()
        y      = self.entry.winfo_rooty() + self.entry.winfo_height() + 4

        # Create the toplevel once; reuse it to avoid OS window flicker.
        if self._dropdown is None:
            self._dropdown = ctk.CTkToplevel(self)
            self._dropdown.overrideredirect(True)
            self._dropdown.attributes("-topmost", True)
            self._dropdown.configure(fg_color=self._t.BG)
            self._outer = ctk.CTkFrame(
                self._dropdown,
                fg_color=self._t.BG,
                border_color=self._t.BORDER,
                border_width=1,
                corner_radius=self._t.RADIUS,
            )
            self._outer.pack(fill="both", expand=True)
        else:
            if self._outer:
                self._outer.configure(
                    fg_color=self._t.BG,
                    border_color=self._t.BORDER,
                    corner_radius=self._t.RADIUS,
                )

        # Clear and repopulate only the inner buttons.
        if self._outer:
            for child in self._outer.winfo_children():
                child.destroy()

        for lang in self._suggestions[:MAX_VIS]:
            btn = ctk.CTkButton(
                self._outer,
                text=lang,
                anchor="w",
                fg_color="transparent",
                hover_color=self._t.ENTRY_BG,
                text_color=self._t.FG,
                font=self._t.FONT,
                height=ROW_H,
                corner_radius=self._t.RADIUS - 1,
                command=lambda l=lang: self._select_suggestion(l),
            )
            btn.pack(fill="x", padx=4, pady=(2, 0))

        self._dropdown.geometry(f"{width}x{height}+{x}+{y}")
        self._dropdown.deiconify()

    def _select_suggestion(self, lang: str):
        self._suggestions = []   # clear before hide so FocusIn re-check finds no matches
        self.entry.delete(0, "end")
        self.entry.insert(0, lang)
        self._hide_dropdown()
        self.entry.focus_set()

    def _hide_dropdown(self):
        if self._dropdown is not None:
            self._dropdown.destroy()
            self._dropdown = None
            self._outer = None

    def _hide_dropdown_deferred(self, event=None):
        # Delay so a suggestion button click registers before FocusOut tears it down.
        self.after(150, self._hide_dropdown)


class LanguageInputFrame(ctk.CTkFrame):
    """Container managing N _LanguageRow instances + an add button."""

    def __init__(self, parent, theme: Theme = LIGHT, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._t = theme
        self._rows: list[_LanguageRow] = []

        self._rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._rows_frame.pack(fill="x")
        self._rows_frame.grid_columnconfigure(0, weight=1)

        self._add_btn = ctk.CTkButton(
            self,
            text="+ Add language",
            fg_color="transparent",
            hover_color=self._t.ENTRY_BG,
            text_color=self._t.ACCENT,
            border_width=1,
            border_color=self._t.ACCENT,
            corner_radius=self._t.RADIUS,
            font=self._t.FONT_SM,
            height=30,
            command=self.add_row,
        )
        self._add_btn.pack(anchor="w", pady=(8, 0))

        self.add_row(is_first=True)

    # -- public -------------------------------------------------------

    def add_row(self, is_first: bool = False):
        row = _LanguageRow(
            self._rows_frame,
            on_remove=self._remove_row,
            theme=self._t,
            is_first=is_first,
        )
        row.pack(fill="x", pady=(0, 6))
        self._rows.append(row)

    def set_theme(self, theme: Theme) -> None:
        """Re-apply all widget colors. Call when the user switches appearance mode."""
        self._t = theme
        self._add_btn.configure(
            hover_color=theme.ENTRY_BG,
            text_color=theme.ACCENT,
            border_color=theme.ACCENT,
            corner_radius=theme.RADIUS,
            font=theme.FONT_SM,
        )
        for row in self._rows:
            row.set_theme(theme)

    def get_languages(self) -> list[str]:
        """Return non-empty, de-duplicated (order-preserving) language list."""
        seen: set[str] = set()
        result: list[str] = []
        for row in self._rows:
            val = row.get_value()
            if val and val.lower() not in seen:
                seen.add(val.lower())
                result.append(val)
        return result

    # -- internal -------------------------------------------------------

    def _remove_row(self, row: "_LanguageRow"):
        if len(self._rows) == 1:
            return
        row.destroy()
        self._rows.remove(row)


if __name__ == "__main__":
    # Standalone smoke test.
    # Run from project root: python -m src.ui.language_input
    from src.config.theme import DARK

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")

    _theme: list[Theme] = [LIGHT]  # mutable cell — avoids nonlocal rebinding
    root = ctk.CTk()
    root.title("Language input — smoke test")
    root.geometry("460x380")
    root.configure(fg_color=_theme[0].BG)

    frame = LanguageInputFrame(root, theme=_theme[0])
    frame.pack(fill="both", expand=True, padx=24, pady=24)

    def _print():
        print("get_languages() →", frame.get_languages())

    def _toggle_theme():
        _theme[0] = DARK if _theme[0] is LIGHT else LIGHT
        root.configure(fg_color=_theme[0].BG)
        frame.set_theme(_theme[0])

    ctk.CTkButton(
        root,
        text="Print languages",
        fg_color=_theme[0].FG,
        hover_color=_theme[0].BTN_HOVER,
        text_color=_theme[0].ON_FG,
        corner_radius=_theme[0].RADIUS,
        font=_theme[0].FONT,
        command=_print,
    ).pack(pady=(0, 8))

    ctk.CTkButton(
        root,
        text="Toggle theme",
        fg_color=_theme[0].FG,
        hover_color=_theme[0].BTN_HOVER,
        text_color=_theme[0].ON_FG,
        corner_radius=_theme[0].RADIUS,
        font=_theme[0].FONT,
        command=_toggle_theme,
    ).pack(pady=(0, 24))

    root.mainloop()
"""UI theme constants for light and dark modes.

Usage:
    from src.config.theme import LIGHT, DARK, Theme

    theme = LIGHT  # or DARK
    widget.configure(fg_color=theme.BG)

All color values are hex strings. Import the Theme instance that matches
the user's selected appearance mode, or switch at runtime by reassigning.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    # -- Surfaces ----------------------------------------------------------
    BG: str         # main window / outer surface
    SURFACE: str    # cards, panels
    ENTRY_BG: str   # input fields — slightly offset from surface

    # -- Text --------------------------------------------------------------
    FG: str         # primary text, filled buttons
    FG_MUTED: str   # placeholders, secondary labels, remove button
    ON_FG: str      # text rendered on top of FG-filled surfaces (e.g. filled buttons)

    # -- Accent ------------------------------------------------------------
    ACCENT: str     # sage green — add button, focus rings, selection highlight

    # -- Hover -------------------------------------------------------------
    BTN_HOVER: str  # hover state for FG-filled primary buttons

    # -- Borders -----------------------------------------------------------
    BORDER: str     # hairline borders on entries, buttons, dropdowns

    # -- Typography --------------------------------------------------------
    FONT: tuple[str, int]
    FONT_SM: tuple[str, int]

    # -- Shape -------------------------------------------------------------
    RADIUS: int     # corner radius in px


LIGHT = Theme(
    BG        = "#F5F4F0",
    SURFACE   = "#ECEAE5",
    ENTRY_BG  = "#E3E1DB",
    FG        = "#2C2C2A",
    FG_MUTED  = "#9E9C97",
    ON_FG     = "#F5F4F0",
    ACCENT    = "#5A7A6B",
    BTN_HOVER = "#444441",
    BORDER    = "#D0CEC8",
    FONT      = ("Inter", 13),
    FONT_SM   = ("Inter", 12),
    RADIUS    = 6,
)

DARK = Theme(
    BG        = "#1E1E1C",
    SURFACE   = "#2A2A28",
    ENTRY_BG  = "#333331",
    FG        = "#F0EEE9",
    FG_MUTED  = "#6B6966",
    ON_FG     = "#1E1E1C",
    ACCENT    = "#6B9E8A",
    BTN_HOVER = "#C8C6C1",
    BORDER    = "#3D3D3A",
    FONT      = ("Inter", 13),
    FONT_SM   = ("Inter", 12),
    RADIUS    = 6,
)
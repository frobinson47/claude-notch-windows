"""Theme definitions and stylesheet generation for Claude Notch.

Provides dark and light theme color tokens, Qt stylesheet generation
for SettingsDialog, and overlay color helpers. No external dependencies.
"""

# ---------------------------------------------------------------------------
# Theme token dictionaries
# ---------------------------------------------------------------------------

_DARK = {
    "bg": (20, 20, 20),
    "bg_alt": "#2a2a2a",
    "bg_hover": "#333",
    "bg_pressed": "#222",
    "border": "#555",
    "text": "#fff",
    "text_secondary": "#ddd",
    "text_muted": "#888",
    "accent": "#4a9eff",
    "tab_bg": "#2a2a2a",
    "tab_selected": "#3a3a3a",
}

_LIGHT = {
    "bg": (245, 245, 245),
    "bg_alt": "#fff",
    "bg_hover": "#ddd",
    "bg_pressed": "#ccc",
    "border": "#ccc",
    "text": "#222",
    "text_secondary": "#444",
    "text_muted": "#888",
    "accent": "#0066dd",
    "tab_bg": "#e8e8e8",
    "tab_selected": "#fff",
}

THEMES: dict = {
    "dark": _DARK,
    "light": _LIGHT,
}

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_theme(name: str) -> dict:
    """Return the theme dict for *name*, falling back to ``"dark"``."""
    return THEMES.get(name, THEMES["dark"])


def get_theme_names() -> list:
    """Return the list of available theme names."""
    return list(THEMES.keys())


# ---------------------------------------------------------------------------
# Overlay colors
# ---------------------------------------------------------------------------


def get_overlay_colors(theme: dict) -> dict:
    """Return overlay-specific colour values derived from *theme*.

    Keys returned:
        bg_rgb              -- background as (r, g, b) tuple
        text_css            -- primary text as CSS colour string
        text_secondary_css  -- secondary text as CSS colour string
        text_muted_css      -- muted text as CSS colour string
        dim_square_rgb      -- colour tuple for dim squares in ActivityIndicator
    """
    bg = theme["bg"]
    # Dim squares: slightly lighter than background for dark, slightly darker
    # for light.  A simple heuristic: shift each channel toward the middle.
    brightness = sum(bg) / 3
    if brightness < 128:
        dim = tuple(min(c + 30, 255) for c in bg)
    else:
        dim = tuple(max(c - 30, 0) for c in bg)

    return {
        "bg_rgb": bg,
        "text_css": theme["text"],
        "text_secondary_css": theme["text_secondary"],
        "text_muted_css": theme["text_muted"],
        "dim_square_rgb": dim,
    }


# ---------------------------------------------------------------------------
# Qt stylesheet generation
# ---------------------------------------------------------------------------


def _arrow_color(theme: dict) -> str:
    """Return the CSS colour used for spin-box / combo-box arrows."""
    # Dark theme uses #aaa, light theme uses #666.
    brightness = sum(theme["bg"]) / 3
    return "#aaa" if brightness < 128 else "#666"


def generate_dialog_stylesheet(theme: dict) -> str:
    """Generate the full Qt stylesheet for *SettingsDialog*.

    When called with the dark theme this produces output identical to the
    original hard-coded ``_DARK_STYLE``.
    """
    t = theme
    arrow = _arrow_color(t)

    # For input text we pick a colour close to theme["text"] but not quite
    # full-white in dark mode (matches the original #eee).
    brightness = sum(t["bg"]) / 3
    input_text = "#eee" if brightness < 128 else t["text"]

    # Tab text for unselected tabs: #ccc in dark, text_secondary in light.
    tab_text = "#ccc" if brightness < 128 else t["text_secondary"]

    # GroupBox title / border colour and button text reuse existing tokens.
    groupbox_color = "#aaa" if brightness < 128 else t["text_muted"]
    pane_border = "#444" if brightness < 128 else t["border"]
    groupbox_border = "#444" if brightness < 128 else t["border"]
    checkbox_border = "#666" if brightness < 128 else t["border"]
    button_hover = "#444" if brightness < 128 else "#bbb"
    slider_groove = "#333" if brightness < 128 else "#ccc"

    return (
        # --- Tab widget ---
        f"QTabWidget::pane {{ border: 1px solid {pane_border}; background: transparent;"
        f" border-radius: 6px; }}\n"
        f"QTabBar::tab {{ background: {t['tab_bg']}; color: {tab_text};"
        f" padding: 8px 18px; margin-right: 2px;"
        f" border-top-left-radius: 6px; border-top-right-radius: 6px; }}\n"
        f"QTabBar::tab:selected {{ background: {t['tab_selected']}; color: {t['text']}; }}\n"
        f"QTabBar::tab:hover {{ background: {t['bg_hover']}; }}\n"
        # --- Labels ---
        f"QLabel {{ color: {t['text_secondary']}; font-size: 13px; }}\n"
        # --- Inputs ---
        f"QSpinBox, QComboBox, QLineEdit {{ background: {t['bg_alt']}; color: {input_text};"
        f" border: 1px solid {t['border']}; border-radius: 4px;"
        f" padding: 4px 8px; min-width: 80px; }}\n"
        # --- SpinBox buttons/arrows ---
        f"QSpinBox::up-button, QSpinBox::down-button {{ background: {t['bg_hover']};"
        f" border: none; width: 16px; }}\n"
        f"QSpinBox::up-arrow {{ image: none;"
        f" border-left: 4px solid transparent; border-right: 4px solid transparent;"
        f" border-bottom: 5px solid {arrow}; }}\n"
        f"QSpinBox::down-arrow {{ image: none;"
        f" border-left: 4px solid transparent; border-right: 4px solid transparent;"
        f" border-top: 5px solid {arrow}; }}\n"
        # --- Checkboxes ---
        f"QCheckBox {{ color: {t['text_secondary']}; font-size: 13px; spacing: 8px; }}\n"
        f"QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 3px;"
        f" border: 1px solid {checkbox_border}; background: {t['bg_alt']}; }}\n"
        f"QCheckBox::indicator:checked {{ background: {t['accent']};"
        f" border-color: {t['accent']}; }}\n"
        # --- Sliders ---
        f"QSlider::groove:horizontal {{ height: 6px; background: {slider_groove};"
        f" border-radius: 3px; }}\n"
        f"QSlider::handle:horizontal {{ background: {t['accent']};"
        f" width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}\n"
        f"QSlider::sub-page:horizontal {{ background: {t['accent']};"
        f" border-radius: 3px; }}\n"
        # --- Buttons ---
        f"QPushButton {{ background: {t['bg_hover']}; color: {t['text_secondary']};"
        f" border: 1px solid {t['border']}; border-radius: 6px;"
        f" padding: 6px 16px; font-size: 13px; }}\n"
        f"QPushButton:hover {{ background: {button_hover}; }}\n"
        f"QPushButton:pressed {{ background: {t['bg_pressed']}; }}\n"
        # --- GroupBox ---
        f"QGroupBox {{ color: {groupbox_color}; border: 1px solid {groupbox_border};"
        f" border-radius: 6px; margin-top: 12px; padding-top: 16px;"
        f" font-size: 12px; }}\n"
        f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px;"
        f" padding: 0 6px; }}\n"
        # --- ComboBox dropdown ---
        f"QComboBox::drop-down {{ border: none; width: 20px; }}\n"
        f"QComboBox::down-arrow {{ image: none;"
        f" border-left: 4px solid transparent; border-right: 4px solid transparent;"
        f" border-top: 5px solid {arrow}; }}\n"
        f"QComboBox QAbstractItemView {{ background: {t['bg_alt']}; color: {input_text};"
        f" selection-background-color: {t['accent']};"
        f" border: 1px solid {t['border']}; }}\n"
    )

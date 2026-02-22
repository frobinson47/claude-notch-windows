"""Tests for theme presets feature."""

import pytest


class TestThemesModule:
    def test_dark_theme_exists(self):
        from themes import THEMES
        assert "dark" in THEMES

    def test_light_theme_exists(self):
        from themes import THEMES
        assert "light" in THEMES

    def test_get_theme_dark(self):
        from themes import get_theme, THEMES
        assert get_theme("dark") is THEMES["dark"]

    def test_get_theme_light(self):
        from themes import get_theme, THEMES
        assert get_theme("light") is THEMES["light"]

    def test_get_theme_fallback(self):
        from themes import get_theme, THEMES
        assert get_theme("nonexistent") is THEMES["dark"]

    def test_get_theme_names(self):
        from themes import get_theme_names
        names = get_theme_names()
        assert "dark" in names
        assert "light" in names

    def test_theme_has_required_keys(self):
        from themes import THEMES
        required = {"bg", "bg_alt", "bg_hover", "bg_pressed", "border",
                     "text", "text_secondary", "text_muted", "accent",
                     "tab_bg", "tab_selected"}
        for name, theme in THEMES.items():
            assert required.issubset(theme.keys()), f"{name} missing keys"

    def test_bg_is_rgb_tuple(self):
        from themes import THEMES
        for name, theme in THEMES.items():
            bg = theme["bg"]
            assert isinstance(bg, tuple) and len(bg) == 3, f"{name} bg not RGB tuple"

    def test_generate_dialog_stylesheet_returns_string(self):
        from themes import get_theme, generate_dialog_stylesheet
        result = generate_dialog_stylesheet(get_theme("dark"))
        assert isinstance(result, str)
        assert len(result) > 100

    def test_generate_dialog_stylesheet_contains_key_selectors(self):
        from themes import get_theme, generate_dialog_stylesheet
        css = generate_dialog_stylesheet(get_theme("dark"))
        assert "QTabWidget" in css
        assert "QPushButton" in css
        assert "QCheckBox" in css
        assert "QSlider" in css

    def test_light_stylesheet_uses_light_colors(self):
        from themes import get_theme, generate_dialog_stylesheet
        css = generate_dialog_stylesheet(get_theme("light"))
        # Light theme should NOT have dark-mode specific colors
        assert "#2a2a2a" not in css  # dark bg_alt
        assert "#fff" in css or "#222" in css  # light theme text colors

    def test_overlay_colors_dark(self):
        from themes import get_theme, get_overlay_colors
        colors = get_overlay_colors(get_theme("dark"))
        assert colors["bg_rgb"] == (20, 20, 20)
        assert "text_css" in colors
        assert "dim_square_rgb" in colors

    def test_overlay_colors_light(self):
        from themes import get_theme, get_overlay_colors
        colors = get_overlay_colors(get_theme("light"))
        assert colors["bg_rgb"] == (245, 245, 245)


class TestThemeSetting:
    def test_theme_default_dark(self, qapp, user_settings):
        assert user_settings.get("theme") == "dark"

    def test_theme_accepts_light(self, qapp, user_settings):
        user_settings.set("theme", "light")
        assert user_settings.get("theme") == "light"

    def test_theme_rejects_invalid(self, qapp, user_settings):
        user_settings.set("theme", "invalid")
        assert user_settings.get("theme") == "dark"  # unchanged

    def test_theme_rejects_non_string(self, qapp, user_settings):
        user_settings.set("theme", 123)
        assert user_settings.get("theme") == "dark"


class TestOverlayTheming:
    def test_overlay_has_theme_colors(self, qapp, notch_config, user_settings):
        from state_manager import StateManager
        from overlay_window import ClaudeNotchOverlay
        sm = StateManager(notch_config, user_settings=user_settings)
        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        assert hasattr(overlay, '_theme_colors')
        assert "bg_rgb" in overlay._theme_colors

    def test_session_card_accepts_theme_colors(self, qapp, notch_config, user_settings):
        from state_manager import SessionState
        from overlay_window import SessionCard
        from themes import get_theme, get_overlay_colors
        session = SessionState(session_id="t1", project_path="/tmp/t", project_name="P")
        colors = get_overlay_colors(get_theme("light"))
        card = SessionCard(session, notch_config, user_settings=user_settings, theme_colors=colors)
        assert card.theme_colors is colors

    def test_mini_card_accepts_theme_colors(self, qapp, notch_config, user_settings):
        from state_manager import SessionState
        from overlay_window import MiniSessionCard
        from themes import get_theme, get_overlay_colors
        session = SessionState(session_id="t1", project_path="/tmp/t", project_name="P")
        colors = get_overlay_colors(get_theme("light"))
        card = MiniSessionCard(session, notch_config, user_settings=user_settings, theme_colors=colors)
        assert card.theme_colors is colors

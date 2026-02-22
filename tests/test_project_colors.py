"""Tests for per-project accent colors (F2)."""

import pytest
from unittest.mock import MagicMock


class TestProjectColorsSetting:
    """Validate project_colors setting in UserSettings."""

    def test_default_is_empty_dict(self, user_settings, qapp):
        assert user_settings.get("project_colors") == {}

    def test_accepts_valid_dict(self, user_settings, qapp):
        colors = {"myproject": "purple", "work": "cyan"}
        user_settings.set("project_colors", colors)
        assert user_settings.get("project_colors") == colors

    def test_rejects_non_dict(self, user_settings, qapp):
        user_settings.set("project_colors", "not a dict")
        assert user_settings.get("project_colors") == {}

    def test_rejects_non_string_keys(self, user_settings, qapp):
        user_settings.set("project_colors", {42: "purple"})
        assert user_settings.get("project_colors") == {}

    def test_rejects_non_string_values(self, user_settings, qapp):
        user_settings.set("project_colors", {"proj": 123})
        assert user_settings.get("project_colors") == {}

    def test_accepts_empty_dict(self, user_settings, qapp):
        user_settings.set("project_colors", {"a": "b"})
        user_settings.set("project_colors", {})
        assert user_settings.get("project_colors") == {}

    def test_round_trip_persistence(self, user_settings, qapp):
        """Set, save, reload from disk."""
        from user_settings import UserSettings, DEFAULTS
        from PySide6.QtCore import QObject

        colors = {"proj1": "green", "proj2": "amber"}
        user_settings.set("project_colors", colors)
        user_settings.flush()  # force debounced save to disk

        us2 = UserSettings.__new__(UserSettings)
        QObject.__init__(us2)
        us2.settings_dir = user_settings.settings_dir
        us2.settings_file = user_settings.settings_file
        us2._settings = dict(DEFAULTS)
        us2._load()
        assert us2.get("project_colors") == colors


class TestProjectColorResolution:
    """Test color resolution precedence in overlay."""

    def test_valid_color_returns_rgb(self, notch_config, user_settings, qapp):
        from overlay_window import ClaudeNotchOverlay
        from state_manager import StateManager, SessionState

        user_settings.set("project_colors", {"myproj": "purple"})
        sm = StateManager(notch_config, user_settings=user_settings)
        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            session = MagicMock()
            session.project_name = "myproj"
            result = overlay._get_project_color(session)
            assert result == tuple(notch_config.get_color_rgb("purple"))
        finally:
            overlay.close()

    def test_invalid_color_name_returns_none(self, notch_config, user_settings, qapp):
        from overlay_window import ClaudeNotchOverlay
        from state_manager import StateManager

        user_settings.set("project_colors", {"myproj": "nonexistent_color"})
        sm = StateManager(notch_config, user_settings=user_settings)
        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            session = MagicMock()
            session.project_name = "myproj"
            result = overlay._get_project_color(session)
            assert result is None
        finally:
            overlay.close()

    def test_unmapped_project_returns_none(self, notch_config, user_settings, qapp):
        from overlay_window import ClaudeNotchOverlay
        from state_manager import StateManager

        user_settings.set("project_colors", {"other": "cyan"})
        sm = StateManager(notch_config, user_settings=user_settings)
        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            session = MagicMock()
            session.project_name = "myproj"
            result = overlay._get_project_color(session)
            assert result is None
        finally:
            overlay.close()

    def test_no_project_name_returns_none(self, notch_config, user_settings, qapp):
        from overlay_window import ClaudeNotchOverlay
        from state_manager import StateManager

        user_settings.set("project_colors", {"myproj": "cyan"})
        sm = StateManager(notch_config, user_settings=user_settings)
        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            session = MagicMock()
            session.project_name = ""
            result = overlay._get_project_color(session)
            assert result is None
        finally:
            overlay.close()

"""Tests for multi-monitor support (F1)."""

import pytest
from unittest.mock import MagicMock, patch


class TestTargetMonitorSetting:
    """Validate target_monitor setting in UserSettings."""

    def test_default_is_empty_string(self, user_settings, qapp):
        assert user_settings.get("target_monitor") == ""

    def test_accepts_string(self, user_settings, qapp):
        user_settings.set("target_monitor", "HDMI-1")
        assert user_settings.get("target_monitor") == "HDMI-1"

    def test_rejects_non_string(self, user_settings, qapp):
        user_settings.set("target_monitor", 42)
        assert user_settings.get("target_monitor") == ""

    def test_accepts_empty_string(self, user_settings, qapp):
        user_settings.set("target_monitor", "HDMI-1")
        user_settings.set("target_monitor", "")
        assert user_settings.get("target_monitor") == ""

    def test_round_trip_persistence(self, user_settings, qapp):
        """Set, save, reload from disk."""
        import json
        from user_settings import UserSettings, DEFAULTS
        from PySide6.QtCore import QObject

        user_settings.set("target_monitor", "DP-2")
        # Reload from the same file
        us2 = UserSettings.__new__(UserSettings)
        QObject.__init__(us2)
        us2.settings_dir = user_settings.settings_dir
        us2.settings_file = user_settings.settings_file
        us2._settings = dict(DEFAULTS)
        us2._load()
        assert us2.get("target_monitor") == "DP-2"


class TestGetTargetScreen:
    """Test _get_target_screen fallback behaviour."""

    def test_empty_setting_returns_primary(self, user_settings, notch_config, qapp):
        from overlay_window import ClaudeNotchOverlay
        from state_manager import StateManager
        from PySide6.QtGui import QGuiApplication

        sm = StateManager(notch_config, user_settings=user_settings)
        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            screen = overlay._get_target_screen()
            assert screen == QGuiApplication.primaryScreen()
        finally:
            overlay.close()

    def test_invalid_name_falls_back_to_primary(self, user_settings, notch_config, qapp):
        from overlay_window import ClaudeNotchOverlay
        from state_manager import StateManager
        from PySide6.QtGui import QGuiApplication

        user_settings.set("target_monitor", "NONEXISTENT_MONITOR_XYZ")
        sm = StateManager(notch_config, user_settings=user_settings)
        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            screen = overlay._get_target_screen()
            assert screen == QGuiApplication.primaryScreen()
        finally:
            overlay.close()

    def test_matching_screen_name_selected(self, user_settings, notch_config, qapp):
        from overlay_window import ClaudeNotchOverlay
        from state_manager import StateManager
        from PySide6.QtGui import QGuiApplication

        # Use the primary screen's actual name — should match itself
        primary = QGuiApplication.primaryScreen()
        user_settings.set("target_monitor", primary.name())

        sm = StateManager(notch_config, user_settings=user_settings)
        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            screen = overlay._get_target_screen()
            assert screen.name() == primary.name()
        finally:
            overlay.close()

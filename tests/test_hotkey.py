"""Unit tests for hotkey_manager."""

import pytest
from hotkey_manager import (
    parse_hotkey,
    validate_hotkey_string,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_ALT,
    MOD_NOREPEAT,
)
from user_settings import DEFAULTS


class TestParseHotkey:
    """Test hotkey string parsing."""

    def test_ctrl_shift_n(self):
        result = parse_hotkey("ctrl+shift+n")
        assert result is not None
        modifiers, vk = result
        assert modifiers == (MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT)
        assert vk == ord("N")

    def test_alt_shift_m(self):
        result = parse_hotkey("alt+shift+m")
        assert result is not None
        modifiers, vk = result
        assert modifiers == (MOD_ALT | MOD_SHIFT | MOD_NOREPEAT)
        assert vk == ord("M")

    def test_ctrl_alt_shift_k(self):
        result = parse_hotkey("ctrl+alt+shift+k")
        assert result is not None
        modifiers, vk = result
        assert modifiers == (MOD_CONTROL | MOD_ALT | MOD_SHIFT | MOD_NOREPEAT)
        assert vk == ord("K")

    def test_alt_f1(self):
        result = parse_hotkey("alt+f1")
        assert result is not None
        modifiers, vk = result
        assert modifiers == (MOD_ALT | MOD_NOREPEAT)
        assert vk == 0x70  # VK_F1

    def test_ctrl_f12(self):
        result = parse_hotkey("ctrl+f12")
        assert result is not None
        _, vk = result
        assert vk == 0x70 + 11  # VK_F12

    def test_ctrl_0(self):
        result = parse_hotkey("ctrl+0")
        assert result is not None
        _, vk = result
        assert vk == ord("0")

    def test_case_insensitive(self):
        result = parse_hotkey("Ctrl+Shift+N")
        assert result is not None
        modifiers, vk = result
        assert modifiers == (MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT)
        assert vk == ord("N")

    def test_whitespace_stripped(self):
        result = parse_hotkey("  ctrl+shift+n  ")
        assert result is not None

    def test_empty_string_returns_none(self):
        assert parse_hotkey("") is None

    def test_none_returns_none(self):
        assert parse_hotkey(None) is None

    def test_bare_key_returns_none(self):
        assert parse_hotkey("n") is None

    def test_no_key_returns_none(self):
        assert parse_hotkey("ctrl+shift+") is None

    def test_invalid_modifier(self):
        assert parse_hotkey("super+n") is None

    def test_invalid_key(self):
        assert parse_hotkey("ctrl+shift+!!") is None

    def test_multiple_keys(self):
        assert parse_hotkey("ctrl+a+b") is None


class TestValidateHotkeyString:
    """Test the validation helper."""

    def test_valid_hotkey(self):
        assert validate_hotkey_string("ctrl+shift+n") is True

    def test_empty_is_valid(self):
        assert validate_hotkey_string("") is True

    def test_non_string_invalid(self):
        assert validate_hotkey_string(123) is False

    def test_invalid_combo(self):
        assert validate_hotkey_string("just+letters") is False

    def test_f_key(self):
        assert validate_hotkey_string("alt+shift+f1") is True


class TestSettingsDefault:
    """Test that the global_hotkey default exists in DEFAULTS."""

    def test_default_exists(self):
        assert "global_hotkey" in DEFAULTS

    def test_default_value(self):
        assert DEFAULTS["global_hotkey"] == "ctrl+shift+n"


class TestHotkeyManagerCreation:
    """Test HotkeyManager creation doesn't crash."""

    def test_create_with_empty_hotkey(self, user_settings, qapp):
        """Manager with empty hotkey should not crash."""
        from hotkey_manager import HotkeyManager

        user_settings.set("global_hotkey", "")
        mgr = HotkeyManager(user_settings)
        mgr.cleanup()

    def test_create_with_invalid_hotkey(self, user_settings, qapp):
        """Manager with invalid hotkey should not crash."""
        from hotkey_manager import HotkeyManager

        user_settings._settings["global_hotkey"] = "garbage"
        mgr = HotkeyManager(user_settings)
        mgr.cleanup()

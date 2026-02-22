"""Tests for click-to-focus feature."""

import pytest


class TestClickToFocusSetting:
    def test_default_false(self, qapp, user_settings):
        assert user_settings.get("click_to_focus") is False

    def test_accepts_bool(self, qapp, user_settings):
        user_settings.set("click_to_focus", True)
        assert user_settings.get("click_to_focus") is True

    def test_rejects_non_bool(self, qapp, user_settings):
        user_settings.set("click_to_focus", "yes")
        assert user_settings.get("click_to_focus") is False  # unchanged


class TestWindowFocusModule:
    def test_find_terminal_hwnd_returns_none_for_invalid_pid(self):
        from window_focus import find_terminal_hwnd
        result = find_terminal_hwnd(99999999)
        assert result is None

    def test_focus_window_returns_false_for_invalid_hwnd(self):
        from window_focus import focus_window
        assert focus_window(0) is False

    def test_is_window_valid_false_for_zero(self):
        from window_focus import is_window_valid
        assert is_window_valid(0) is False

    def test_find_terminal_hwnd_type(self):
        """find_terminal_hwnd returns int or None."""
        from window_focus import find_terminal_hwnd
        import os
        result = find_terminal_hwnd(os.getpid())
        assert result is None or isinstance(result, int)


class TestSessionStateHwnd:
    def test_session_state_has_terminal_hwnd(self):
        from state_manager import SessionState
        s = SessionState(session_id="t1", project_path="/tmp/t", project_name="P")
        assert s.terminal_hwnd is None

    def test_session_state_hwnd_can_be_set(self):
        from state_manager import SessionState
        s = SessionState(session_id="t1", project_path="/tmp/t", project_name="P")
        s.terminal_hwnd = 12345
        assert s.terminal_hwnd == 12345


class TestHookPayloadIncludesPid:
    def test_hook_script_includes_pid(self):
        """Verify the hook script includes pid in its payload."""
        from pathlib import Path
        hook_path = Path(__file__).parent.parent / "hooks" / "notch-hook.py"
        content = hook_path.read_text()
        assert '"pid"' in content or "'pid'" in content
        assert "os.getppid()" in content

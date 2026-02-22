"""Unit tests for NotificationManager and related signal paths."""

import time
import pytest
from unittest.mock import MagicMock, patch
from state_manager import StateManager, NotchConfig
from notification_manager import NotificationManager, _COOLDOWN_SECONDS


@pytest.fixture
def state_manager(notch_config, qapp):
    """StateManager instance for testing."""
    return StateManager(notch_config)


@pytest.fixture
def notification_mgr(state_manager, user_settings, qapp):
    """NotificationManager wired to state_manager and user_settings."""
    return NotificationManager(state_manager, user_settings)


# ── Signal emission tests ────────────────────────────────────────


class TestErrorDetectedSignal:
    """Test error_detected signal emission from StateManager."""

    def test_bash_nonzero_exit_code_emits(self, state_manager, qapp):
        """Non-zero exit code in Bash toolResult emits error_detected."""
        received = []
        state_manager.error_detected.connect(lambda sid, tool: received.append((sid, tool)))

        state_manager.handle_event('hook', {
            'eventType': 'PreToolUse',
            'sessionId': 's1',
            'tool': 'Bash',
            'cwd': '/tmp',
        })
        state_manager.handle_event('hook', {
            'eventType': 'PostToolUse',
            'sessionId': 's1',
            'tool': 'Bash',
            'cwd': '/tmp',
            'toolResult': {'exitCode': 1, 'stdout': '', 'stderr': 'fail'},
        })

        assert len(received) == 1
        assert received[0] == ('s1', 'Bash')

    def test_bash_zero_exit_code_no_emit(self, state_manager, qapp):
        """Zero exit code does not emit error_detected."""
        received = []
        state_manager.error_detected.connect(lambda sid, tool: received.append((sid, tool)))

        state_manager.handle_event('hook', {
            'eventType': 'PostToolUse',
            'sessionId': 's1',
            'tool': 'Bash',
            'cwd': '/tmp',
            'toolResult': {'exitCode': 0, 'stdout': 'ok', 'stderr': ''},
        })

        assert len(received) == 0

    def test_bash_stderr_pattern_emits(self, state_manager, qapp):
        """Known error pattern in stderr emits error_detected even without exit code."""
        received = []
        state_manager.error_detected.connect(lambda sid, tool: received.append((sid, tool)))

        state_manager.handle_event('hook', {
            'eventType': 'PostToolUse',
            'sessionId': 's1',
            'tool': 'Bash',
            'cwd': '/tmp',
            'toolResult': {'stdout': '', 'stderr': 'bash: foo: command not found'},
        })

        assert len(received) == 1

    def test_bash_stdout_error_text_no_emit(self, state_manager, qapp):
        """Error-like text in stdout (not stderr) does NOT emit — reduces false positives."""
        received = []
        state_manager.error_detected.connect(lambda sid, tool: received.append((sid, tool)))

        state_manager.handle_event('hook', {
            'eventType': 'PostToolUse',
            'sessionId': 's1',
            'tool': 'Bash',
            'cwd': '/tmp',
            'toolResult': {'exitCode': 0, 'stdout': 'error: this is fine', 'stderr': ''},
        })

        assert len(received) == 0

    def test_non_bash_tool_no_error_check(self, state_manager, qapp):
        """PostToolUse for non-Bash tools does not emit error_detected."""
        received = []
        state_manager.error_detected.connect(lambda sid, tool: received.append((sid, tool)))

        state_manager.handle_event('hook', {
            'eventType': 'PostToolUse',
            'sessionId': 's1',
            'tool': 'Read',
            'cwd': '/tmp',
            'toolResult': {'exitCode': 1},
        })

        assert len(received) == 0

    def test_missing_tool_result_no_emit(self, state_manager, qapp):
        """Missing toolResult does not crash or emit."""
        received = []
        state_manager.error_detected.connect(lambda sid, tool: received.append((sid, tool)))

        state_manager.handle_event('hook', {
            'eventType': 'PostToolUse',
            'sessionId': 's1',
            'tool': 'Bash',
            'cwd': '/tmp',
        })

        assert len(received) == 0

    def test_string_tool_result_no_emit(self, state_manager, qapp):
        """String toolResult (unstructured) does not trigger heuristic scanning."""
        received = []
        state_manager.error_detected.connect(lambda sid, tool: received.append((sid, tool)))

        state_manager.handle_event('hook', {
            'eventType': 'PostToolUse',
            'sessionId': 's1',
            'tool': 'Bash',
            'cwd': '/tmp',
            'toolResult': 'error: something went wrong',
        })

        assert len(received) == 0


class TestAttentionNeededSignal:
    """Test attention_needed signal emission from StateManager."""

    def test_ask_user_question_emits(self, state_manager, qapp):
        """PreToolUse with AskUserQuestion tool emits attention_needed."""
        received = []
        state_manager.attention_needed.connect(lambda sid: received.append(sid))

        state_manager.handle_event('hook', {
            'eventType': 'PreToolUse',
            'sessionId': 's2',
            'tool': 'AskUserQuestion',
            'cwd': '/tmp',
        })

        assert received == ['s2']

    def test_other_tool_no_attention(self, state_manager, qapp):
        """PreToolUse with non-AskUserQuestion tool does not emit attention_needed."""
        received = []
        state_manager.attention_needed.connect(lambda sid: received.append(sid))

        state_manager.handle_event('hook', {
            'eventType': 'PreToolUse',
            'sessionId': 's2',
            'tool': 'Read',
            'cwd': '/tmp',
        })

        assert received == []


# ── NotificationManager cooldown tests ───────────────────────────


class TestCooldown:
    """Test cooldown behavior prevents sound spam."""

    def test_first_call_plays(self, notification_mgr, qapp):
        """First call to a sound type is not blocked by cooldown."""
        with patch('notification_manager.winsound') as mock_ws:
            notification_mgr.on_error('s1', 'Bash')
            mock_ws.MessageBeep.assert_called_once()

    def test_rapid_repeat_blocked(self, notification_mgr, qapp):
        """Second call within cooldown window is blocked."""
        with patch('notification_manager.winsound') as mock_ws:
            notification_mgr.on_error('s1', 'Bash')
            notification_mgr.on_error('s1', 'Bash')
            # Only one call despite two events
            assert mock_ws.MessageBeep.call_count == 1

    def test_different_types_independent(self, notification_mgr, qapp):
        """Different event types have independent cooldowns."""
        with patch('notification_manager.winsound') as mock_ws:
            notification_mgr.on_error('s1', 'Bash')
            notification_mgr.on_attention('s1')
            # Both should play — different cooldown keys
            assert mock_ws.MessageBeep.call_count == 2

    def test_cooldown_expires(self, notification_mgr, qapp, monkeypatch):
        """After cooldown expires, sound plays again."""
        call_count = 0

        def fake_beep(flag):
            nonlocal call_count
            call_count += 1

        with patch('notification_manager.winsound') as mock_ws:
            mock_ws.MessageBeep = fake_beep
            mock_ws.MB_ICONHAND = 0x10
            mock_ws.MB_ICONEXCLAMATION = 0x30
            mock_ws.MB_ICONASTERISK = 0x40

            notification_mgr.on_error('s1', 'Bash')
            assert call_count == 1

            # Simulate cooldown expiry by backdating the timestamp
            notification_mgr._cooldowns['error'] = time.time() - _COOLDOWN_SECONDS - 1

            notification_mgr.on_error('s1', 'Bash')
            assert call_count == 2


# ── NotificationManager settings gating ──────────────────────────


class TestSettingsGating:
    """Test that sounds/flash respect user settings."""

    def test_sounds_disabled_no_beep(self, notification_mgr, user_settings, qapp):
        """When sounds_enabled is False, no sound plays."""
        user_settings.set("sounds_enabled", False)
        with patch('notification_manager.winsound') as mock_ws:
            notification_mgr.on_error('s1', 'Bash')
            mock_ws.MessageBeep.assert_not_called()

    def test_flash_disabled_no_signal(self, notification_mgr, user_settings, qapp):
        """When error_flash_enabled is False, error_flash signal is not emitted."""
        user_settings.set("error_flash_enabled", False)
        received = []
        notification_mgr.error_flash.connect(lambda sid: received.append(sid))

        notification_mgr.on_error('s1', 'Bash')

        assert received == []

    def test_flash_enabled_emits_signal(self, notification_mgr, user_settings, qapp):
        """When error_flash_enabled is True, error_flash signal is emitted."""
        received = []
        notification_mgr.error_flash.connect(lambda sid: received.append(sid))

        with patch('notification_manager.winsound'):
            notification_mgr.on_error('s1', 'Bash')

        assert received == ['s1']

    def test_session_end_sound(self, notification_mgr, qapp):
        """Session end plays the asterisk sound."""
        with patch('notification_manager.winsound') as mock_ws:
            notification_mgr.on_session_end('s1')
            mock_ws.MessageBeep.assert_called_once()


# ── Settings migration tests ─────────────────────────────────────


class TestSettingsMigration:
    """Test that old settings files without new keys load correctly."""

    def test_old_settings_get_new_defaults(self, tmp_path, qapp):
        """Settings JSON missing sounds_enabled/error_flash_enabled still works."""
        import json
        from user_settings import UserSettings, DEFAULTS
        from PySide6.QtCore import QObject

        # Write an old-format settings file (missing new keys)
        old_settings = {
            "idle_timeout": 20,
            "activity_timeout": 90,
            "server_port": 27182,
            "launch_on_startup": False,
            "screen_position": "top-right",
            "background_opacity": 200,
            "auto_hide": True,
            "show_category_letter": True,
            "animation_speed_multiplier": 1.5,
            "animations_enabled": True,
        }
        settings_dir = tmp_path / "migration"
        settings_dir.mkdir()
        settings_file = settings_dir / "settings.json"
        settings_file.write_text(json.dumps(old_settings))

        # Load using UserSettings
        us = UserSettings.__new__(UserSettings)
        QObject.__init__(us)
        us.settings_dir = settings_dir
        us.settings_file = settings_file
        us._settings = dict(DEFAULTS)
        us._load()

        # Old values preserved
        assert us.get("idle_timeout") == 20
        assert us.get("animation_speed_multiplier") == 1.5
        # New keys get defaults
        assert us.get("sounds_enabled") is True
        assert us.get("error_flash_enabled") is True
        assert us.get("toasts_enabled") is True
        assert us.get("target_monitor") == ""
        assert us.get("project_colors") == {}


# ── Desktop toast tests (F3) ─────────────────────────────────────


class TestToastSignal:
    """Test toast_requested signal emission."""

    def test_toast_emitted_on_error(self, notification_mgr, qapp):
        """Error event emits toast_requested signal."""
        received = []
        notification_mgr.toast_requested.connect(lambda t, m, i: received.append((t, m, i)))

        with patch('notification_manager.winsound'):
            notification_mgr.on_error('s1', 'Bash')

        assert len(received) == 1
        assert received[0][0] == "Claude Code Error"
        assert "Bash" in received[0][1]

    def test_toast_emitted_on_attention(self, notification_mgr, qapp):
        """Attention event emits toast_requested signal."""
        received = []
        notification_mgr.toast_requested.connect(lambda t, m, i: received.append((t, m, i)))

        with patch('notification_manager.winsound'):
            notification_mgr.on_attention('s1')

        assert len(received) == 1
        assert "Attention" in received[0][1]

    def test_toast_emitted_on_session_end(self, notification_mgr, qapp):
        """Session end event emits toast_requested signal."""
        received = []
        notification_mgr.toast_requested.connect(lambda t, m, i: received.append((t, m, i)))

        with patch('notification_manager.winsound'):
            notification_mgr.on_session_end('s1')

        assert len(received) == 1
        assert "ended" in received[0][1]

    def test_toast_disabled_blocks_signal(self, notification_mgr, user_settings, qapp):
        """When toasts_enabled is False, toast_requested is not emitted."""
        user_settings.set("toasts_enabled", False)
        received = []
        notification_mgr.toast_requested.connect(lambda t, m, i: received.append((t, m, i)))

        with patch('notification_manager.winsound'):
            notification_mgr.on_error('s1', 'Bash')

        assert received == []

    def test_toasts_enabled_default(self, user_settings, qapp):
        """toasts_enabled defaults to True."""
        assert user_settings.get("toasts_enabled") is True

    def test_shared_cooldown_blocks_rapid_toast(self, notification_mgr, qapp):
        """Rapid duplicate events block both sound and toast."""
        received = []
        notification_mgr.toast_requested.connect(lambda t, m, i: received.append((t, m, i)))

        with patch('notification_manager.winsound'):
            notification_mgr.on_error('s1', 'Bash')
            notification_mgr.on_error('s1', 'Bash')

        # Only one toast despite two events
        assert len(received) == 1

    def test_sounds_disabled_toast_still_fires(self, notification_mgr, user_settings, qapp):
        """When sounds_enabled is False, toast still fires."""
        user_settings.set("sounds_enabled", False)
        received = []
        notification_mgr.toast_requested.connect(lambda t, m, i: received.append((t, m, i)))

        notification_mgr.on_error('s1', 'Bash')

        assert len(received) == 1

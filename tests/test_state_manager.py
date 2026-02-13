"""Unit tests for StateManager."""

import time
import pytest
from state_manager import StateManager, NotchConfig, ActiveTool, SessionState


class TestNotchConfig:
    """Tests for NotchConfig."""

    def test_load_config(self, notch_config):
        assert notch_config.categories
        assert notch_config.tools
        assert notch_config.patterns
        assert notch_config.colors

    def test_get_tool_info_known_tool(self, notch_config):
        info = notch_config.get_tool_info("Read")
        assert info["tool_name"] == "Read"
        assert info["category"]  # Whatever the config defines
        assert info["color"]
        assert info["pattern"]
        assert info["attention"]

    def test_get_tool_info_unknown_tool(self, notch_config):
        info = notch_config.get_tool_info("NonExistentTool")
        assert info["tool_name"] == "NonExistentTool"
        # Should use unknownTool defaults
        assert info["category"]

    def test_get_color_rgb(self, notch_config):
        rgb = notch_config.get_color_rgb("orange")
        assert isinstance(rgb, tuple)
        assert len(rgb) == 3
        assert all(0 <= c <= 255 for c in rgb)

    def test_get_color_rgb_unknown(self, notch_config):
        rgb = notch_config.get_color_rgb("nonexistent_color")
        # Falls back to orange
        assert isinstance(rgb, tuple)
        assert len(rgb) == 3

    def test_get_pattern_config(self, notch_config):
        config = notch_config.get_pattern_config("scan")
        assert "mode" in config

    def test_get_attention_config(self, notch_config):
        config = notch_config.get_attention_config("ambient")
        assert "opacity" in config

    def test_get_attention_config_unknown(self, notch_config):
        config = notch_config.get_attention_config("nonexistent")
        # Falls back to ambient
        assert "opacity" in config

    def test_duration_speed_mult_normal(self, notch_config):
        level, mult = notch_config.get_duration_speed_mult(0.0)
        assert level == "normal"
        assert mult == 1.0

    def test_duration_speed_mult_extended(self, notch_config):
        level, mult = notch_config.get_duration_speed_mult(10.0)
        assert level == "extended"
        assert mult < 1.0

    def test_duration_speed_mult_stuck(self, notch_config):
        level, mult = notch_config.get_duration_speed_mult(999.0)
        assert level == "stuck"
        assert mult <= 0.3


class TestStateManager:
    """Tests for StateManager event handling."""

    def test_create(self, qapp, notch_config):
        sm = StateManager(notch_config)
        assert sm.sessions == {}
        assert not sm.has_activity

    def test_handle_pre_tool_use(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test/project",
            "tool": "Read",
        })
        assert "s1" in sm.sessions
        session = sm.sessions["s1"]
        assert session.active_tool is not None
        assert session.active_tool.tool_name == "Read"
        assert session.active_tool.attention  # Should have attention set
        assert session.project_name == "project"

    def test_handle_post_tool_use_starts_grace(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Bash",
        })
        sm.handle_event("hook", {
            "eventType": "PostToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Bash",
        })
        session = sm.sessions["s1"]
        # Should be in grace period (synthetic thinking tool)
        assert session.active_tool is not None
        assert session.active_tool.tool_name == "_thinking"

    def test_handle_stop(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })
        sm.handle_event("hook", {
            "eventType": "Stop",
            "sessionId": "s1",
            "cwd": "C:/test",
        })
        session = sm.sessions["s1"]
        assert not session.is_active

    def test_handle_session_end(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "SessionStart",
            "sessionId": "s1",
            "cwd": "C:/test",
        })
        sm.handle_event("hook", {
            "eventType": "SessionEnd",
            "sessionId": "s1",
            "cwd": "C:/test",
        })
        session = sm.sessions["s1"]
        assert not session.is_active

    def test_handle_notification(self, qapp, notch_config):
        sm = StateManager(notch_config)
        received = []
        sm.notification_received.connect(lambda sid, msg: received.append((sid, msg)))
        sm.handle_event("hook", {
            "eventType": "Notification",
            "sessionId": "s1",
            "cwd": "C:/test",
            "toolInput": {"message": "Hello"},
        })
        assert len(received) == 1
        assert received[0] == ("s1", "Hello")

    def test_handle_notification_no_message(self, qapp, notch_config):
        sm = StateManager(notch_config)
        received = []
        sm.notification_received.connect(lambda sid, msg: received.append((sid, msg)))
        sm.handle_event("hook", {
            "eventType": "Notification",
            "sessionId": "s1",
            "cwd": "C:/test",
            "toolInput": {},
        })
        # Empty message, should not emit
        assert len(received) == 0

    def test_permission_mode_saved(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
            "permissionMode": "plan",
        })
        assert sm.sessions["s1"].permission_mode == "plan"

    def test_multiple_sessions(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test/alpha",
            "tool": "Read",
        })
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s2",
            "cwd": "C:/test/beta",
            "tool": "Bash",
        })
        assert len(sm.sessions) == 2
        assert sm.sessions["s1"].project_name == "alpha"
        assert sm.sessions["s2"].project_name == "beta"

    def test_cleanup_stale_sessions(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })
        session = sm.sessions["s1"]
        session.is_active = False
        session.active_tool = None
        session.last_activity = time.time() - 9999
        sm.cleanup_stale_sessions()
        assert "s1" not in sm.sessions

    def test_pinned_session_not_cleaned(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test/proj",
            "tool": "Read",
        })
        sm.pinned_paths.add("C:/test/proj")
        session = sm.sessions["s1"]
        session.is_active = False
        session.active_tool = None
        session.last_activity = time.time() - 9999
        sm.cleanup_stale_sessions()
        assert "s1" in sm.sessions  # pinned, not removed

    def test_get_status_dict(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })
        status = sm.get_status_dict()
        assert status["status"] == "running"
        assert status["session_count"] == 1
        assert len(status["sessions"]) == 1
        s = status["sessions"][0]
        assert s["session_id"] == "s1"
        assert s["active_tool"]["tool_name"] == "Read"

    def test_get_status_dict_empty(self, qapp, notch_config):
        sm = StateManager(notch_config)
        status = sm.get_status_dict()
        assert status["session_count"] == 0
        assert status["sessions"] == []

    def test_attention_field_on_active_tool(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Bash",
        })
        tool = sm.sessions["s1"].active_tool
        assert tool.attention in ("peripheral", "ambient", "focal", "urgent")

    def test_grace_period_uses_fun_verb(self, qapp, notch_config):
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })
        sm.handle_event("hook", {
            "eventType": "PostToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })
        tool = sm.sessions["s1"].active_tool
        assert tool.tool_name == "_thinking"
        assert tool.display_name in sm._fun_verbs


class TestActiveTool:
    """Tests for ActiveTool dataclass."""

    def test_defaults(self):
        tool = ActiveTool(tool_name="Read")
        assert tool.category == "think"
        assert tool.attention == "ambient"
        assert tool.started_at > 0

    def test_custom_attention(self):
        tool = ActiveTool(tool_name="Bash", attention="focal")
        assert tool.attention == "focal"


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_display_name_from_project(self):
        s = SessionState(session_id="s1", project_path="C:/work/myproj", project_name="myproj")
        assert s.display_name == "myproj"

    def test_status_text_idle(self):
        s = SessionState(session_id="s1", project_path="C:/work/proj", project_name="proj")
        assert "Idle" in s.status_text

    def test_status_text_active(self):
        s = SessionState(
            session_id="s1", project_path="C:/work/proj", project_name="proj",
            active_tool=ActiveTool(tool_name="Bash", display_name="Running")
        )
        assert "Running" in s.status_text

    def test_is_stale(self):
        s = SessionState(session_id="s1", project_path="", project_name="")
        s.last_activity = time.time() - 100
        assert s.is_stale

    def test_is_stale_at_custom(self):
        s = SessionState(session_id="s1", project_path="", project_name="")
        s.last_activity = time.time() - 30
        assert not s.is_stale_at(60)
        assert s.is_stale_at(20)

"""Tests for mini mode (compact single-line session cards)."""

import pytest
from state_manager import SessionState, ActiveTool


def _make_session(project="my-project", tool_name=None):
    """Create a SessionState, optionally with an active tool."""
    s = SessionState(session_id="test-1", project_path="/tmp/test", project_name=project)
    if tool_name:
        s.active_tool = ActiveTool(
            tool_name=tool_name,
            display_name=tool_name.title(),
            category="code",
            color="cyan",
            pattern="scan",
            attention="focused",
        )
    return s


class TestMiniModeSetting:
    """Validate mini_mode setting in UserSettings."""

    def test_setting_default_false(self, user_settings, qapp):
        assert user_settings.get("mini_mode") is False

    def test_setting_accepts_bool(self, user_settings, qapp):
        user_settings.set("mini_mode", True)
        assert user_settings.get("mini_mode") is True

    def test_setting_rejects_non_bool(self, user_settings, qapp):
        user_settings.set("mini_mode", "yes")
        assert user_settings.get("mini_mode") is False


class TestMiniSessionCard:
    """Validate MiniSessionCard rendering."""

    def test_mini_card_displays_project_name(self, qapp, notch_config):
        from overlay_window import MiniSessionCard

        session = _make_session(project="cool-app")
        card = MiniSessionCard(session, notch_config)
        assert card._project_label.text() == "cool-app"

    def test_mini_card_displays_tool_status(self, qapp, notch_config):
        from overlay_window import MiniSessionCard

        session = _make_session(tool_name="bash")
        card = MiniSessionCard(session, notch_config)
        assert card._status_label.text() == "Bash"

    def test_mini_card_shows_idle_when_no_tool(self, qapp, notch_config):
        from overlay_window import MiniSessionCard

        session = _make_session()
        card = MiniSessionCard(session, notch_config)
        assert card._status_label.text() == "Idle"

    def test_mini_card_update_animation_noop(self, qapp, notch_config):
        from overlay_window import MiniSessionCard

        session = _make_session(tool_name="bash")
        card = MiniSessionCard(session, notch_config)
        # Should not raise
        card.update_animation()


class TestOverlayCardType:
    """Verify overlay creates the correct card type based on mini_mode."""

    def test_overlay_uses_mini_cards_when_enabled(
        self, user_settings, notch_config, qapp
    ):
        from overlay_window import ClaudeNotchOverlay, MiniSessionCard
        from state_manager import StateManager

        user_settings.set("mini_mode", True)
        sm = StateManager(notch_config, user_settings=user_settings)

        # Inject a session so the overlay creates a card
        session = _make_session()
        sm.sessions[session.session_id] = session

        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            overlay._update_sessions()
            assert len(overlay.session_cards) == 1
            card = next(iter(overlay.session_cards.values()))
            assert isinstance(card, MiniSessionCard)
        finally:
            overlay.close()

    def test_overlay_uses_full_cards_when_disabled(
        self, user_settings, notch_config, qapp
    ):
        from overlay_window import ClaudeNotchOverlay, SessionCard
        from state_manager import StateManager

        # mini_mode defaults to False
        sm = StateManager(notch_config, user_settings=user_settings)

        session = _make_session()
        sm.sessions[session.session_id] = session

        overlay = ClaudeNotchOverlay(sm, user_settings=user_settings)
        try:
            overlay._update_sessions()
            assert len(overlay.session_cards) == 1
            card = next(iter(overlay.session_cards.values()))
            assert isinstance(card, SessionCard)
        finally:
            overlay.close()

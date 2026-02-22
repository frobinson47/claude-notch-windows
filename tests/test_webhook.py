"""Unit tests for webhook settings, dispatcher, and notification integration."""

import pytest
from unittest.mock import MagicMock, patch
from webhook_dispatcher import WebhookDispatcher
from notification_manager import NotificationManager


# ── Webhook settings tests ───────────────────────────────────────


class TestWebhookSettings:
    """Test webhook-related user settings defaults and validation."""

    def test_webhook_url_default_empty(self, user_settings, qapp):
        """webhook_url defaults to empty string."""
        assert user_settings.get("webhook_url") == ""

    def test_webhook_enabled_default_false(self, user_settings, qapp):
        """webhook_enabled defaults to False."""
        assert user_settings.get("webhook_enabled") is False

    def test_webhook_url_rejects_non_https(self, user_settings, qapp):
        """Setting a non-empty URL without 'https://' prefix is rejected."""
        user_settings.set("webhook_url", "http://example.com/hook")
        assert user_settings.get("webhook_url") == ""

        user_settings.set("webhook_url", "ftp://example.com/hook")
        assert user_settings.get("webhook_url") == ""

        user_settings.set("webhook_url", "not-a-url")
        assert user_settings.get("webhook_url") == ""

        # Valid https URL should be accepted
        user_settings.set("webhook_url", "https://example.com/hook")
        assert user_settings.get("webhook_url") == "https://example.com/hook"


# ── Webhook dispatcher tests ────────────────────────────────────


class TestWebhookDispatcher:
    """Test WebhookDispatcher format detection, send_test, and redaction."""

    def test_detect_discord_url(self):
        """URL containing 'discord.com/api/webhooks' detected as 'discord'."""
        wd = WebhookDispatcher()
        result = wd._detect_format("https://discord.com/api/webhooks/123/abc")
        assert result == "discord"

    def test_detect_slack_url(self):
        """URL containing 'hooks.slack.com' detected as 'slack'."""
        wd = WebhookDispatcher()
        result = wd._detect_format("https://hooks.slack.com/services/T00/B00/xxx")
        assert result == "slack"

    def test_detect_generic_url(self):
        """Other URL detected as 'generic'."""
        wd = WebhookDispatcher()
        result = wd._detect_format("https://example.com/my-webhook")
        assert result == "generic"

    def test_send_test_invalid_url(self):
        """send_test with invalid/unreachable URL returns (False, error_string)."""
        wd = WebhookDispatcher()
        success, message = wd.send_test("https://invalid.test.example.localhost/hook")
        assert success is False
        assert isinstance(message, str)
        assert len(message) > 0

    def test_redact_strips_paths(self):
        """_redact method strips full paths to just project name."""
        wd = WebhookDispatcher()

        # Windows path
        result = wd._redact(r"Error in C:\Users\admin\projects\my-project")
        assert "my-project" in result
        assert "Users" not in result
        assert "admin" not in result

        # Unix path
        result = wd._redact("Error in /home/user/projects/my-project")
        assert "my-project" in result
        assert "home" not in result
        assert "user" not in result


# ── NotificationManager webhook integration tests ───────────────


class TestNotificationManagerWebhook:
    """Test webhook dispatch from NotificationManager."""

    @pytest.fixture
    def state_manager(self, notch_config, qapp):
        """StateManager instance for testing."""
        from state_manager import StateManager
        return StateManager(notch_config)

    @pytest.fixture
    def notification_mgr(self, state_manager, user_settings, qapp):
        """NotificationManager wired to state_manager and user_settings."""
        return NotificationManager(state_manager, user_settings)

    def test_webhook_dispatched_on_error(self, notification_mgr, user_settings, qapp):
        """When webhook_enabled=True and webhook_url set, on_error calls _webhook.send."""
        user_settings.set("webhook_enabled", True)
        user_settings.set("webhook_url", "https://example.com/hook")

        with patch('notification_manager.winsound'):
            with patch.object(notification_mgr._webhook, 'send') as mock_send:
                notification_mgr.on_error('s1', 'Bash')
                mock_send.assert_called_once_with(
                    "error", "Claude Code Error", "Error in Bash"
                )

    def test_webhook_not_dispatched_when_disabled(self, notification_mgr, user_settings, qapp):
        """When webhook_enabled=False, on_error does NOT call _webhook.send."""
        user_settings.set("webhook_enabled", False)
        user_settings.set("webhook_url", "https://example.com/hook")

        with patch('notification_manager.winsound'):
            with patch.object(notification_mgr._webhook, 'send') as mock_send:
                notification_mgr.on_error('s1', 'Bash')
                mock_send.assert_not_called()

"""
Notification manager for Claude Code Notch.
Coordinates sound cues and error flash signals with debounce/cooldown.
"""

import logging
import time
import winsound
from PySide6.QtCore import QObject, Signal
from webhook_dispatcher import WebhookDispatcher

logger = logging.getLogger(__name__)

# Windows system sound mappings
_SOUND_MAP = {
    "attention": winsound.MB_ICONEXCLAMATION,
    "error": winsound.MB_ICONHAND,
    "session_end": winsound.MB_ICONASTERISK,
}

# Minimum seconds between repeated notifications of the same type
_COOLDOWN_SECONDS = 2.0

# QSystemTrayIcon.MessageIcon enum values (avoid importing QSystemTrayIcon here)
_TOAST_INFO = 1       # QSystemTrayIcon.Information
_TOAST_WARNING = 2    # QSystemTrayIcon.Warning
_TOAST_CRITICAL = 3   # QSystemTrayIcon.Critical


class NotificationManager(QObject):
    """Central notification coordinator for sound cues, error flashes, and desktop toasts."""

    error_flash = Signal(str)  # session_id — triggers red flash on overlay
    toast_requested = Signal(str, str, int)  # title, message, QSystemTrayIcon.MessageIcon int

    def __init__(self, state_manager, user_settings, parent=None):
        super().__init__(parent)
        self._user_settings = user_settings
        self._cooldowns: dict[str, float] = {}  # event_type -> last_played timestamp
        self._webhook = WebhookDispatcher()

        # Connect state manager signals
        state_manager.error_detected.connect(self.on_error)
        state_manager.attention_needed.connect(self.on_attention)
        state_manager.session_ended.connect(self.on_session_end)

    def _is_cooled_down(self, event_type: str) -> bool:
        """Check if enough time has passed since the last notification of this type."""
        now = time.time()
        last = self._cooldowns.get(event_type, 0.0)
        if now - last < _COOLDOWN_SECONDS:
            return False
        self._cooldowns[event_type] = now
        return True

    def _play_sound_unchecked(self, event_type: str):
        """Play a system sound if enabled (caller already checked cooldown)."""
        if not self._user_settings.get("sounds_enabled"):
            return
        sound_flag = _SOUND_MAP.get(event_type)
        if sound_flag is None:
            return
        try:
            winsound.MessageBeep(sound_flag)
        except Exception as e:
            logger.debug(f"Failed to play sound '{event_type}': {e}")

    def _emit_toast(self, title: str, message: str, icon_type: int):
        """Emit toast signal if toasts are enabled (caller already checked cooldown)."""
        if not self._user_settings.get("toasts_enabled"):
            return
        self.toast_requested.emit(title, message, icon_type)

    def _trigger_flash(self, session_id: str):
        """Emit error flash signal if enabled."""
        if not self._user_settings.get("error_flash_enabled"):
            return
        self.error_flash.emit(session_id)

    def _dispatch_webhook(self, event_type: str, title: str, message: str):
        """Send webhook notification if enabled and URL configured."""
        url = self._user_settings.get("webhook_url")
        if not self._user_settings.get("webhook_enabled") or not url:
            return
        self._webhook.url = url
        self._webhook.send(event_type, title, message)

    # ── Public slots ────────────────────────────────────────────

    def on_error(self, session_id: str, tool_name: str):
        """Handle error detection: play error sound + trigger red flash + toast."""
        if self._is_cooled_down("error"):
            self._play_sound_unchecked("error")
            self._emit_toast("Claude Code Error", f"Error in {tool_name}", _TOAST_CRITICAL)
            self._dispatch_webhook("error", "Claude Code Error", f"Error in {tool_name}")
        self._trigger_flash(session_id)

    def on_attention(self, session_id: str):
        """Handle attention-needed event: play attention sound + toast."""
        if self._is_cooled_down("attention"):
            self._play_sound_unchecked("attention")
            self._emit_toast("Claude Code", "Attention needed", _TOAST_WARNING)
            self._dispatch_webhook("attention", "Attention Needed", "User input required")

    def on_session_end(self, session_id: str):
        """Handle session end: play session-end sound + toast."""
        if self._is_cooled_down("session_end"):
            self._play_sound_unchecked("session_end")
            self._emit_toast("Claude Code", "Session ended", _TOAST_INFO)
            self._dispatch_webhook("session_end", "Session Ended", "Claude Code session ended")

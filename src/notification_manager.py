"""
Notification manager for Claude Code Notch.
Coordinates sound cues and error flash signals with debounce/cooldown.
"""

import logging
import time
import winsound
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

# Windows system sound mappings
_SOUND_MAP = {
    "attention": winsound.MB_ICONEXCLAMATION,
    "error": winsound.MB_ICONHAND,
    "session_end": winsound.MB_ICONASTERISK,
}

# Minimum seconds between repeated sounds of the same type
_COOLDOWN_SECONDS = 2.0


class NotificationManager(QObject):
    """Central notification coordinator for sound cues and error flashes."""

    error_flash = Signal(str)  # session_id — triggers red flash on overlay

    def __init__(self, state_manager, user_settings, parent=None):
        super().__init__(parent)
        self._user_settings = user_settings
        self._cooldowns: dict[str, float] = {}  # event_type -> last_played timestamp

        # Connect state manager signals
        state_manager.error_detected.connect(self.on_error)
        state_manager.attention_needed.connect(self.on_attention)
        state_manager.session_ended.connect(self.on_session_end)

    def _is_cooled_down(self, event_type: str) -> bool:
        """Check if enough time has passed since the last sound of this type."""
        now = time.time()
        last = self._cooldowns.get(event_type, 0.0)
        if now - last < _COOLDOWN_SECONDS:
            return False
        self._cooldowns[event_type] = now
        return True

    def _play_sound(self, event_type: str):
        """Play a system sound if enabled and not in cooldown."""
        if not self._user_settings.get("sounds_enabled"):
            return
        if not self._is_cooled_down(event_type):
            return
        sound_flag = _SOUND_MAP.get(event_type)
        if sound_flag is None:
            return
        try:
            winsound.MessageBeep(sound_flag)
        except Exception as e:
            logger.debug(f"Failed to play sound '{event_type}': {e}")

    def _trigger_flash(self, session_id: str):
        """Emit error flash signal if enabled."""
        if not self._user_settings.get("error_flash_enabled"):
            return
        self.error_flash.emit(session_id)

    # ── Public slots ────────────────────────────────────────────

    def on_error(self, session_id: str, tool_name: str):
        """Handle error detection: play error sound + trigger red flash."""
        self._play_sound("error")
        self._trigger_flash(session_id)

    def on_attention(self, session_id: str):
        """Handle attention-needed event: play attention sound."""
        self._play_sound("attention")

    def on_session_end(self, session_id: str):
        """Handle session end: play session-end sound."""
        self._play_sound("session_end")

"""
Global hotkey manager for Claude Code Notch.
Uses Win32 RegisterHotKey/UnregisterHotKey via ctypes — zero dependencies.
Runs a GetMessage loop in a daemon thread; bridges to Qt via Signal.
"""

import ctypes
import ctypes.wintypes
import logging
import re
import threading
from typing import Optional, Tuple

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

# Win32 constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
HOTKEY_ID = 1

_MODIFIER_MAP = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "alt": MOD_ALT,
}

# F1-F24 virtual key codes
_FKEY_MAP = {f"f{i}": 0x70 + (i - 1) for i in range(1, 25)}

# Regex for valid hotkey strings like "ctrl+shift+n", "alt+f1"
HOTKEY_PATTERN = re.compile(
    r"^(?:(?:ctrl|control|shift|alt)\+){1,3}(?:[a-z0-9]|f(?:[1-9]|1[0-9]|2[0-4]))$",
    re.IGNORECASE,
)


def parse_hotkey(hotkey_str: str) -> Optional[Tuple[int, int]]:
    """Parse a hotkey string into (modifiers, virtual_key_code).

    Returns None if the string is empty, invalid, or unparseable.

    Examples:
        "ctrl+shift+n"  -> (MOD_CONTROL | MOD_SHIFT, ord('N'))
        "alt+f1"        -> (MOD_ALT, 0x70)
        ""              -> None
    """
    if not hotkey_str or not hotkey_str.strip():
        return None

    hotkey_str = hotkey_str.strip().lower()
    if not HOTKEY_PATTERN.match(hotkey_str):
        return None

    parts = hotkey_str.split("+")
    key_part = parts[-1]
    modifier_parts = parts[:-1]

    # Build modifier bitmask
    modifiers = MOD_NOREPEAT
    for mod in modifier_parts:
        if mod not in _MODIFIER_MAP:
            return None
        modifiers |= _MODIFIER_MAP[mod]

    # Resolve virtual key code
    if key_part in _FKEY_MAP:
        vk = _FKEY_MAP[key_part]
    elif len(key_part) == 1 and key_part.isalnum():
        vk = ord(key_part.upper())
    else:
        return None

    return (modifiers, vk)


def validate_hotkey_string(value: str) -> bool:
    """Return True if value is a valid hotkey string or empty (disabled)."""
    if not isinstance(value, str):
        return False
    if value == "":
        return True
    return HOTKEY_PATTERN.match(value.strip()) is not None


class HotkeyManager(QObject):
    """Manages a single global hotkey via Win32 API.

    Emits ``hotkey_pressed`` on the Qt main thread when the hotkey fires.
    Registration failure is non-fatal — the app continues with tray-only toggle.
    """

    hotkey_pressed = Signal()

    def __init__(self, user_settings, parent=None):
        super().__init__(parent)
        self._user_settings = user_settings
        self._registered = False
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop_event = threading.Event()

        hotkey_str = self._user_settings.get("global_hotkey")
        self._register(hotkey_str)

    # ── Public API ────────────────────────────────────────────────

    def update_hotkey(self, hotkey_str: str):
        """Unregister old hotkey, register new one."""
        self._unregister()
        self._register(hotkey_str)

    def cleanup(self):
        """Unregister the hotkey and stop the listener thread."""
        self._unregister()

    # ── Internal ──────────────────────────────────────────────────

    def _register(self, hotkey_str: str):
        """Parse and register the hotkey, start the listener thread."""
        parsed = parse_hotkey(hotkey_str)
        if parsed is None:
            if hotkey_str:
                logger.warning(f"Invalid hotkey string: {hotkey_str!r}, hotkey disabled")
            else:
                logger.info("Global hotkey disabled (empty string)")
            return

        modifiers, vk = parsed
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listener_thread,
            args=(modifiers, vk),
            daemon=True,
            name="hotkey-listener",
        )
        self._thread.start()

    def _unregister(self):
        """Signal the listener thread to unregister and stop."""
        if self._thread is not None and self._thread.is_alive():
            self._stop_event.set()
            # Post WM_NULL to unblock GetMessage so the thread can exit
            if self._thread_id is not None:
                ctypes.windll.user32.PostThreadMessageW(
                    self._thread_id, 0x0000, 0, 0  # WM_NULL
                )
            self._thread.join(timeout=2.0)
            self._thread = None
            self._thread_id = None
        self._registered = False

    def _listener_thread(self, modifiers: int, vk: int):
        """Daemon thread: register hotkey, run GetMessage loop, unregister on exit."""
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        ok = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, modifiers, vk)
        if not ok:
            logger.warning(
                f"RegisterHotKey failed (key may be in use by another app). "
                f"modifiers=0x{modifiers:04x} vk=0x{vk:02x}"
            )
            self._registered = False
            return

        self._registered = True
        logger.info(f"Global hotkey registered: modifiers=0x{modifiers:04x} vk=0x{vk:02x}")

        msg = ctypes.wintypes.MSG()
        try:
            while not self._stop_event.is_set():
                ret = ctypes.windll.user32.GetMessageW(
                    ctypes.byref(msg), None, 0, 0
                )
                if ret <= 0:
                    break
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self.hotkey_pressed.emit()
        finally:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            self._registered = False
            logger.info("Global hotkey unregistered")

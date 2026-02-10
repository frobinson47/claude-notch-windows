"""
User settings persistence for Claude Code Notch.
Manages user preferences separately from the design config.
"""

import json
import logging
import os
import tempfile
import winreg
from pathlib import Path
from typing import Any, Dict, Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

DEFAULTS = {
    "idle_timeout": 15,
    "activity_timeout": 60,
    "server_port": 27182,
    "launch_on_startup": False,
    "screen_position": "top-right",
    "background_opacity": 220,
    "auto_hide": True,
    "show_category_letter": True,
    "animation_speed_multiplier": 1.0,
    "animations_enabled": True,
}

# Validation ranges for numeric settings
VALIDATION = {
    "idle_timeout": (5, 120),
    "activity_timeout": (10, 300),
    "server_port": (1024, 65535),
    "background_opacity": (0, 255),
    "animation_speed_multiplier": (0.25, 3.0),
}

VALID_POSITIONS = {"top-right", "top-left", "bottom-right", "bottom-left"}

STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = "ClaudeCodeNotch"


class UserSettings(QObject):
    """Manages user preferences with file persistence and change signals."""

    settings_changed = pyqtSignal(str)  # emits the key name that changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_dir = Path.home() / "AppData" / "Roaming" / "claude-notch-windows"
        self.settings_file = self.settings_dir / "settings.json"
        self._settings: Dict[str, Any] = dict(DEFAULTS)
        self._load()

    def _load(self):
        """Load settings from disk, falling back to defaults for missing/invalid keys."""
        if not self.settings_file.exists():
            logger.info("No settings file found, using defaults")
            return

        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load settings, using defaults: {e}")
            return

        if not isinstance(data, dict):
            logger.warning("Settings file is not a dict, using defaults")
            return

        for key, default in DEFAULTS.items():
            value = data.get(key, default)
            if self._validate(key, value):
                self._settings[key] = value
            else:
                logger.warning(f"Invalid value for {key}: {value!r}, using default {default!r}")
                self._settings[key] = default

    def _validate(self, key: str, value: Any) -> bool:
        """Validate a setting value."""
        default = DEFAULTS.get(key)
        if default is None:
            return False

        # Type check
        if isinstance(default, bool):
            return isinstance(value, bool)
        if isinstance(default, int) and not isinstance(default, bool):
            if not isinstance(value, int) or isinstance(value, bool):
                return False
        if isinstance(default, float):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False

        # Range check
        if key in VALIDATION:
            lo, hi = VALIDATION[key]
            return lo <= value <= hi

        if key == "screen_position":
            return value in VALID_POSITIONS

        return True

    def _save(self):
        """Atomically save settings to disk."""
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.settings_dir), suffix=".tmp", prefix="settings_"
            )
            with os.fdopen(fd, "w") as f:
                json.dump(self._settings, f, indent=2)
            # Atomic replace (Windows: os.replace works)
            os.replace(tmp_path, str(self.settings_file))
        except OSError as e:
            logger.error(f"Failed to save settings: {e}")
            # Clean up temp file if it still exists
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def get(self, key: str) -> Any:
        """Get a setting value."""
        return self._settings.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any):
        """Set a setting value, save to disk, and emit signal."""
        if key not in DEFAULTS:
            logger.warning(f"Unknown setting key: {key}")
            return
        if not self._validate(key, value):
            logger.warning(f"Invalid value for {key}: {value!r}")
            return
        old = self._settings.get(key)
        if old == value:
            return
        self._settings[key] = value
        self._save()
        logger.info(f"Setting changed: {key} = {value!r}")
        self.settings_changed.emit(key)

    def get_all(self) -> Dict[str, Any]:
        """Get a copy of all settings."""
        return dict(self._settings)

    def reset_to_defaults(self):
        """Reset all settings to defaults, save, and emit signals."""
        changed_keys = [k for k in DEFAULTS if self._settings.get(k) != DEFAULTS[k]]
        self._settings = dict(DEFAULTS)
        self._save()
        for key in changed_keys:
            self.settings_changed.emit(key)
        logger.info("Settings reset to defaults")

    # --- Windows startup helpers ---

    def get_startup_enabled(self) -> bool:
        """Check if launch-on-startup is registered in the Windows registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, STARTUP_REG_NAME)
                return True
        except FileNotFoundError:
            return False
        except OSError:
            return False

    def set_startup_enabled(self, enabled: bool):
        """Add or remove the app from Windows startup via registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    # Use the run.bat launcher
                    app_path = Path(__file__).parent.parent / "run.bat"
                    winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ, str(app_path))
                    logger.info(f"Added startup entry: {app_path}")
                else:
                    try:
                        winreg.DeleteValue(key, STARTUP_REG_NAME)
                        logger.info("Removed startup entry")
                    except FileNotFoundError:
                        pass
        except OSError as e:
            logger.error(f"Failed to update startup registry: {e}")

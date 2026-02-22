"""Shared fixtures for tests."""

import sys
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication (required for QObject/Signal tests)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def notch_config():
    """NotchConfig loaded from real config file."""
    from state_manager import NotchConfig
    return NotchConfig()


@pytest.fixture
def user_settings(tmp_path, qapp, monkeypatch):
    """UserSettings using a temp directory for isolation."""
    from user_settings import UserSettings, DEFAULTS
    from PySide6.QtCore import QObject, QTimer
    # Build instance without __init__ so it doesn't load real settings
    settings = UserSettings.__new__(UserSettings)
    QObject.__init__(settings)
    settings.settings_dir = tmp_path
    settings.settings_file = tmp_path / "settings.json"
    settings._settings = dict(DEFAULTS)
    # Debounce timer (matches __init__)
    settings._save_timer = QTimer(settings)
    settings._save_timer.setSingleShot(True)
    settings._save_timer.setInterval(500)
    settings._save_timer.timeout.connect(settings._save)
    return settings

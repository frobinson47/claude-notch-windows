"""Unit tests for UserSettings."""

import json
import pytest
from user_settings import UserSettings, DEFAULTS, VALIDATION, VALID_POSITIONS


class TestDefaults:
    """Test default values and retrieval."""

    def test_all_defaults_present(self, user_settings):
        for key, default in DEFAULTS.items():
            assert user_settings.get(key) == default

    def test_get_unknown_key(self, user_settings):
        assert user_settings.get("nonexistent_key") is None

    def test_get_all(self, user_settings):
        all_settings = user_settings.get_all()
        assert isinstance(all_settings, dict)
        assert all_settings == dict(DEFAULTS)
        # Ensure it's a copy
        all_settings["idle_timeout"] = 9999
        assert user_settings.get("idle_timeout") != 9999


class TestSetAndGet:
    """Test setting and getting values."""

    def test_set_valid_int(self, user_settings):
        user_settings.set("idle_timeout", 30)
        assert user_settings.get("idle_timeout") == 30

    def test_set_valid_bool(self, user_settings):
        user_settings.set("auto_hide", False)
        assert user_settings.get("auto_hide") is False

    def test_set_valid_float(self, user_settings):
        user_settings.set("animation_speed_multiplier", 2.0)
        assert user_settings.get("animation_speed_multiplier") == 2.0

    def test_set_valid_position(self, user_settings):
        user_settings.set("screen_position", "bottom-left")
        assert user_settings.get("screen_position") == "bottom-left"

    def test_set_no_change_no_save(self, user_settings):
        """Setting same value should not emit signal."""
        received = []
        user_settings.settings_changed.connect(lambda k: received.append(k))
        user_settings.set("idle_timeout", DEFAULTS["idle_timeout"])
        assert len(received) == 0

    def test_set_emits_signal(self, user_settings):
        received = []
        user_settings.settings_changed.connect(lambda k: received.append(k))
        user_settings.set("idle_timeout", 30)
        assert received == ["idle_timeout"]


class TestValidation:
    """Test validation rules."""

    def test_reject_out_of_range_int(self, user_settings):
        user_settings.set("idle_timeout", 1)  # Below minimum of 5
        assert user_settings.get("idle_timeout") == DEFAULTS["idle_timeout"]

    def test_reject_out_of_range_high(self, user_settings):
        user_settings.set("idle_timeout", 9999)  # Above maximum of 120
        assert user_settings.get("idle_timeout") == DEFAULTS["idle_timeout"]

    def test_reject_wrong_type_bool_for_int(self, user_settings):
        user_settings.set("idle_timeout", True)  # bool is not valid for int
        assert user_settings.get("idle_timeout") == DEFAULTS["idle_timeout"]

    def test_reject_wrong_type_str_for_int(self, user_settings):
        user_settings.set("idle_timeout", "thirty")
        assert user_settings.get("idle_timeout") == DEFAULTS["idle_timeout"]

    def test_reject_invalid_position(self, user_settings):
        user_settings.set("screen_position", "center")
        assert user_settings.get("screen_position") == DEFAULTS["screen_position"]

    def test_reject_unknown_key(self, user_settings):
        user_settings.set("nonexistent", 42)
        assert user_settings.get("nonexistent") is None

    def test_accept_boundary_values(self, user_settings):
        lo, hi = VALIDATION["idle_timeout"]
        user_settings.set("idle_timeout", lo)
        assert user_settings.get("idle_timeout") == lo
        user_settings.set("idle_timeout", hi)
        assert user_settings.get("idle_timeout") == hi

    def test_float_accepts_int(self, user_settings):
        """animation_speed_multiplier (float default) should accept int values."""
        user_settings.set("animation_speed_multiplier", 2)
        assert user_settings.get("animation_speed_multiplier") == 2


class TestPersistence:
    """Test saving and loading."""

    def test_save_and_load(self, tmp_path, qapp):
        from user_settings import UserSettings
        s1 = UserSettings()
        s1.settings_dir = tmp_path
        s1.settings_file = tmp_path / "settings.json"
        s1.set("idle_timeout", 42)

        # Create a new instance pointing at same file
        s2 = UserSettings()
        s2.settings_dir = tmp_path
        s2.settings_file = tmp_path / "settings.json"
        s2._settings = dict(DEFAULTS)
        s2._load()
        assert s2.get("idle_timeout") == 42

    def test_load_corrupted_file(self, tmp_path, qapp):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("not valid json{{{")
        s = UserSettings()
        s.settings_dir = tmp_path
        s.settings_file = settings_file
        s._settings = dict(DEFAULTS)
        s._load()
        # Should fall back to defaults
        assert s.get("idle_timeout") == DEFAULTS["idle_timeout"]

    def test_load_invalid_values_fall_back(self, tmp_path, qapp):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"idle_timeout": -1, "auto_hide": "yes"}))
        s = UserSettings()
        s.settings_dir = tmp_path
        s.settings_file = settings_file
        s._settings = dict(DEFAULTS)
        s._load()
        assert s.get("idle_timeout") == DEFAULTS["idle_timeout"]
        assert s.get("auto_hide") == DEFAULTS["auto_hide"]


class TestReset:
    """Test reset to defaults."""

    def test_reset_restores_defaults(self, user_settings):
        user_settings.set("idle_timeout", 99)
        user_settings.set("auto_hide", False)
        user_settings.reset_to_defaults()
        assert user_settings.get("idle_timeout") == DEFAULTS["idle_timeout"]
        assert user_settings.get("auto_hide") == DEFAULTS["auto_hide"]

    def test_reset_emits_signals(self, user_settings):
        user_settings.set("idle_timeout", 99)
        received = []
        user_settings.settings_changed.connect(lambda k: received.append(k))
        user_settings.reset_to_defaults()
        assert "idle_timeout" in received

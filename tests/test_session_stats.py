"""Tests for SessionStats and StateManager stats integration."""

import pytest


@pytest.fixture
def session_stats(tmp_path):
    from session_stats import SessionStats
    stats = SessionStats.__new__(SessionStats)
    stats.stats_dir = tmp_path
    stats.stats_file = tmp_path / "session_stats.json"
    stats._data = stats._default_data()
    return stats


class TestSessionStatsModule:
    def test_default_data(self, session_stats):
        data = session_stats.get_stats()
        assert data["schema_version"] == 1
        assert data["tool_counts"] == {}
        assert data["category_seconds"] == {}
        assert data["session_count"] == 0
        assert data["total_tool_uses"] == 0

    def test_record_tool_use(self, session_stats):
        session_stats.record_tool_use("Bash", "code", 5.0)
        data = session_stats.get_stats()
        assert data["tool_counts"]["Bash"] == 1
        assert data["category_seconds"]["code"] == 5.0
        assert data["total_tool_uses"] == 1

    def test_multiple_tool_uses_accumulate(self, session_stats):
        session_stats.record_tool_use("Bash", "code", 3.0)
        session_stats.record_tool_use("Bash", "code", 7.0)
        session_stats.record_tool_use("Read", "code", 2.0)
        data = session_stats.get_stats()
        assert data["tool_counts"]["Bash"] == 2
        assert data["tool_counts"]["Read"] == 1
        assert data["category_seconds"]["code"] == 12.0
        assert data["total_tool_uses"] == 3

    def test_increment_session_count(self, session_stats):
        session_stats.increment_session_count()
        session_stats.increment_session_count()
        assert session_stats.get_stats()["session_count"] == 2

    def test_persistence_round_trip(self, tmp_path):
        from session_stats import SessionStats
        s1 = SessionStats.__new__(SessionStats)
        s1.stats_dir = tmp_path
        s1.stats_file = tmp_path / "session_stats.json"
        s1._data = s1._default_data()
        s1.record_tool_use("Bash", "code", 5.0)

        # New instance from same path
        s2 = SessionStats.__new__(SessionStats)
        s2.stats_dir = tmp_path
        s2.stats_file = tmp_path / "session_stats.json"
        s2._data = s2._default_data()
        s2._load()
        assert s2.get_stats()["tool_counts"]["Bash"] == 1

    def test_schema_version_present(self, session_stats):
        assert session_stats.get_stats()["schema_version"] == 1

    def test_prune_stale_data(self, tmp_path):
        import time as _time
        from session_stats import SessionStats
        s = SessionStats.__new__(SessionStats)
        s.stats_dir = tmp_path
        s.stats_file = tmp_path / "session_stats.json"
        s._data = s._default_data()
        s._data["last_updated"] = _time.time() - (91 * 86400)  # 91 days ago
        s._data["tool_counts"]["Old"] = 10
        s._save()

        s2 = SessionStats.__new__(SessionStats)
        s2.stats_dir = tmp_path
        s2.stats_file = tmp_path / "session_stats.json"
        s2._data = s2._default_data()
        s2._load()
        assert s2.get_stats()["tool_counts"] == {}  # pruned

    def test_corrupted_file_resets(self, tmp_path):
        from session_stats import SessionStats
        (tmp_path / "session_stats.json").write_text("not json!!!")
        s = SessionStats.__new__(SessionStats)
        s.stats_dir = tmp_path
        s.stats_file = tmp_path / "session_stats.json"
        s._data = s._default_data()
        s._load()
        assert s.get_stats()["tool_counts"] == {}


class TestStateManagerStatsIntegration:
    def test_post_tool_use_records_stats(self, qapp, notch_config, user_settings, tmp_path):
        from state_manager import StateManager
        sm = StateManager(notch_config, user_settings=user_settings)
        # Redirect stats to tmp
        sm.session_stats.stats_dir = tmp_path
        sm.session_stats.stats_file = tmp_path / "session_stats.json"
        sm.session_stats._data = sm.session_stats._default_data()

        sm.handle_event('hook', {
            'eventType': 'PreToolUse',
            'sessionId': 's1',
            'cwd': '/tmp/test',
            'tool': 'Bash',
        })
        sm.handle_event('hook', {
            'eventType': 'PostToolUse',
            'sessionId': 's1',
            'cwd': '/tmp/test',
            'tool': 'Bash',
        })
        data = sm.session_stats.get_stats()
        assert data["tool_counts"].get("Bash", 0) >= 1

    def test_thinking_tool_excluded(self, qapp, notch_config, user_settings, tmp_path):
        from state_manager import StateManager
        sm = StateManager(notch_config, user_settings=user_settings)
        sm.session_stats.stats_dir = tmp_path
        sm.session_stats.stats_file = tmp_path / "session_stats.json"
        sm.session_stats._data = sm.session_stats._default_data()

        # Simulate a Stop event which triggers _thinking grace period
        sm.handle_event('hook', {
            'eventType': 'PreToolUse',
            'sessionId': 's1',
            'cwd': '/tmp/test',
            'tool': 'Bash',
        })
        sm.handle_event('hook', {
            'eventType': 'Stop',
            'sessionId': 's1',
            'cwd': '/tmp/test',
        })
        data = sm.session_stats.get_stats()
        assert "_thinking" not in data["tool_counts"]

    def test_session_end_increments_count(self, qapp, notch_config, user_settings, tmp_path):
        from state_manager import StateManager
        sm = StateManager(notch_config, user_settings=user_settings)
        sm.session_stats.stats_dir = tmp_path
        sm.session_stats.stats_file = tmp_path / "session_stats.json"
        sm.session_stats._data = sm.session_stats._default_data()

        sm.handle_event('hook', {
            'eventType': 'SessionStart',
            'sessionId': 's1',
            'cwd': '/tmp/test',
        })
        sm.handle_event('hook', {
            'eventType': 'SessionEnd',
            'sessionId': 's1',
            'cwd': '/tmp/test',
        })
        assert sm.session_stats.get_stats()["session_count"] == 1

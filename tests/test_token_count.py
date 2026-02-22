"""Tests for token counting: transcript parsing, throttling, and context percent."""

import json
import time
import threading
from unittest.mock import patch, MagicMock

import pytest
from state_manager import StateManager, SessionState


class TestTranscriptParsing:
    """Tests for _read_transcript JSONL parsing."""

    def test_reads_last_usage(self, qapp, notch_config, tmp_path):
        """With 2 assistant messages, the LAST usage values are used."""
        sm = StateManager(notch_config)
        # Create a session so _apply_token_update can find it
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            {"type": "user", "message": {"role": "user", "content": "hello"}},
            {"type": "assistant", "message": {"role": "assistant", "usage": {
                "input_tokens": 100, "output_tokens": 50,
                "cache_creation_input_tokens": 10, "cache_read_input_tokens": 20,
            }}},
            {"type": "user", "message": {"role": "user", "content": "world"}},
            {"type": "assistant", "message": {"role": "assistant", "usage": {
                "input_tokens": 500, "output_tokens": 150,
                "cache_creation_input_tokens": 100, "cache_read_input_tokens": 600,
            }}},
        ]
        transcript.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")

        sm._read_transcript("s1", str(transcript))
        # Allow signal to be processed by Qt event loop
        qapp.processEvents()
        time.sleep(0.1)
        qapp.processEvents()

        session = sm.sessions["s1"]
        assert session.token_stats.input_tokens == 500
        assert session.token_stats.output_tokens == 150
        assert session.token_stats.cache_creation_tokens == 100
        assert session.token_stats.cache_read_tokens == 600

    def test_empty_transcript(self, qapp, notch_config, tmp_path):
        """Empty file does not crash."""
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })

        transcript = tmp_path / "empty.jsonl"
        transcript.write_text("", encoding="utf-8")

        # Should not raise
        sm._read_transcript("s1", str(transcript))
        qapp.processEvents()

        # Token stats should remain at defaults (0)
        session = sm.sessions["s1"]
        assert session.token_stats.input_tokens == 0
        assert session.token_stats.output_tokens == 0

    def test_missing_file(self, qapp, notch_config):
        """Nonexistent path does not crash."""
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })

        # Should not raise even with a bogus path
        sm._read_transcript("s1", "C:/nonexistent/path/transcript.jsonl")
        qapp.processEvents()

        session = sm.sessions["s1"]
        assert session.token_stats.input_tokens == 0

    def test_no_usage_in_messages(self, qapp, notch_config, tmp_path):
        """Transcript with only user-type messages does not crash."""
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })

        transcript = tmp_path / "no_usage.jsonl"
        lines = [
            {"type": "user", "message": {"role": "user", "content": "hello"}},
            {"type": "user", "message": {"role": "user", "content": "world"}},
        ]
        transcript.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")

        # Should not raise
        sm._read_transcript("s1", str(transcript))
        qapp.processEvents()

        session = sm.sessions["s1"]
        assert session.token_stats.input_tokens == 0
        assert session.token_stats.output_tokens == 0


class TestTokenThrottling:
    """Tests for _update_token_usage throttling logic."""

    def test_throttle_skips_rapid_reads(self, qapp, notch_config, tmp_path):
        """If last_token_read_time is recent, no thread is spawned."""
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })
        session = sm.sessions["s1"]
        # Set last read to just now (within the 5s throttle window)
        session.last_token_read_time = time.time()

        with patch("threading.Thread") as mock_thread:
            sm._update_token_usage(session, {"transcriptPath": str(tmp_path / "t.jsonl")})
            mock_thread.assert_not_called()

    def test_throttle_allows_after_delay(self, qapp, notch_config, tmp_path):
        """If last_token_read_time is old enough, a thread IS spawned."""
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })
        session = sm.sessions["s1"]
        # Set last read to 10 seconds ago (past the 5s throttle window)
        session.last_token_read_time = time.time() - 10

        with patch("state_manager.threading.Thread") as mock_thread:
            mock_instance = MagicMock()
            mock_thread.return_value = mock_instance
            sm._update_token_usage(session, {"transcriptPath": str(tmp_path / "t.jsonl")})
            mock_thread.assert_called_once()
            mock_instance.start.assert_called_once()


class TestContextPercent:
    """Tests for _apply_token_update context percentage calculation."""

    def test_context_percent_calculated(self, qapp, notch_config):
        """input_tokens=100000 should yield context_percent ~ 50.0."""
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })

        # Call _apply_token_update directly (main-thread slot)
        sm._apply_token_update("s1", 100000, 0, 0, 0)

        session = sm.sessions["s1"]
        assert abs(session.context_percent - 50.0) < 0.1

    def test_context_percent_capped_at_100(self, qapp, notch_config):
        """input_tokens=300000 should yield context_percent == 100.0 (capped)."""
        sm = StateManager(notch_config)
        sm.handle_event("hook", {
            "eventType": "PreToolUse",
            "sessionId": "s1",
            "cwd": "C:/test",
            "tool": "Read",
        })

        sm._apply_token_update("s1", 300000, 0, 0, 0)

        session = sm.sessions["s1"]
        assert session.context_percent == 100.0

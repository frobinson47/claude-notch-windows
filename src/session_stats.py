import json
import logging
import os
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
PRUNE_AFTER_DAYS = 90


class SessionStats:
    def __init__(self):
        self.stats_dir = Path.home() / "AppData" / "Roaming" / "claude-notch-windows"
        self.stats_file = self.stats_dir / "session_stats.json"
        self._data = self._default_data()
        self._load()

    def _default_data(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "tool_counts": {},
            "category_seconds": {},
            "session_count": 0,
            "total_tool_uses": 0,
            "first_recorded": None,
            "last_updated": None,
        }

    def _load(self):
        if not self.stats_file.exists():
            return
        try:
            with open(self.stats_file, "r") as f:
                data = json.load(f)
            if data.get("schema_version") != SCHEMA_VERSION:
                logger.warning("session_stats.json schema mismatch, resetting")
                return
            self._data = data
            self._prune_if_stale()
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load session stats: {e}")

    def _save(self):
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(self.stats_dir), suffix=".tmp", prefix="stats_")
            with os.fdopen(fd, "w") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp_path, str(self.stats_file))
        except OSError as e:
            logger.error(f"Failed to save session stats: {e}")
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _prune_if_stale(self):
        last_updated = self._data.get("last_updated")
        if last_updated is None:
            return
        age_days = (time.time() - last_updated) / 86400
        if age_days > PRUNE_AFTER_DAYS:
            logger.info("session_stats older than 90 days, resetting")
            self._data = self._default_data()
            self._save()

    def record_tool_use(self, tool_name: str, category: str, duration_seconds: float):
        now = time.time()
        counts = self._data["tool_counts"]
        counts[tool_name] = counts.get(tool_name, 0) + 1

        cat_secs = self._data["category_seconds"]
        cat_secs[category] = cat_secs.get(category, 0.0) + duration_seconds

        self._data["total_tool_uses"] += 1
        self._data["last_updated"] = now
        if self._data["first_recorded"] is None:
            self._data["first_recorded"] = now

        self._save()

    def increment_session_count(self):
        now = time.time()
        self._data["session_count"] += 1
        self._data["last_updated"] = now
        if self._data["first_recorded"] is None:
            self._data["first_recorded"] = now
        self._save()

    def get_stats(self) -> dict:
        return dict(self._data)

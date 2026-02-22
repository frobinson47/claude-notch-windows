"""
Webhook dispatcher for Claude Code Notch.
Sends event payloads to Discord/Slack webhooks asynchronously.
No Qt dependency — uses only stdlib (urllib.request, threading, json, logging, time).
"""

import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

# Minimum seconds between webhook sends (rate limit)
_RATE_LIMIT_SECONDS = 5.0

# Maximum Retry-After delay we will honor (seconds)
_MAX_RETRY_AFTER = 30

# Discord embed color mapping
_DISCORD_COLORS = {
    "error": 0xFF0000,
    "attention": 0xFFA500,
    "session_end": 0x4A9EFF,
}

# Default Discord embed color for unknown event types
_DISCORD_COLOR_DEFAULT = 0x808080


class WebhookDispatcher:
    """Dispatches event payloads to Discord/Slack webhooks without blocking."""

    def __init__(self):
        self._url: str = ""
        self._last_send_time: float = 0.0
        self._lock = threading.Lock()

    # ── url property ────────────────────────────────────────────────

    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, value: str) -> None:
        self._url = value.strip() if value else ""

    # ── public API ──────────────────────────────────────────────────

    def send(self, event_type: str, title: str, message: str, project: str = "") -> None:
        """Fire-and-forget async send.  Never blocks the caller."""
        url = self._url
        if not url:
            return

        with self._lock:
            now = time.monotonic()
            if now - self._last_send_time < _RATE_LIMIT_SECONDS:
                logger.debug("Webhook rate-limited, dropping event %s", event_type)
                return
            self._last_send_time = now

        t = threading.Thread(
            target=self._do_send,
            args=(url, event_type, title, message, project),
            daemon=True,
        )
        t.start()

    def send_test(self, url: str) -> tuple:
        """Synchronous test send.  Returns (True, 'OK') or (False, 'error message')."""
        fmt = self._detect_format(url)
        payload = self._build_payload(
            event_type="test",
            title="Webhook Test",
            message="If you see this, the webhook is configured correctly.",
            project="claude-notch",
            fmt=fmt,
        )
        try:
            self._post(url, payload)
            return (True, "OK")
        except Exception as exc:
            return (False, str(exc))

    # ── format detection ────────────────────────────────────────────

    def _detect_format(self, url: str) -> str:
        """Return 'discord', 'slack', or 'generic' based on URL pattern."""
        if "discord.com/api/webhooks" in url:
            return "discord"
        if "hooks.slack.com" in url:
            return "slack"
        return "generic"

    # ── payload building ────────────────────────────────────────────

    def _build_payload(self, event_type: str, title: str, message: str,
                       project: str, fmt: str) -> dict:
        """Build the formatted payload dict for the detected webhook format."""
        safe_title = self._redact(title)
        safe_message = self._redact(message)
        safe_project = self._redact(project)

        if fmt == "discord":
            color = _DISCORD_COLORS.get(event_type, _DISCORD_COLOR_DEFAULT)
            return {
                "content": safe_message,
                "embeds": [
                    {
                        "title": safe_title,
                        "description": safe_message,
                        "color": color,
                    }
                ],
            }

        if fmt == "slack":
            return {"text": f"{safe_title}: {safe_message}"}

        # generic
        return {
            "event_type": event_type,
            "title": safe_title,
            "message": safe_message,
            "project": safe_project,
        }

    # ── redaction ───────────────────────────────────────────────────

    def _redact(self, text: str) -> str:
        """Strip full filesystem paths to their final component and truncate
        long hex-like IDs (session IDs) to the first 8 characters."""
        if not text:
            return text

        # Replace Windows and Unix absolute paths with just the final component.
        # Matches sequences like C:\Users\foo\bar\project or /home/user/project
        text = re.sub(
            r'[A-Za-z]:[\\\/](?:[^\\\/\s]+[\\\/])+([^\\\/\s]+)',
            r'\1',
            text,
        )
        text = re.sub(
            r'\/(?:[^\/\s]+\/)+([^\/\s]+)',
            r'\1',
            text,
        )

        # Truncate long hex IDs (16+ hex chars) to first 8 chars
        text = re.sub(
            r'\b([0-9a-fA-F]{8})[0-9a-fA-F]{8,}\b',
            r'\1...',
            text,
        )

        return text

    # ── internal send logic ─────────────────────────────────────────

    def _do_send(self, url: str, event_type: str, title: str,
                 message: str, project: str) -> None:
        """Background thread target: build payload and POST."""
        fmt = self._detect_format(url)
        payload = self._build_payload(event_type, title, message, project, fmt)
        try:
            self._post(url, payload)
            logger.debug("Webhook sent: %s -> %s", event_type, fmt)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                self._handle_429(url, payload, exc)
            else:
                logger.warning("Webhook HTTP error %s: %s", exc.code, exc.reason)
        except Exception as exc:
            logger.warning("Webhook send failed: %s", exc)

    def _handle_429(self, url: str, payload: dict, exc: urllib.error.HTTPError) -> None:
        """Retry once after honouring the Retry-After header."""
        retry_after = _RATE_LIMIT_SECONDS
        try:
            header_val = exc.headers.get("Retry-After", "")
            if header_val:
                retry_after = min(float(header_val), _MAX_RETRY_AFTER)
        except (ValueError, TypeError):
            pass

        logger.info("Webhook 429 — retrying after %.1fs", retry_after)
        time.sleep(retry_after)

        try:
            self._post(url, payload)
            logger.debug("Webhook retry succeeded")
        except Exception as retry_exc:
            logger.warning("Webhook retry failed: %s", retry_exc)

    @staticmethod
    def _post(url: str, payload: dict) -> None:
        """Send a JSON POST request to *url*."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ClaudeNotch/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()  # drain response body

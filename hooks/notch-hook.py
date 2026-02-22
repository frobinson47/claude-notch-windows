"""
Claude Code Notch Hook (Python version)
Sends hook events to the Windows Notch app via HTTP.

~50-200ms startup vs 500-2000ms for PowerShell.
"""
import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        return

    if not raw or not raw.strip():
        return

    try:
        hook_data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return

    payload = json.dumps({
        "eventType": hook_data.get("hook_event_name", ""),
        "sessionId": hook_data.get("session_id", ""),
        "cwd": hook_data.get("cwd", ""),
        "pid": os.getppid(),
        "tool": hook_data.get("tool_name", ""),
        "toolInput": hook_data.get("tool_input"),
        "toolOutput": hook_data.get("tool_output"),
        "transcriptPath": hook_data.get("transcript_path", ""),
        "permissionMode": hook_data.get("permission_mode", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }).encode("utf-8")

    try:
        req = Request(
            "http://localhost:27182/hook",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urlopen(req, timeout=2)
    except Exception:
        pass  # Silently fail if server not running


if __name__ == "__main__":
    main()

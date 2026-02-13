"""
Send-to-Notch Command (Python version)
Pins the current session to the Windows Notch display.
"""
import json
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        return

    try:
        hook_data = json.loads(raw) if raw and raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        hook_data = {}

    payload = json.dumps({
        "sessionId": hook_data.get("session_id", ""),
        "cwd": hook_data.get("cwd", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }).encode("utf-8")

    try:
        req = Request(
            "http://localhost:27182/pin",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urlopen(req, timeout=2)
        print("Session pinned to Notch display")
    except Exception:
        print("Error: Notch app not running")


if __name__ == "__main__":
    main()

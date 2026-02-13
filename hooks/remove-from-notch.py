"""
Remove-from-Notch Command (Python version)
Unpins all sessions from the Windows Notch display.
"""
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

def main():
    payload = json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }).encode("utf-8")

    try:
        req = Request(
            "http://localhost:27182/unpin",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urlopen(req, timeout=2)
        print("All sessions unpinned from Notch display")
    except Exception:
        print("Error: Notch app not running")


if __name__ == "__main__":
    main()

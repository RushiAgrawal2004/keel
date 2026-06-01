from __future__ import annotations

import json
from pathlib import Path
from urllib import request

from .memory import list_events


def send_governance_webhook(repo_path: Path, url: str, event_type: str = "keel.export") -> dict:
    payload = {
        "type": event_type,
        "project": repo_path.name,
        "events": list_events(repo_path, limit=100),
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "keel/0.1.0"},
        method="POST",
    )
    with request.urlopen(req, timeout=15) as response:
        body = response.read().decode("utf-8", errors="replace")
        return {
            "status": response.status,
            "reason": response.reason,
            "body": body,
        }


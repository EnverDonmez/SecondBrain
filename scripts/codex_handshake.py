"""No thread listing/history read. Only initialize the installed official CLI."""

import json
from pathlib import Path

from second_brain.app_server import AppServerConnection

with AppServerConnection() as server:
    report = {
        "status": "verified",
        "operation": "initialize / initialized only",
        "private_threads_read": 0,
        "model_turns_started": 0,
        "result_fields": sorted(server.info),
        "user_agent": server.info.get("userAgent"),
    }
Path("reports/codex-handshake.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))

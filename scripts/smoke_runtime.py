"""Read-only smoke test of the real loopback service. Never prints the owner key."""

import json
from pathlib import Path

import httpx

root = Path(__file__).resolve().parent.parent
with httpx.Client(base_url="http://127.0.0.1:8765", timeout=15, trust_env=False) as client:
    public = client.get("/healthz")
    public.raise_for_status()
    assert public.json()["application"] == "second-brain-os"
    assert client.get("/api/status").status_code == 403
    client.headers["Authorization"] = "Bearer " + (root / "data/owner.token").read_text().strip()
    status = client.get("/api/status")
    status.raise_for_status()
    media = client.get("/api/media/capabilities")
    media.raise_for_status()
    diagnostics = client.get("/api/diagnostics")
    diagnostics.raise_for_status()
    assert diagnostics.json()["integrity"]["quick_check"] == "ok"
    schema = client.get("/api/openapi.json")
    schema.raise_for_status()
    assert "/api/assets/{identity}/process" in schema.json()["paths"]
    result = {
        "url": str(client.base_url),
        "health": public.json(),
        "authentication_required": True,
        "counts": status.json()["counts"],
        "runtime": status.json()["runtime"],
        "media": media.json(),
        "integrity": diagnostics.json()["integrity"],
        "personal_records_written_by_test": 0,
    }
(root / "reports/local-runtime.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))

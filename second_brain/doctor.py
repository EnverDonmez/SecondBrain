"""Read-only local diagnostics; does not create a brain or expose credentials."""

import sqlite3
from contextlib import closing
from pathlib import Path

import httpx

from . import __version__
from .credentials import client_token
from .service import service_health, validate_service


def diagnose(root, port=8765):
    root = Path(root).resolve()
    checks = []

    def add(name, ok, detail):
        checks.append({"name": name, "ok": ok, "detail": detail})

    path = root / "brain.sqlite3"
    if not path.is_file():
        add("database", False, "No database yet. Start the service to initialize it.")
    else:
        try:
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)) as con:
                integrity = con.execute("PRAGMA quick_check").fetchone()[0]
                schema = con.execute("PRAGMA user_version").fetchone()[0]
                expected = len(list((Path(__file__).parent / "migrations").glob("*.sql")))
                add("database", integrity == "ok", integrity)
                add("schema", schema == expected, {"current": schema, "expected": expected})
        except sqlite3.Error:
            add("database", False, "Cannot read the database; check permissions and integrity.")
    add("owner_key", (root / "owner.token").is_file(), "Key contents are never included.")
    try:
        health = service_health(port)
        if health:
            validate_service(health, root)
        add(
            "service",
            health is not None,
            "Ready" if health else "Offline. Run scripts/Start.ps1 -Background.",
        )
    except (RuntimeError, ValueError) as exc:
        health = None
        add("service", False, str(exc))
    try:
        token = client_token()
        # The managed local connection is discoverable without opening host configuration.
        managed = root / "connections/codex/client.token"
        if not token and managed.is_file():
            token = managed.read_text("utf-8").strip() if managed.stat().st_size <= 4096 else ""
        if token and health:
            with httpx.Client(trust_env=False, timeout=5) as client:
                response = client.post(
                    f"http://127.0.0.1:{port}/api/action/brain.prepare_context",
                    headers={"Authorization": "Bearer " + token},
                    json={"query": "connection health", "budget": 512},
                )
            add("client_connection", response.status_code == 200, {"http_status": response.status_code})
        else:
            add("client_connection", False, "Start the service and configure a restricted client token.")
    except (OSError, ValueError, httpx.HTTPError):
        add("client_connection", False, "Cannot read the restricted token or contact the service.")
    return {"version": __version__, "ready": all(c["ok"] for c in checks), "checks": checks}

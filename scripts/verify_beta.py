"""Actual HTTP/stdio beta acceptance, isolated from the user's data directory."""

import asyncio
import hashlib
import json
import os
import signal
import secrets
import socket
import sys
import tempfile
import time
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import second_brain
from second_brain.models import now
from second_brain.service import ensure_service, instance_id, service_health
from second_brain.tool_surface import CORE_TOOLS


def payload(result):
    assert not result.is_error, str(result.content)
    return result.structured_content or json.loads(
        "".join(x.text for x in result.content if x.type == "text")
    )


def stop_synthetic(root, port):
    health = service_health(port)
    if health is None:
        return
    assert health["instance_id"] == instance_id(root)
    os.kill(health["pid"], signal.SIGTERM)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if service_health(port) is None:
            return
        time.sleep(0.1)
    raise AssertionError("Synthetic process did not stop")


async def scenario(root, port):
    started = ensure_service(root, port)
    assert started["started"] and not ensure_service(root, port)["started"]
    # Each request reconnects because this scenario deliberately kills the service.
    with httpx.Client(
        base_url=started["url"], trust_env=False, timeout=30, limits=httpx.Limits(max_keepalive_connections=0)
    ) as api:
        assert api.get("/api/status").status_code == 403
        assert api.get("/").status_code == 200
        for name in ("app.js", "style.css"):
            assert api.get("/static/" + name).status_code == 200
        login = api.post("/api/login", json={"token": (root / "owner.token").read_text("utf-8")})
        assert login.status_code == 200 and "HttpOnly" in login.headers["set-cookie"]
        api.headers["X-Brain-Request"] = "1"
        issued = api.post(
            "/api/tokens",
            json={
                "name": "synthetic-beta",
                "principal": {
                    "id": "synthetic-beta",
                    "role": "agent",
                    "scopes": ["global", "beta"],
                    "permissions": ["read", "propose", "capture"],
                    "clearance": 1,
                },
            },
        )
        assert issued.status_code == 200
        token = issued.json()["token"]
        token_file = root / "connections/codex/client.token"
        token_file.parent.mkdir(parents=True)
        token_file.write_text(token, encoding="utf-8")
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "second_brain", "mcp"],
            env={
                **os.environ,
                "SB_TOKEN": "",
                "SB_TOKEN_FILE": str(token_file),
                "SB_PORT": str(port),
                "SB_AUTOSTART": "1",
                "SB_DATA_DIR": str(root),
                "SB_MCP_PROFILE": "core",
                "PYTHONIOENCODING": "utf-8",
            },
        )
        queries = {"query": "veritabanı", "scope": "beta", "budget": 5000}
        async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            assert {t.name for t in (await session.list_tools()).tools} == set(CORE_TOOLS)
            root_map = payload(await session.call_tool("brain.navigate", {"request": {"branch": "root"}}))
            assert root_map
            for year, database in ((2025, "SQLite"), (2026, "PostgreSQL")):
                value = f"Beta projesinde veritabanı olarak {database} kullanıyorum."
                request = {
                    "source": "synthetic-beta",
                    "source_id": f"database-{year}",
                    "actor": "user",
                    "source_text": value,
                    "scope": "beta",
                    "occurred_at": f"{year}-01-01",
                    "facts": [
                        {
                            "assertion": "direct_user",
                            "memory_type": "DECISION",
                            "subject": "Beta",
                            "predicate": "database",
                            "value": value,
                            "topics": ["veritabanı"],
                        }
                    ],
                }
                saved = payload(await session.call_tool("brain.remember", {"request": request}))
                assert not saved["approval_required"] and saved["applied"][0]["current"]
            memory_id = saved["applied"][0]["id"]
            explanation = "Bu kaydı veritabanı başlığı altında düzenliyorum."
            organized = payload(
                await session.call_tool(
                    "brain.remember",
                    {
                        "request": {
                            "actor": "assistant",
                            "source_text": explanation,
                            "scope": "beta",
                            "facts": [],
                            "change": {
                                "operation": "organize",
                                "id": memory_id,
                                "instruction": explanation,
                                "topics": ["altyapı/veritabanı"],
                            },
                        }
                    },
                )
            )
            assert organized["change"]["status"] == "active"
            structure = payload(await session.call_tool("brain.read", {"request": {"id": memory_id}}))
            assert structure["topics"] == ["altyapı/veritabanı"] and "PostgreSQL" in structure["text"]
            inference = "Bu proje için düzenli yedek kontrolü yararlı olabilir."
            proposed = payload(
                await session.call_tool(
                    "brain.remember",
                    {
                        "request": {
                            "actor": "assistant",
                            "source_text": inference,
                            "scope": "beta",
                            "facts": [
                                {
                                    "memory_type": "MODEL_INFERENCE",
                                    "subject": "Beta",
                                    "predicate": "backup.note",
                                    "value": inference,
                                }
                            ],
                        }
                    },
                )
            )
            pending_id = proposed["candidates"][0]["id"]
            pending = payload(
                await session.call_tool("brain.navigate", {"request": {"branch": "review", "scope": "beta"}})
            )
            assert pending_id in {row["id"] for row in pending["cards"]}
            pending_detail = payload(
                await session.call_tool(
                    "brain.read", {"request": {"id": pending_id, "include_pending": True}}
                )
            )
            assert not pending_detail["approved"]
            reviewed = payload(
                await session.call_tool(
                    "brain.remember",
                    {
                        "request": {
                            "actor": "user",
                            "source_text": "Bu kaydı onayla.",
                            "scope": "beta",
                            "facts": [],
                            "change": {
                                "operation": "approve",
                                "id": pending_id,
                                "instruction": "Bu kaydı onayla.",
                            },
                        }
                    },
                )
            )
            assert reviewed["change"]["status"] == "active"
            accepted = payload(await session.call_tool("brain.read", {"request": {"id": pending_id}}))
            assert accepted["trust"] == "inferred" and accepted["acceptance"] == "conversation_review"
            observation = api.get("/api/observer").json()
            assert observation["read_only"] and all(
                item["action"] != "api.access" for item in observation["activity"]["items"]
            )
            saved_count = api.get("/api/status").json()["counts"]["memories"]
            payload(await session.call_tool("brain.remember", {"request": request}))
            detail = payload(await session.call_tool("brain.read", {"request": {"id": memory_id}}))
            assert "PostgreSQL" in json.dumps(detail, ensure_ascii=False)
            context = payload(await session.call_tool("brain.prepare_context", queries))
            assert "PostgreSQL" in json.dumps(context, ensure_ascii=False)
            repeat = payload(
                await session.call_tool("brain.prepare_context", {**queries, "known_state": context["state"]})
            )
            assert repeat["unchanged"]
            history = payload(
                await session.call_tool("brain.prepare_context", {**queries, "valid_at": "2025-06-01"})
            )
            assert "SQLite" in json.dumps(history, ensure_ascii=False)
            assert (await session.call_tool("brain.prepare_context", {"scope": "private"})).is_error
            with httpx.Client(
                base_url=started["url"], trust_env=False, headers={"Authorization": "Bearer " + token}
            ) as agent:
                assert agent.get("/api/audit").status_code == 403
                assert agent.post("/api/action/brain.forget", json={"id": memory_id}).status_code == 403
            assert api.get("/api/status").json()["counts"]["memories"] == saved_count
            source_hashes = sorted(
                hashlib.sha256(row["text"].encode()).hexdigest()
                for row in api.get("/api/export/json").json()["events"]
            )
            password = secrets.token_urlsafe(24)
            backup = api.post("/api/backups", json={"password": password})
            assert backup.status_code == 200
            bid = backup.json()["id"]
            assert (
                api.post(f"/api/backups/{bid}/verify", json={"password": password}).json()["integrity"]
                == "ok"
            )
            imported = api.post(
                "/api/import",
                files={"file": ("synthetic-note.txt", b"A durable source document.", "text/plain")},
                data={"scope": "beta"},
            )
            assert imported.status_code == 200
            jid = imported.json()["id"]
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                job = next(
                    row
                    for row in api.post("/api/action/brain.sync_status", json={}).json()["jobs"]
                    if row["id"] == jid
                )
                if job["state"] == "done":
                    break
                assert job["state"] not in {"dead", "cancelled"}, job
                await asyncio.sleep(0.1)
            assert job["state"] == "done"
            restored = api.post(
                f"/api/backups/{bid}/restore", json={"password": password, "confirmation": bid}
            )
            assert restored.status_code == 200
            assert api.get("/api/status").json()["counts"]["memories"] == saved_count
            assert (
                sorted(
                    hashlib.sha256(row["text"].encode()).hexdigest()
                    for row in api.get("/api/export/json").json()["events"]
                )
                == source_hashes
            )
            # The existing stdio connection must recover when its HTTP service disappears.
            stop_synthetic(root, port)
            recovered = payload(
                await session.call_tool("brain.prepare_context", {**queries, "known_state": context["state"]})
            )
            assert not recovered.get("unchanged") and "PostgreSQL" in json.dumps(
                recovered, ensure_ascii=False
            )
            assert api.get("/api/diagnostics").json()["integrity"]["quick_check"] == "ok"
            assert api.post("/api/logout").status_code == 200
            assert api.get("/api/status").status_code == 403
    return {
        "http_login_logout": True,
        "core_mcp_tools": 4,
        "source_grounded_save_and_read": True,
        "direct_statement_correction_and_history": True,
        "exact_retry_deduplicated": True,
        "unchanged_context": True,
        "scope_and_admin_denied": True,
        "queued_file_import": True,
        "encrypted_backup_verify_restore": True,
        "restored_source_hashes_equal": True,
        "mcp_autostart_after_process_exit": True,
        "ai_metadata_organization_without_claim_rewrite": True,
        "conversational_review_preserves_inference_type": True,
        "read_only_observation_dashboard": True,
        "autostart_lifetime": "Host-managed; use Start.cmd for an independent background service.",
        "sqlite_integrity": "ok",
    }


def main():
    project = Path(__file__).resolve().parent.parent
    if os.environ.get("SB_VERIFY_INSTALLED") == "1":
        expected_package = Path(
            os.environ.get("SB_VERIFY_PACKAGE_ROOT", str(project / ".test-tmp/wheel-install"))
        )
        assert Path(second_brain.__file__).resolve().is_relative_to(expected_package)
    directory = project / ".test-tmp"
    directory.mkdir(exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="beta-acceptance-", dir=directory) as temp:
        root = Path(temp).resolve() / "brain with spaces"
        try:
            result = asyncio.run(scenario(root, port))
        finally:
            stop_synthetic(root, port)
    report = {
        "checked_at": now(),
        "version": second_brain.__version__,
        "checks": result,
        "package_location": "source"
        if Path(second_brain.__file__).resolve().is_relative_to(project / "second_brain")
        else "installed-wheel",
        "personal_records_written": 0,
        "external_model_calls": 0,
        "limits": "Synthetic local acceptance on Windows; does not measure general language understanding or year-long recall.",
    }
    target = project / "reports/beta-0.1/acceptance.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Beta release regressions: lifecycle, diagnostics and safe connection failures."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import tomllib

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from second_brain import __version__
from second_brain.api import create_app
from second_brain.connection import activate, codex_entry, config_block
from second_brain.doctor import diagnose
from second_brain.mcp_server import request_action
from second_brain.models import OWNER, Principal
from second_brain.security import create_token
from second_brain.service import ensure_service, instance_id, service_health, service_lock


def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def stop_test_service(pid, port):
    # Only the process just created with a pytest-owned synthetic data directory.
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if service_health(port) is None:
            return
        time.sleep(0.05)
    raise AssertionError("Synthetic test service did not exit")


def test_background_start_reuse_restart_and_wrong_brain_guard(tmp_path, monkeypatch):
    monkeypatch.delenv("SB_TOKEN", raising=False)
    monkeypatch.delenv("SB_TOKEN_FILE", raising=False)
    root = tmp_path / "brain with spaces"
    app = create_app(root, run_worker=False)
    principal = Principal(
        id="beta", role="agent", permissions=["read", "capture", "propose"], scopes=["global"], clearance=1
    )
    token = create_token(app.state.brain.db, OWNER, "beta", principal)["token"]
    managed = root / "connections/codex/client.token"
    managed.parent.mkdir(parents=True)
    managed.write_text(token, encoding="utf-8")
    port = unused_port()
    running = ensure_service(root, port)
    try:
        assert running["started"] and running["health"]["version"] == __version__
        assert running["health"]["instance_id"] == instance_id(root)
        assert not ensure_service(root, port)["started"]
        with pytest.raises(RuntimeError, match="another data directory"):
            ensure_service(tmp_path / "wrong brain", port)
        assert not (tmp_path / "wrong brain").exists()
        owner = (root / "owner.token").read_text("utf-8")
        with httpx.Client(base_url=running["url"], trust_env=False, timeout=10) as client:
            assert client.get("/api/status").status_code == 403
            client.headers["Authorization"] = "Bearer " + owner
            for year in (3, 4):
                value = f"Ben {year}. sınıfım."
                response = client.post(
                    "/api/action/brain.remember",
                    json={
                        "actor": "user",
                        "source_id": f"beta-year-{year}",
                        "source_text": value,
                        "occurred_at": f"202{year + 1}-01-01",
                        "facts": [
                            {
                                "assertion": "direct_user",
                                "memory_type": "USER_ASSERTED_FACT",
                                "subject": "user",
                                "predicate": "education.year",
                                "value": value,
                            }
                        ],
                    },
                )
                assert response.status_code == 200 and response.json()["applied"][0]["current"]
            before = client.post(
                "/api/action/brain.prepare_context", json={"query": "sınıf", "budget": 2400}
            ).json()
            assert "Ben 4. sınıfım." in json.dumps(before, ensure_ascii=False)
            assert diagnose(root, port)["ready"]
            assert token not in json.dumps(diagnose(root, port))
        stop_test_service(running["pid"], port)
        running = ensure_service(root, port)
        with httpx.Client(
            base_url=running["url"], trust_env=False, timeout=10, headers={"Authorization": "Bearer " + token}
        ) as client:
            after = client.post(
                "/api/action/brain.prepare_context",
                json={"query": "sınıf", "budget": 2400, "known_state": before["state"]},
            ).json()
            assert after["state"] != before["state"] and not after.get("unchanged")
            assert "Ben 4. sınıfım." in json.dumps(after, ensure_ascii=False)
        # Another service cannot own this directory even on a different port.
        duplicate = subprocess.run(  # noqa: S603 -- fixed CLI and synthetic pytest directory
            [
                sys.executable,
                "-m",
                "second_brain",
                "--data",
                str(root),
                "serve",
                "--port",
                str(unused_port()),
            ],
            capture_output=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert duplicate.returncode != 0 and b"Another service owns" in duplicate.stderr
        assert (root / "service.lock").stat().st_size == 1
    finally:
        if service_health(port):
            stop_test_service(running["pid"], port)


def test_doctor_offline_does_not_create_database(tmp_path, monkeypatch):
    monkeypatch.delenv("SB_TOKEN", raising=False)
    monkeypatch.delenv("SB_TOKEN_FILE", raising=False)
    root = tmp_path / "absent"
    report = diagnose(root, unused_port())
    assert not report["ready"] and not root.exists()
    assert any(c["name"] == "service" and not c["ok"] for c in report["checks"])


def test_service_lock_releases_after_exception(tmp_path):
    with pytest.raises(ValueError):
        with service_lock(tmp_path):
            raise ValueError("synthetic startup failure")
    with service_lock(tmp_path):
        assert (tmp_path / "service.lock").stat().st_size == 1


def test_interrupted_job_resumes_immediately_with_same_identity_and_checkpoint(brain):
    queued = brain.queue.enqueue("import", "synthetic-crash-retry", {"cursor": 12}, OWNER)
    claimed = brain.queue.claim()
    assert claimed["id"] == queued["id"] and claimed["attempts"] == 1
    assert brain.queue.recover_interrupted() == 1
    assert brain.queue.recover_interrupted() == 0
    resumed = brain.queue.claim()
    assert resumed["id"] == queued["id"] and resumed["attempts"] == 2
    assert resumed["payload"]["cursor"] == 12


@pytest.mark.parametrize(
    "status,body", [(403, {"error": "Authentication required"}), (502, "invalid upstream response")]
)
def test_mcp_errors_are_actionable_without_secret_echo(monkeypatch, status, body):
    import second_brain.mcp_server as module

    monkeypatch.setenv("SB_TOKEN", "synthetic-restricted-key")
    monkeypatch.setenv("SB_AUTOSTART", "0")
    original = httpx.Client
    transport = httpx.MockTransport(
        lambda request: (
            httpx.Response(status, json=body) if isinstance(body, dict) else httpx.Response(status, text=body)
        )
    )
    monkeypatch.setattr(module.httpx, "Client", lambda **kwargs: original(**kwargs, transport=transport))
    with pytest.raises(ToolError) as error:
        request_action("brain.prepare_context", {})
    assert "synthetic-restricted-key" not in str(error.value)
    assert "Privacy" in str(error.value) or "doctor" in str(error.value)


def test_mcp_offline_and_missing_credentials_explain_recovery(monkeypatch, tmp_path):
    monkeypatch.setenv("SB_TOKEN", "synthetic-restricted-key")
    monkeypatch.setenv("SB_PORT", str(unused_port()))
    monkeypatch.setenv("SB_AUTOSTART", "0")
    with pytest.raises(ToolError, match="offline"):
        request_action("brain.prepare_context", {})
    monkeypatch.setenv("SB_TOKEN", "")
    monkeypatch.setenv("SB_TOKEN_FILE", str(tmp_path / "missing.token"))
    with pytest.raises(ToolError, match="token file is unavailable"):
        request_action("brain.prepare_context", {})


def test_managed_pre_beta_connection_upgrade_preserves_other_config(tmp_path):
    workspace = tmp_path / "project"
    token = workspace / "data/connections/codex/client.token"
    token.parent.mkdir(parents=True)
    token.write_text("synthetic-credential", encoding="utf-8")
    old = codex_entry(workspace, token)
    old["env"].pop("SB_AUTOSTART")
    old["env"].pop("SB_DATA_DIR")
    original = 'model = "keep"\n' + config_block(old) + '\n[mcp_servers.other]\ncommand = "keep"\n'
    config = tmp_path / "config.toml"
    config.write_text(original, encoding="utf-8")
    result = activate(workspace, config)
    expected = tomllib.loads(original)
    expected["mcp_servers"]["second-brain"] = codex_entry(workspace, token)
    assert result["upgraded"] and tomllib.loads(config.read_text("utf-8")) == expected
    assert (token.parent / "config.before-beta.toml").read_text("utf-8") == original
    assert activate(workspace, config)["already_configured"]


def test_mcp_autostart_requires_absolute_explicit_directory(monkeypatch):
    monkeypatch.setenv("SB_TOKEN", "synthetic-credential")
    monkeypatch.setenv("SB_AUTOSTART", "1")
    monkeypatch.setenv("SB_DATA_DIR", "relative-data")
    with pytest.raises(ToolError, match="absolute SB_DATA_DIR"):
        request_action("brain.prepare_context", {})

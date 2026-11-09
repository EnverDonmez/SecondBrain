import sys

from fastapi import FastAPI, File, UploadFile
from fastapi.testclient import TestClient

from second_brain.api import create_app
from second_brain.http_limits import RequestSizeLimit
from second_brain.models import OWNER, EventInput, MemoryInput, Principal
from second_brain.security import create_token
from second_brain.vault import DPAPI_PREFIX, Vault


def test_browser_session_is_revoked_and_reads_do_not_grow_audit(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    with TestClient(app) as client:
        owner = (tmp_path / "owner.token").read_text().strip()
        assert client.post("/api/login", json={"token": owner, "remember": True}).status_code == 200
        cookie = client.cookies["brain_session"]
        assert cookie != owner
        for _ in range(3):
            assert client.get("/api/observer").status_code == 200
        db = app.state.brain.db
        assert db.one("SELECT COUNT(*) n FROM audit WHERE action='api.access'")["n"] == 0
        assert client.post("/api/logout", headers={"x-brain-request": "1"}).status_code == 200
        assert client.get("/api/status", headers={"Cookie": "brain_session=" + cookie}).status_code == 403
        assert client.get("/api/status", headers={"Authorization": "Bearer " + cookie}).status_code == 403
        assert client.get("/api/status", headers={"Cookie": "brain_session=" + owner}).status_code == 403
        assert client.get("/api/status", headers={"Authorization": "Bearer " + owner}).status_code == 200


def test_body_limit_checks_header_and_stream_before_parsing():
    app = FastAPI()
    app.add_middleware(RequestSizeLimit, limit=256)

    @app.post("/json")
    def json_body(body: dict):
        return body

    @app.post("/file")
    async def upload(file: UploadFile = File()):
        return {"bytes": len(await file.read())}

    with TestClient(app) as client:
        assert client.post("/json", headers={"Content-Length": "abc"}, content="{}").status_code == 400
        assert client.post("/json", json={"value": "x" * 512}).status_code == 413
        assert (
            client.post(
                "/json",
                headers={"Content-Type": "application/json"},
                content=iter([b'{"value":"', b"x" * 512, b'"}']),
            ).status_code
            == 413
        )
        multipart = b'--test\r\nContent-Disposition: form-data; name="file"; filename="a"\r\n\r\n'
        assert (
            client.post(
                "/file",
                headers={"Content-Type": "multipart/form-data; boundary=test"},
                content=iter([multipart, b"x" * 512, b"\r\n--test--\r\n"]),
            ).status_code
            == 413
        )
        assert client.post("/file", files={"file": ("a", b"x")}).json() == {"bytes": 1}


def test_legacy_vault_key_remains_usable_after_protection(tmp_path):
    key_path = tmp_path / "master.key"
    key_path.write_bytes(bytes(range(32)))
    vault = Vault(tmp_path)
    vault.put(b"synthetic asset", "a")
    if sys.platform == "win32":
        assert key_path.read_bytes().startswith(DPAPI_PREFIX)
    assert Vault(tmp_path).get("a") == b"synthetic asset"


def test_batch_review_preserves_permissions_and_individual_results(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    brain = app.state.brain
    source = brain.events.ingest(EventInput(source="synthetic", source_id="one", text="Evidence."), OWNER)
    candidate = brain.memory.propose(
        MemoryInput(
            memory_type="LESSON", predicate="test", value="Check output.", source_event_ids=[source["id"]]
        ),
        OWNER,
    )
    agent = Principal(id="test-agent", role="agent", permissions=["read", "capture", "propose"])
    client_key = create_token(brain.db, OWNER, "synthetic", agent)["token"]
    action = {"operation": "approve", "ids": [candidate["id"], "a" * 32]}
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + client_key}
        assert client.post("/api/review/batch", json=action, headers=headers).status_code == 403
        client.headers["Authorization"] = "Bearer " + (tmp_path / "owner.token").read_text().strip()
        result = client.post("/api/review/batch", json=action).json()["results"]
        assert result[0] == {"id": candidate["id"], "status": "active"}
        assert "error" in result[1]
        assert client.post("/api/review/batch", json=action).json()["results"] == result

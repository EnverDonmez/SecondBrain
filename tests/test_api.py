import json

import pytest
from fastapi.testclient import TestClient

from second_brain.api import create_app
from second_brain.models import Principal


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "api", run_worker=False)
    with TestClient(app) as c:
        c.headers["Authorization"] = "Bearer " + (tmp_path / "api" / "owner.token").read_text()
        yield c


def test_api_round_trip_and_export(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200
    event = client.post(
        "/api/events",
        json={"source": "dashboard", "source_id": "one", "actor": "user", "text": "Türkçe yanıt"},
    ).json()
    record = client.post(
        "/api/memories",
        json={"predicate": "language", "value": "Türkçe yanıt", "source_event_ids": [event["id"]]},
    ).json()
    assert client.post("/api/search", json={"query": "Türkçe"}).json()["items"] == []
    assert client.post("/api/memories/" + record["id"] + "/approve").status_code == 200
    assert client.post("/api/search", json={"query": "Türkçe"}).json()["items"][0]["value"] == "Türkçe yanıt"
    for kind in ["json", "jsonl", "markdown"]:
        exported = client.get("/api/export/" + kind)
        assert exported.status_code == 200 and "Türkçe" in exported.text
    profile = client.post(
        "/api/action/brain.prepare_context", json={"query": "Beynimi tara", "budget": 2000}
    ).json()
    assert profile["records"] and profile["sources"]


def test_captured_preference_is_reviewable_and_replay_safe(client):
    payload = {"source": "synthetic", "source_id": "preference", "text": "Bana Türkçe ve kısa cevap ver."}
    response = client.post("/api/events", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["candidates"]) == 2 and body["approval_required"]
    replay = client.post("/api/events", json=payload).json()
    assert {c["id"] for c in replay["candidates"]} == {c["id"] for c in body["candidates"]}
    assert not client.post("/api/search", json={"query": "Türkçe"}).json()["items"]
    for candidate in body["candidates"]:
        assert client.post("/api/memories/" + candidate["id"] + "/approve").status_code == 200
    assert client.post("/api/search", json={"query": "Türkçe"}).json()["items"]


def test_auth_csrf_and_host(client):
    client.headers.pop("Authorization")
    assert client.get("/api/status").status_code == 403
    assert client.post("/api/events", json={}, headers={"Origin": "https://evil.test"}).status_code == 403
    assert client.get("/healthz", headers={"Host": "evil.test"}).status_code == 400
    key = (client.app.state.brain.db.root / "owner.token").read_text()
    assert client.post("/api/login", json={"token": key}).status_code == 200
    assert client.get("/api/status").status_code == 200
    assert client.post("/api/logout").status_code == 403
    assert client.post("/api/logout", headers={"X-Brain-Request": "1"}).status_code == 200


@pytest.mark.parametrize("remember", [False, True])
def test_owner_remember_me_cookie_lifetime_and_logout(client, remember):
    key = (client.app.state.brain.db.root / "owner.token").read_text()
    client.headers.pop("Authorization")
    response = client.post("/api/login", json={"token": key, "remember": remember})
    assert response.status_code == 200 and response.json()["remembered"] is remember
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    if remember:
        assert "Max-Age=2592000" in cookie
    else:
        assert "Max-Age" not in cookie and "expires=" not in cookie.lower()
    assert client.get("/api/observer").status_code == 200
    logout = client.post("/api/logout", headers={"X-Brain-Request": "1"})
    assert logout.status_code == 200 and "Max-Age=0" in logout.headers["set-cookie"]
    assert client.get("/api/observer").status_code == 403


def test_remember_me_requires_actual_boolean(client):
    key = (client.app.state.brain.db.root / "owner.token").read_text()
    client.headers.pop("Authorization")
    response = client.post("/api/login", json={"token": key, "remember": "false"})
    assert response.status_code == 422 and "brain_session" not in response.cookies


def test_scoped_agent_no_approval_admin_or_delete(client):
    principal = Principal(
        id="codex", role="agent", scopes=["global"], permissions=["read", "propose", "capture"], clearance=1
    )
    created = client.post("/api/tokens", json={"name": "codex", "principal": principal.model_dump()}).json()
    owner = client.headers["Authorization"]
    client.headers["Authorization"] = "Bearer " + created["token"]
    assert client.get("/api/status").status_code == 200
    assert client.get("/api/audit").status_code == 403
    assert client.post("/api/action/brain.forget", json={"id": "anything"}).status_code == 403
    assert client.post("/api/action/brain.commit_memory", json={"id": "anything"}).status_code == 403
    assert client.post("/api/search", json={"query": "", "include_candidates": True}).status_code == 403
    client.headers["Authorization"] = owner
    assert client.delete("/api/tokens/" + created["id"]).status_code == 200
    client.headers["Authorization"] = "Bearer " + created["token"]
    assert client.get("/api/status").status_code == 403


def test_file_job_and_source(client):
    result = client.post(
        "/api/import",
        files={"file": ("notes.md", "# Kaynak\nBelgelenmiş bir bilgi".encode(), "text/markdown")},
    ).json()
    assert result["state"] == "pending"
    brain = client.app.state.brain
    assert brain.process_one()
    job = client.post("/api/action/brain.sync_status", json={}).json()["jobs"][0]
    assert job["state"] == "done"
    assert json.loads(job["result"])["events"] == 1
    candidate = client.post("/api/search", json={"query": "", "include_candidates": True}).json()["items"][0]
    assert candidate["memory_type"] == "EXTERNAL_KNOWLEDGE"
    assert client.post("/api/memories/" + candidate["id"] + "/approve").status_code == 200


def test_api_validation(client):
    assert client.post("/api/search", json={"query": "a", "limit": 999999}).status_code == 422
    assert (
        client.post("/api/events", json={"source": "x", "source_id": "x", "sensitivity": -1}).status_code
        == 422
    )
    assert client.post("/api/search", json={"valid_at": "not-a-date"}).status_code == 422
    assert client.post("/api/action/unknown", json={}).status_code == 422


def test_no_identifier_fragment_false_positive(client):
    brain = client.app.state.brain
    from second_brain.models import OWNER, EventInput, MemoryInput, SearchInput

    event = brain.events.ingest(EventInput(source="test", source_id="one", text="Ankara"), OWNER)
    memory = brain.memory.propose(
        MemoryInput(
            subject="facts-003", predicate="home_city", value="Ankara", source_event_ids=[event["id"]]
        ),
        OWNER,
    )
    brain.memory.commit(memory["id"], OWNER)
    for engine in ["fts", "bm25", "hybrid"]:
        assert not brain.retrieval.search(SearchInput(query="unknown-003", engine=engine), OWNER)["items"]


def test_revoking_token_cancels_queued_import(client):
    principal = Principal(
        id="capture-test", role="agent", scopes=["global"], permissions=["read", "capture"], clearance=1
    )
    created = client.post(
        "/api/tokens", json={"name": "revocation-test", "principal": principal.model_dump()}
    ).json()
    owner = client.headers["Authorization"]
    client.headers["Authorization"] = "Bearer " + created["token"]
    job = client.post(
        "/api/import", files={"file": ("queued.md", b"Queued content must not be processed")}
    ).json()
    client.headers["Authorization"] = owner
    assert client.delete("/api/tokens/" + created["id"]).status_code == 200
    brain = client.app.state.brain
    assert brain.db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "cancelled"
    assert not brain.process_one()
    assert not brain.db.one("SELECT 1 FROM events")


def test_empty_meaning_query_abstains(client):
    test_api_round_trip_and_export(client)
    for query in ["ne", "hangi", "???"]:
        result = client.post("/api/search", json={"query": query}).json()
        assert result["abstain"] and not result["items"] and result["warnings"]

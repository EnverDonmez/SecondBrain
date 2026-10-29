import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from second_brain.api import create_app
from second_brain.db import Database, dumps
from second_brain.models import OWNER, EventInput, MemoryInput, Principal, SearchInput
from second_brain.security import Denied, create_token


def agent(**updates):
    return Principal(
        id="conversation-ai",
        role="agent",
        permissions=["read", "capture", "propose"],
        scopes=["global", "secondbrain"],
        clearance=1,
    ).model_copy(update=updates)


def packet(**updates):
    return {
        "source_id": "conversation-one:message-one",
        "source_text": "Projede SQLite kullanacağım. Yedekler her gün alınacak.",
        "actor": "user",
        "scope": "secondbrain",
        "facts": [
            {
                "subject": "SecondBrain",
                "predicate": "database",
                "value": "SQLite",
                "memory_type": "DECISION",
                "topics": ["altyapı"],
            },
            {
                "subject": "SecondBrain",
                "predicate": "backup",
                "value": "Her gün yedek alınacak.",
                "memory_type": "DECISION",
                "topics": ["altyapı"],
            },
        ],
        **updates,
    }


def test_remember_batch_retry_review_and_no_model(brain, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Economy mode must not call a model")

    monkeypatch.setattr(brain.provider, "extract", forbidden)
    monkeypatch.setattr("second_brain.providers.LocalEmbedder.embed", forbidden)
    brain.learning.feedback("Dağıtım öncesi bağlantı testini çalıştır", "global", "correction", OWNER)
    brain.learning.feedback("Dağıtım öncesi bağlantı testini uygula", "global", "correction", OWNER)
    first = brain.dispatch("brain.remember", packet(), agent())
    second = brain.dispatch("brain.remember", packet(), agent())
    assert first["candidates"] == second["candidates"]
    assert first["source_event_id"] == second["source_event_id"]
    assert second["source_duplicate"] and first["approval_required"]
    assert first["additional_model_calls"] == 0
    assert brain.db.one("SELECT COUNT(*) n FROM events WHERE source='ai-conversation'")["n"] == 1
    assert brain.db.one("SELECT COUNT(*) n FROM memories")["n"] == 2
    assert not brain.retrieval.search(SearchInput(query="SQLite"), agent())["items"]
    with pytest.raises(Denied):
        brain.dispatch("brain.commit_memory", {"id": first["candidates"][0]["id"]}, agent())
    for record in first["candidates"]:
        brain.memory.commit(record["id"], OWNER)
    assert not brain.db.one("SELECT 1 FROM jobs WHERE kind='vector_memory'")
    result = brain.retrieval.search(SearchInput(query="SQLite", scope="secondbrain"), agent())
    assert {row["id"] for row in result["items"]} == {r["id"] for r in first["candidates"]}
    assert any(row["retrieval_path"] == "graph" for row in result["items"])
    context = brain.dispatch("brain.prepare_context", {"query": "SQLite", "scope": "secondbrain"}, agent())
    assert len(dumps(context).encode()) <= 3000
    assert any("yedek" in row["value"] for row in context["records"])
    assert brain.provider.db.one("SELECT COUNT(*) n FROM usage")["n"] == 0


def test_invalid_batch_does_not_leave_sources_or_candidates(brain):
    invalid = packet()
    invalid["facts"][1]["topics"] = ["x" * 121]
    with pytest.raises(ValueError):
        brain.dispatch("brain.remember", invalid, agent())
    with pytest.raises(Denied):
        brain.dispatch("brain.remember", packet(scope="private"), agent())
    with pytest.raises(Denied):
        brain.dispatch("brain.remember", packet(), agent(permissions=["read", "propose"]))
    invalid = packet(actor="assistant")
    invalid["facts"][0]["memory_type"] = "USER_PREFERENCE"
    with pytest.raises(Denied):
        brain.dispatch("brain.remember", invalid, agent())
    assert not brain.db.one("SELECT 1 FROM events")
    assert not brain.db.one("SELECT 1 FROM memories")


def test_remember_without_host_id_uses_honest_content_hash(brain):
    request = packet(source_id=None)
    first = brain.dispatch("brain.remember", request, agent())
    second = brain.dispatch("brain.remember", request, agent())
    assert first["candidates"] == second["candidates"]
    source = brain.events.get(first["source_event_id"], agent())
    assert source["source_id"].startswith("excerpt-sha256:")
    assert source["metadata"]["source_identity_kind"] == "excerpt_hash"


def linked(
    brain,
    value,
    *,
    subject="project",
    scope="global",
    sensitivity=1,
    related=None,
    topics=None,
    valid_from="2026-01-01",
    valid_to=None,
    supersedes=None,
):
    source = brain.events.ingest(
        EventInput(
            source="synthetic",
            source_id=value + valid_from,
            text=value,
            scope=scope,
            sensitivity=sensitivity,
            occurred_at=valid_from,
        ),
        OWNER,
    )
    candidate = brain.memory.propose(
        MemoryInput(
            subject=subject,
            predicate="fact:" + value,
            value=value,
            scope=scope,
            sensitivity=sensitivity,
            topics=topics or [],
            related_memory_ids=related or [],
            source_event_ids=[source["id"]],
            valid_from=valid_from,
            valid_to=valid_to,
            supersedes=supersedes,
        ),
        OWNER,
    )
    return brain.memory.commit(candidate["id"], OWNER)


def test_graph_hops_do_not_bridge_forbidden_or_inactive_memory(brain):
    seed = linked(brain, "quartz", subject="origin", topics=["start"])
    bridge = linked(brain, "neon", subject="bridge", topics=["start", "next"])
    end = linked(brain, "violet", subject="end", topics=["next"])
    linked(brain, "secret", scope="private", topics=["start"])
    linked(brain, "classified", sensitivity=2, topics=["start"])
    linked(brain, "expired", subject="past", topics=["start"], valid_to="2026-02-01")
    one = brain.retrieval.search(SearchInput(query="quartz", graph_hops=1), agent())
    two = brain.retrieval.search(SearchInput(query="quartz", graph_hops=2), agent())
    assert {row["id"] for row in one["items"]} == {seed["id"], bridge["id"]}
    assert {row["id"] for row in two["items"]} == {seed["id"], bridge["id"], end["id"]}
    foreign = agent(tenant="another")
    assert not brain.retrieval.search(SearchInput(query="quartz", graph_hops=2), foreign)["items"]
    brain.memory.hide(bridge["id"], OWNER)
    assert {
        row["id"]
        for row in brain.retrieval.search(SearchInput(query="quartz", graph_hops=2), agent())["items"]
    } == {seed["id"]}


def test_explicit_link_sensitivity_erasure_and_reindex(brain):
    seed = linked(brain, "quartz", subject="origin")
    target = linked(brain, "violet", subject="end", related=[seed["id"]])
    assert {row["id"] for row in brain.retrieval.search(SearchInput(query="quartz"), agent())["items"]} == {
        seed["id"],
        target["id"],
    }
    for hidden in [linked(brain, "private", scope="private"), linked(brain, "sensitive", sensitivity=2)]:
        bad = packet()
        bad["facts"][0]["related_memory_ids"] = [hidden["id"]]
        with pytest.raises(Denied):
            brain.dispatch("brain.remember", bad, agent())
    brain.privacy.forget(seed["id"], OWNER)
    assert brain.memory.get(target["id"], OWNER)["related_memory_ids"] == []
    brain.memory.rebuild(OWNER)
    assert not brain.db.one("SELECT 1 FROM memory_links")
    assert not brain.db.one("SELECT 1 FROM memory_nodes WHERE memory_id=?", (seed["id"],))


def test_indexed_search_bounds_content_fetch_and_avoids_generic_user_hub(brain, monkeypatch):
    # Bulk SQL setup keeps this a retrieval regression rather than a write benchmark.
    for i in range(120):
        linked(brain, "quartz " + str(i), subject="user", topics=["hub"])
    linked(brain, "unrelated", subject="user")
    statements = []
    original = brain.db.rows

    def track(sql, params=()):
        statements.append(sql)
        return original(sql, params)

    monkeypatch.setattr(brain.db, "rows", track)
    result = brain.retrieval.search(SearchInput(query="quartz", limit=100), agent())
    assert 0 < result["candidates_examined"] <= result["candidate_limit"] == 96
    assert all("unrelated" != row["value"] for row in result["items"])
    assert all("SELECT m.* FROM memories m WHERE" not in sql or "LIMIT" in sql for sql in statements)
    assert not brain.db.one("SELECT 1 FROM memory_nodes WHERE node='entity:user'")


def test_version_four_migration_rebuilds_graph_and_vocabulary(tmp_path, brain, make_memory):
    import sqlite3
    from second_brain.memory import MemoryRegistry

    existing = make_memory("Kısa yanıt", subject="Synthetic project")
    legacy = brain.db.one("SELECT * FROM memories WHERE id=?", (existing["id"],))
    legacy.pop("topics")
    legacy.pop("related_memory_ids")
    legacy.pop("subject_key")
    legacy.pop("predicate_key")
    root = tmp_path / "legacy"
    root.mkdir()
    with sqlite3.connect(root / "brain.sqlite3") as con:
        for migration in sorted(Path("second_brain/migrations").glob("*.sql"))[:4]:
            con.executescript(migration.read_text("utf-8"))
        MemoryRegistry._insert(con, legacy)
        con.execute("PRAGMA user_version=4")
        con.commit()
    db = Database(root)
    assert db.one("PRAGMA user_version")["user_version"] == 7
    assert db.one("SELECT 1 FROM memory_nodes WHERE memory_id=?", (existing["id"],))
    assert db.one("SELECT 1 FROM memory_fts WHERE memory_fts MATCH 'sbconceptanswer'")
    db.migrate()
    assert db.one("SELECT COUNT(*) n FROM migrations")["n"] == 3


def test_portable_instructions_and_manual_json_http(tmp_path):
    app = create_app(tmp_path / "api", run_worker=False)
    token = create_token(app.state.brain.db, OWNER, "test", agent())["token"]
    with TestClient(app) as client:
        assert client.get("/api/assistant-contract").status_code == 403
        client.headers["Authorization"] = "Bearer " + token
        contract = client.get("/api/assistant-contract").json()
        assert "brain.remember" in contract["instructions"]
        assert contract["default_engine"] == "economy"
        response = client.post("/api/action/brain.remember", json=packet())
        assert response.status_code == 200 and response.json()["approval_required"]
        assert len(response.json()["candidates"]) == 2
        assert "source_text" in json.dumps(contract["schema"])


def test_existing_codex_allowlist_upgrade_preserves_all_other_settings(tmp_path):
    import tomllib
    from second_brain.connection import activate, codex_entry, config_block

    workspace = tmp_path / "project"
    token = workspace / "data/connections/codex/client.token"
    token.parent.mkdir(parents=True)
    token.write_text("synthetic-restricted", encoding="utf-8")
    old = codex_entry(workspace, token)
    old["enabled_tools"].remove("brain.remember")
    original = 'model = "existing"\n' + config_block(old) + '\n[mcp_servers.other]\ncommand = "other"\n'
    config = tmp_path / "config.toml"
    config.write_text(original, encoding="utf-8")
    result = activate(workspace, config)
    assert result["upgraded"] and result["added_tools"] == ["brain.remember"]
    expected = tomllib.loads(original)
    expected["mcp_servers"]["second-brain"] = codex_entry(workspace, token)
    assert tomllib.loads(config.read_text("utf-8")) == expected
    assert (token.parent / "config.before-economy.toml").read_text("utf-8") == original
    assert token.read_text("utf-8") == "synthetic-restricted"
    assert activate(workspace, config)["already_configured"]

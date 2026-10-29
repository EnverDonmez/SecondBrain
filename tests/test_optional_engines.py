from pathlib import Path

import pytest

from second_brain.models import OWNER, Principal, SearchInput
from second_brain.providers import index_vectors


@pytest.mark.skipif(
    not Path("data/models/ready.json").exists(), reason="Local embedding model has not been installed"
)
def test_real_cpu_embeddings_and_mem0_projection(brain, make_memory, monkeypatch):
    import socket

    connections = []

    def no_network(self, address):
        connections.append(str(address))
        raise AssertionError("Local engine runtime attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setenv("SB_MODEL_DIR", str(Path("data/models").resolve()))
    first = make_memory("Yanıtları kısa ve Türkçe tercih ederim", predicate="reply_style")
    make_memory("Gizli proje bütçesi elli birim", predicate="budget", scope="private-project")
    indexed = index_vectors(brain.db, OWNER)
    assert indexed["indexed"] == 2
    vector = brain.retrieval.search(
        SearchInput(query="Kullanıcı hangi dilde ve uzunlukta cevap ister?", engine="vector"), OWNER
    )
    assert vector["items"] and vector["items"][0]["id"] == first["id"]
    from second_brain.mem0_adapter import Mem0Adapter

    adapter = Mem0Adapter(brain)
    try:
        assert adapter.health()["telemetry"] is False
        reader = Principal(id="reader", role="reader", scopes=["global"], permissions=["read"], clearance=1)
        result = adapter.retrieve(SearchInput(query="Türkçe kısa cevap"), reader)
        assert result["items"] and result["items"][0]["id"] == first["id"]
        assert all(row["scope"] == "global" for row in result["items"])
        assert adapter.delete(first["id"])["acknowledged"]
    finally:
        adapter.close()
    assert connections == []


@pytest.mark.skipif(not Path("data/models/ready.json").exists(), reason="Local embedding model missing")
def test_long_tail_automatic_index_history_and_erasure(brain, make_memory, monkeypatch):
    monkeypatch.setenv("SB_MEMORY_MODE", "semantic")
    monkeypatch.setenv("SB_MODEL_DIR", str(Path("data/models").resolve()))
    value = (
        "Ağaçlar toprakta büyür ve düzenli sulama gerektirir. " * 45
    ) + "Denizaltı keşif aracının acil durum parolası mavi mercandır."
    record = make_memory(value, predicate="long_source", memory_type="EXTERNAL_KNOWLEDGE", actor="document")
    assert brain.db.one("SELECT kind FROM jobs WHERE state='pending'")["kind"] == "vector_memory"
    brain.process_one()
    chunks = brain.db.rows("SELECT * FROM vector_chunks WHERE memory_id=?", (record["id"],))
    assert len(chunks) > 3 and max(chunk["end_char"] for chunk in chunks) == len(value)
    query = "Denizaltı keşif aracının acil durum parolası nedir?"
    result = brain.retrieval.search(SearchInput(query=query, engine="vector"), OWNER)
    assert result["items"][0]["id"] == record["id"]
    assert "mavi mercandır" in result["items"][0]["match"]["text"]
    packet = brain.retrieval.prepare_context(query, OWNER, budget=3000)
    assert packet["records"] and "mavi mercandır" in packet["records"][0]["value"]
    assert packet["records"][0]["value_is_excerpt"]
    adapter = brain.mem0()
    result = adapter.retrieve(SearchInput(query=query), OWNER)
    assert result["items"] and result["items"][0]["id"] == record["id"]
    assert "mavi mercandır" in result["items"][0]["match"]["text"]
    brain.privacy.forget(record["id"], OWNER)
    assert not brain.db.one("SELECT 1 FROM vector_chunks")
    assert not brain.retrieval.search(SearchInput(query=query, engine="hybrid"), OWNER)["items"]
    assert not adapter.retrieve(SearchInput(query=query), OWNER)["items"]
    brain.reset_projections()


@pytest.mark.skipif(not Path("data/models/ready.json").exists(), reason="Local embedding model missing")
def test_semantic_reindex_includes_closed_known_time_versions(brain, make_memory, monkeypatch):
    old = make_memory("SQLite veritabanı kullanılacak", predicate="database", memory_type="DECISION")
    make_memory(
        "PostgreSQL veritabanı kullanılacak",
        predicate="database",
        memory_type="DECISION",
        supersedes=old["id"],
        valid_from="2026-03-01",
    )
    monkeypatch.setenv("SB_MODEL_DIR", str(Path("data/models").resolve()))
    index_vectors(brain.db, OWNER)
    assert brain.db.one("SELECT 1 FROM vector_chunks WHERE memory_id=?", (old["id"],))
    result = brain.retrieval.search(
        SearchInput(
            query="Hangi veritabanı kullanılacak?",
            engine="vector",
            valid_at="2026-02-01",
            known_at=old["known_from"],
        ),
        OWNER,
    )
    assert result["items"] and result["items"][0]["id"] == old["id"]
    current = brain.retrieval.search(
        SearchInput(query="Hangi veritabanı kullanılacak?", engine="vector", valid_at="2026-06-01"), OWNER
    )
    assert current["items"] and all(row["value"].startswith("PostgreSQL") for row in current["items"])

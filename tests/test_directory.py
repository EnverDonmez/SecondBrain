import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from second_brain.db import dumps
from second_brain.models import OWNER, EventInput, MemoryInput, Principal
from second_brain.security import Denied, NotFound


def agent(**updates):
    return Principal(
        role="agent", permissions=["read", "capture", "propose"], scopes=["global", "atlas"], clearance=1
    ).model_copy(update=updates)


def save(
    brain,
    value,
    *,
    topic="Work/Atlas/Storage",
    scope="atlas",
    kind="DECISION",
    predicate="database",
    valid_from="2024-01-01",
    supersedes=None,
    sensitivity=1,
):
    source = brain.events.ingest(
        EventInput(
            source="synthetic-directory",
            source_id=hashlib.sha256((value + valid_from).encode()).hexdigest(),
            text=value,
            scope=scope,
            occurred_at=valid_from,
            sensitivity=sensitivity,
        ),
        OWNER,
    )
    row = brain.memory.propose(
        MemoryInput(
            subject="Atlas",
            predicate=predicate,
            value=value,
            topics=[topic],
            scope=scope,
            memory_type=kind,
            source_event_ids=[source["id"]],
            valid_from=valid_from,
            supersedes=supersedes,
            sensitivity=sensitivity,
        ),
        OWNER,
    )
    return brain.memory.commit(row["id"], OWNER)


def nav(brain, **request):
    return brain.dispatch("brain.navigate", request, agent())


def read(brain, identity, **request):
    return brain.dispatch("brain.read", {"id": identity, **request}, agent())


def test_directory_general_to_specific_and_no_payload_in_root(brain):
    row = save(brain, "SQLite kullanılacak. " + "Kaynak ayrıntısı " * 150)
    save(brain, "Private project", scope="private", topic="Secret/Project")
    root = nav(brain, budget=1200)
    assert {"projects", "topics", "knowledge", "conversations"} <= {
        item["branch"] for item in root["branches"]
    }
    assert "SQLite" not in dumps(root) and "Private" not in dumps(root)
    assert nav(brain, branch="projects")["branches"] == [{"branch": "projects", "key": "atlas", "count": 1}]
    assert nav(brain, branch="topics")["branches"][0]["key"] == "work"
    assert any(item["key"] == "work/atlas" for item in nav(brain, branch="topics", key="work")["branches"])
    leaf = nav(brain, branch="topics", key="work/atlas/storage")
    assert leaf["cards"][0]["id"] == row["id"]
    assert len(leaf["cards"][0]["preview"]) == 160
    opened = read(brain, row["id"], characters=200)
    assert opened["text"] == row["value"][:200] and opened["more"]
    assert len(dumps(root).encode()) <= 1200


def test_topic_parent_records_and_paginated_children_are_not_lost(brain):
    parent = save(brain, "Top-level decision", topic="Work", predicate="parent")
    expected = {"work/child" + str(i) for i in range(12)}
    for i in range(12):
        save(brain, "Child " + str(i), topic="Work/Child" + str(i), predicate="child" + str(i))
    seen, offset = [], 0
    while True:
        packet = nav(brain, branch="topics", key="work", limit=3, budget=1000, offset=offset)
        seen += packet["branches"]
        if not packet["more"]:
            break
        assert packet["next_offset"] > offset
        offset = packet["next_offset"]
    assert {row["key"] for row in seen if not row.get("records")} == expected
    assert len(seen) == 13
    rows = nav(brain, branch="topics", key="work", records=True, limit=20, budget=16000)["cards"]
    assert parent["id"] in {row["id"] for row in rows}


def test_year_old_source_recalled_after_many_new_turns_without_a_model(brain, monkeypatch):
    monkeypatch.setattr(
        "second_brain.providers.LocalEmbedder.embed", lambda *args: pytest.fail("Unexpected model")
    )
    original = "Bahçe " * 250 + "Orion projesinin teslim tarihi 17 Kasım 2024 olarak belirlenmişti."
    source = brain.events.ingest(
        EventInput(
            source="conversation",
            source_id="old-message",
            text=original,
            scope="atlas",
            conversation_id="2024-thread",
            occurred_at="2024-11-01",
        ),
        OWNER,
    )
    for i in range(45):
        brain.events.ingest(
            EventInput(
                source="conversation",
                source_id=str(i),
                text="Yeni günlük kayıt " + str(i),
                scope="atlas",
                occurred_at="2026-01-01",
            ),
            OWNER,
        )
    result = nav(brain, branch="conversations", query="Orion", since="2024-01-01", until="2024-12-31")
    assert result["cards"][0]["id"] == source["id"]
    excerpt = read(brain, source["id"], kind="event", query="Orion", characters=400)
    assert "17 Kasım 2024" in excerpt["text"]
    assert original[excerpt["start_char"] : excerpt["end_char"]] == excerpt["text"]
    context = brain.dispatch(
        "brain.prepare_context", {"query": "Orion", "scope": "atlas", "budget": 2400}, agent()
    )
    assert context["episodes"][0]["id"] == source["id"]
    assert "17 Kasım 2024" in context["episodes"][0]["text"]
    assert context["records"] == [] and len(dumps(context).encode()) <= 2400
    assert not nav(brain, branch="conversations", query="Orion", known_at="2025-01-01")["cards"]


def test_checkpoint_without_fact_is_persistent_evidence_not_user_rule(brain):
    payload = {
        "source_text": "Atlas aktarımı için tablo eşlemelerini tamamladık.",
        "actor": "assistant",
        "conversation_id": "thread-1",
        "scope": "atlas",
        "checkpoint": "Amaç: Atlas aktarımı. Sonraki adım: migration testi.",
        "topics": ["Work/Atlas/Migration"],
    }
    first = brain.dispatch("brain.remember", payload, agent())
    assert first["source_searchable"] and first["candidates"] == []
    assert brain.dispatch("brain.remember", payload, agent())["source_duplicate"]
    card = nav(brain, branch="conversations", key="thread-1", query="migration")["cards"][0]
    assert card["checkpoint"].startswith("Amaç:") and card["approval"] == "source_only"
    assert not brain.db.one("SELECT 1 FROM memories")
    assert read(brain, card["id"], kind="event")["trust"] == "source_only"


def test_corrections_current_historical_and_explicit_versions(brain):
    old = save(brain, "SQLite", valid_from="2024-01-01")
    new = save(brain, "PostgreSQL", valid_from="2026-01-01", supersedes=old["id"])
    assert read(brain, new["id"])["text"] == "PostgreSQL"
    with pytest.raises(NotFound):
        read(brain, old["id"])
    assert read(brain, old["id"], include_history=True)["text"] == "SQLite"
    current = nav(brain, branch="knowledge", query="SQLite")
    assert current["cards"] == []
    historical = nav(brain, branch="knowledge", query="SQLite", valid_at="2025-01-01")
    assert historical["cards"] and historical["cards"][0]["preview"] == "SQLite"
    versions = nav(brain, branch="knowledge", query="SQLite", include_history=True)
    assert old["id"] in {row["id"] for row in versions["cards"]}
    original_source = read(brain, old["source_event_ids"][0], kind="event")
    assert any(item["id"] == new["id"] for item in original_source["current_memory_refs"])


def test_exact_unicode_paging_respects_total_payload_budget(brain):
    value = "İstanbul 🧠 ve Türkçe kayıt. " * 120
    row = save(brain, value)
    chunks, offset = [], 0
    while True:
        part = read(brain, row["id"], offset=offset, characters=700, budget=1300)
        assert len(dumps(part).encode()) <= 1300
        assert value[part["start_char"] : part["end_char"]] == part["text"]
        chunks.append(part["text"])
        if not part["more"]:
            break
        assert part["next_offset"] > offset
        offset = part["next_offset"]
    assert "".join(chunks) == value


def test_cache_invalidates_on_changes_and_never_crosses_scope(brain):
    save(brain, "SQLite")
    first = nav(brain)
    assert not first["cache_hit"] and nav(brain)["cache_hit"]
    save(brain, "Updated note", predicate="note")
    assert not nav(brain)["cache_hit"]
    limited = agent(scopes=["global"])
    assert brain.dispatch("brain.navigate", {}, limited)["branches"] == []
    assert brain.dispatch("brain.navigate", {}, agent(tenant="other"))["branches"] == []
    with pytest.raises(Denied):
        nav(brain, branch="projects", key="private")
    for budget in [512, 800, 1800]:
        assert len(dumps(nav(brain, budget=budget)).encode()) <= budget


def test_future_transition_expires_cached_map(brain, monkeypatch):
    import second_brain.directory as directory
    import second_brain.retrieval as retrieval

    instant = datetime.now(UTC)
    clock = [0.0]
    monkeypatch.setattr(directory.time, "monotonic", lambda: clock[0])

    def frozen():
        return (instant + timedelta(seconds=clock[0])).isoformat(timespec="microseconds")

    monkeypatch.setattr(directory, "now", frozen)
    monkeypatch.setattr(retrieval, "now", frozen)
    save(brain, "Future project", valid_from=(instant + timedelta(seconds=2)).isoformat())
    assert nav(brain)["branches"] == []
    assert nav(brain)["cache_hit"]
    clock[0] = 3.0
    refreshed = nav(brain)
    assert refreshed["branches"] and not refreshed["cache_hit"]


def test_skill_tool_routing_reads_metadata_and_disabled_entries_invalidate(brain):
    from second_brain.skills import recall_skill_package

    skill = brain.skills.register(recall_skill_package(), OWNER)
    brain.skills.state(skill["id"], True, OWNER)
    tool = brain.tools.register(
        "python",
        "binary",
        {
            "binary": "python",
            "description": "Python script runner",
            "credential_env_names": ["DO_NOT_EXPOSE"],
        },
        OWNER,
    )[0]
    brain.tools.set_state(tool["id"], True, OWNER)
    card = nav(brain, branch="skills")["cards"][0]
    assert "content" not in card and "manifest" not in card
    assert not read(brain, skill["id"], kind="skill")["executable"]
    tools = nav(brain, branch="tools")
    assert tools["cards"][0]["kind"] == "tool" and "DO_NOT_EXPOSE" not in dumps(tools)
    assert "DO_NOT_EXPOSE" not in read(brain, tool["id"], kind="tool")["text"]
    assert nav(brain, branch="tools")["cache_hit"]
    brain.tools.set_state(tool["id"], False, OWNER)
    assert not nav(brain, branch="tools")["cards"]
    assert not nav(brain, branch="skills", scope="atlas")["cards"]


def test_erasure_cleans_directory_source_index_and_hot_cache(brain):
    row = save(brain, "Quartz source")
    source_id = row["source_event_ids"][0]
    assert nav(brain, query="Quartz")["branches"]
    brain.privacy.forget(row["id"], OWNER)
    assert not nav(brain, query="Quartz")["branches"]
    assert not brain.db.one("SELECT 1 FROM episode_fts WHERE id=?", (source_id,))
    assert not brain.db.one("SELECT 1 FROM memory_routes WHERE memory_id=?", (row["id"],))
    brain.memory.rebuild(OWNER)
    assert not nav(brain)["branches"]


def test_quarantine_and_unapproved_facts_never_become_authoritative(brain):
    payload = {
        "actor": "user",
        "scope": "atlas",
        "source_text": "password=synthetic-private-key",
        "facts": [{"memory_type": "USER_PREFERENCE", "predicate": "unsafe", "value": "Do not promote"}],
    }
    result = brain.dispatch("brain.remember", payload, agent())
    assert not result["source_searchable"] and result["approval_required"]
    assert nav(brain)["branches"] == []
    with pytest.raises(Denied):
        read(brain, result["source_event_id"], kind="event")
    with pytest.raises(NotFound):
        read(brain, result["candidates"][0]["id"])


def test_source_only_erasure_has_owner_gate_and_cleans_all_indexes(brain):
    payload = {"source_text": "Orion checkpoint", "scope": "atlas", "actor": "user"}
    result = brain.dispatch("brain.remember", payload, agent())
    identity = result["source_event_id"]
    assert nav(brain, query="Orion")["branches"]
    assert brain.directory.cache
    with pytest.raises(Denied):
        brain.dispatch("brain.forget", {"id": identity, "confirmation": identity}, agent())
    preview = brain.dispatch("brain.forget", {"id": identity}, OWNER)
    assert preview["events"] == 1 and preview["memories"] == 0
    brain.dispatch("brain.forget", {"id": identity, "confirmation": identity}, OWNER)
    assert not brain.directory.cache
    assert not nav(brain, query="Orion")["branches"]
    with pytest.raises(Denied):
        brain.dispatch("brain.remember", payload, agent())

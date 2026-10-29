"""Adversarial retrieval cases: distraction, incomplete packets and disputed evidence."""

import secrets

import pytest

from second_brain.db import dumps
from second_brain.models import OWNER, EventInput, MemoryInput, Principal, SearchInput


def reader(**updates):
    return Principal(role="agent", permissions=["read"], scopes=["global", "atlas"], clearance=1).model_copy(
        update=updates
    )


def record(
    brain,
    value,
    *,
    subject=None,
    predicate="decision",
    topics=None,
    related=None,
    importance=3,
    memory_type="USER_ASSERTED_FACT",
    sensitivity=1,
    scope="atlas",
    valid_from="2024-01-01",
):
    source = brain.events.ingest(
        EventInput(
            source="retrieval-fixture",
            source_id=secrets.token_hex(8),
            text=value,
            scope=scope,
            sensitivity=sensitivity,
            occurred_at=valid_from,
        ),
        OWNER,
    )
    candidate = brain.memory.propose(
        MemoryInput(
            value=value,
            subject=subject or secrets.token_hex(8),
            predicate=predicate,
            scope=scope,
            source_event_ids=[source["id"]],
            topics=topics or [],
            related_memory_ids=related or [],
            importance=importance,
            memory_type=memory_type,
            sensitivity=sensitivity,
            valid_from=valid_from,
        ),
        OWNER,
    )
    return brain.memory.commit(candidate["id"], OWNER)


def test_topic_neighbors_cannot_displace_direct_evidence(brain):
    direct = [record(brain, f"Quartz requirement {i}", topics=["Work/Shared"]) for i in range(6)]
    for i in range(8):
        record(brain, f"Unrelated gardening {i}", topics=["Work/Shared"], importance=5)
    found = brain.retrieval.search(SearchInput(query="Quartz", scope="atlas", limit=4), reader())
    assert len(found["items"]) == 4
    assert {x["id"] for x in found["items"]} <= {x["id"] for x in direct}
    assert all(x["retrieval_path"] == "index" for x in found["items"])


def test_explicit_evidence_precedes_broad_topic_hub_and_explains_path(brain):
    seed = record(brain, "Quartz launch", topics=["Shared"])
    target = record(brain, "Backup owner is Deniz", related=[seed["id"]], importance=1)
    for i in range(15):
        record(brain, f"Garden journal {i}", topics=["Shared"], importance=5)
    found = brain.retrieval.search(SearchInput(query="Quartz", scope="atlas", limit=2), reader())
    assert [x["id"] for x in found["items"]] == [seed["id"], target["id"]]
    assert found["items"][1]["via_memory_id"] == seed["id"]
    assert found["items"][1]["relation"] == "explicit"
    assert found["items"][1]["graph_depth"] == 1


def test_economy_pages_use_one_stable_candidate_window(brain):
    for i in range(30):
        record(brain, f"Quartz item {i}", topics=["Shared"])
    whole = brain.retrieval.search(SearchInput(query="Quartz", limit=30), reader())["items"]
    pages = [
        brain.retrieval.search(SearchInput(query="Quartz", limit=5, offset=i), reader())["items"]
        for i in range(0, 30, 5)
    ]
    assert [x["id"] for page in pages for x in page] == [x["id"] for x in whole]


def test_old_specific_source_beats_recent_weak_matches(brain):
    original = brain.events.ingest(
        EventInput(
            source="conversation",
            source_id="old",
            text="Quartz teslim tarihi 17 Kasım olarak belirlendi.",
            scope="atlas",
            occurred_at="2024-01-01",
        ),
        OWNER,
    )
    for i in range(12):
        brain.events.ingest(
            EventInput(
                source="conversation",
                source_id=str(i),
                text=f"Bahçe teslim notu {i}",
                scope="atlas",
                occurred_at="2026-01-01",
            ),
            OWNER,
        )
    packet = brain.dispatch(
        "brain.prepare_context", {"query": "Quartz teslim", "scope": "atlas", "budget": 2000}, reader()
    )
    assert packet["episodes"][0]["id"] == original["id"]
    assert "17 Kasım" in packet["episodes"][0]["text"]


@pytest.mark.parametrize("budget", [512, 800, 1500, 3000])
def test_context_omissions_are_visible_within_the_entire_byte_budget(brain, budget):
    for i in range(4):
        record(brain, "Quartz " + str(i) + " ayrıntı" * 100)
    packet = brain.dispatch("brain.prepare_context", {"query": "Quartz", "budget": budget}, reader())
    assert packet["truncated"]
    assert len(dumps(packet).encode("utf-8")) == packet["estimated_tokens_upper_bound"] <= budget


def test_source_search_candidate_omission_is_visible(brain):
    for i in range(8):
        brain.events.ingest(
            EventInput(source="conversation", source_id=str(i), text=f"Quartz notu {i}"), OWNER
        )
    packet = brain.dispatch("brain.prepare_context", {"query": "Quartz", "budget": 8000}, reader())
    assert len(packet["episodes"]) == 3 and packet["truncated"]


def test_disputed_alternative_is_marked_without_promoting_it(brain):
    approved = record(brain, "SQLite", subject="Atlas", predicate="database")
    before = brain.memory.get(approved["id"], OWNER)["known_from"]
    disputed = record(brain, "PostgreSQL", subject="Atlas", predicate="database")
    assert disputed["status"] == "disputed"
    packet = brain.dispatch(
        "brain.prepare_context", {"query": "SQLite", "scope": "atlas", "budget": 3000}, reader()
    )
    row = next(x for x in packet["records"] if x["id"] == approved["id"])
    assert row["review_required"]
    assert disputed["id"] not in {x["id"] for x in packet["records"]}
    past = brain.retrieval.search(SearchInput(query="SQLite", known_at=before), reader())
    assert not past["items"][0].get("review_required")
    brain.memory.reject(disputed["id"], OWNER)
    assert not brain.retrieval.search(SearchInput(query="SQLite"), reader())["items"][0].get(
        "review_required"
    )


def test_conflict_signal_does_not_leak_higher_clearance_or_future_alternatives(brain):
    approved = record(brain, "SQLite", subject="Atlas", predicate="database")
    hidden = record(brain, "Hidden alternative", subject="Atlas", predicate="database", sensitivity=2)
    future = record(
        brain, "Future alternative", subject="Atlas", predicate="database", valid_from="2099-01-01"
    )
    assert hidden["status"] == future["status"] == "disputed"
    found = brain.retrieval.search(SearchInput(query="SQLite"), reader())
    assert found["items"][0]["id"] == approved["id"]
    assert not found["items"][0].get("review_required")


def test_source_capture_quality_is_exposed_in_read_and_context(brain):
    saved = brain.dispatch(
        "brain.remember",
        {"source_text": "Quartz için kaynak araştırması yapalım.", "actor": "user", "scope": "atlas"},
        reader(permissions=["read", "capture", "propose"]),
    )
    opened = brain.dispatch("brain.read", {"kind": "event", "id": saved["source_event_id"]}, reader())
    assert opened["actor_is_client_reported"]
    assert opened["capture_path"] == "assistant_selected_excerpt"
    packet = brain.dispatch("brain.prepare_context", {"query": "Quartz", "budget": 3000}, reader())
    assert packet["episodes"][0]["actor_is_client_reported"]
    assert packet["episodes"][0]["capture_path"] == "assistant_selected_excerpt"


def test_evidence_packet_preserves_graph_explanation_without_model_calls(brain, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Memory retrieval attempted an additional model call")

    monkeypatch.setattr("second_brain.providers.LocalEmbedder.embed", forbidden)
    monkeypatch.setattr(brain.provider, "extract", forbidden)
    seed = record(brain, "Quartz release")
    target = record(brain, "Deniz handles backups", related=[seed["id"]])
    packet = brain.dispatch("brain.prepare_context", {"query": "Quartz", "budget": 5000}, reader())
    linked = next(x for x in packet["records"] if x["id"] == target["id"])
    assert linked["retrieval_path"] == "graph" and linked["via_memory_id"] == seed["id"]
    assert not brain.db.one("SELECT 1 FROM usage")


def test_disputed_policy_is_not_silently_ignored_or_replaced(brain):
    first = record(
        brain,
        "Ask before publishing",
        subject="user",
        predicate="publish",
        scope="global",
        memory_type="POLICY",
    )
    second = record(
        brain,
        "Publish immediately",
        subject="user",
        predicate="publish",
        scope="global",
        memory_type="POLICY",
    )
    assert second["status"] == "disputed"
    opened = brain.dispatch("brain.read", {"id": first["id"]}, reader())
    assert opened["review_required"] and opened["text"] == first["value"]
    packet = brain.dispatch("brain.prepare_context", {"query": "Unrelated task", "budget": 3000}, reader())
    assert packet["policy_context_complete"]
    assert packet["records"][0]["review_required"] and packet["records"][0]["id"] == first["id"]


def test_client_metadata_cannot_assert_verified_authorship(brain):
    source = brain.events.ingest(
        EventInput(
            source="unattested-client",
            source_id="claim",
            text="A claimed user message",
            metadata={"actor_is_client_reported": False},
        ),
        OWNER,
    )
    opened = brain.dispatch("brain.read", {"kind": "event", "id": source["id"]}, reader())
    assert opened["actor_is_client_reported"]


def test_context_compilation_does_not_mix_a_concurrent_correction(brain, monkeypatch):
    import threading

    old = record(brain, "SQLite", subject="Atlas", predicate="database")
    source = brain.events.ingest(
        EventInput(
            source="correction", source_id="new", scope="atlas", text="PostgreSQL", occurred_at="2026-01-01"
        ),
        OWNER,
    )
    candidate = brain.memory.propose(
        MemoryInput(
            subject="Atlas",
            predicate="database",
            value="PostgreSQL",
            scope="atlas",
            source_event_ids=[source["id"]],
            supersedes=old["id"],
            valid_from="2026-01-01",
        ),
        OWNER,
    )
    entered, completed = threading.Event(), threading.Event()

    def correct():
        entered.set()
        brain.memory.commit(candidate["id"], OWNER)
        completed.set()

    worker = threading.Thread(target=correct, daemon=True)
    original = brain.retrieval.search
    started = False

    def interleave(request, principal):
        nonlocal started
        found = original(request, principal)
        if not started:
            started = True
            worker.start()
            assert entered.wait(1)
            assert not completed.wait(0.1), "A write interleaved with packet compilation"
        return found

    monkeypatch.setattr(brain.retrieval, "search", interleave)
    packet = brain.dispatch(
        "brain.prepare_context", {"query": "SQLite", "scope": "atlas", "budget": 3000}, reader()
    )
    worker.join(timeout=3)
    assert completed.is_set()
    assert packet["records"][0]["id"] == old["id"]
    assert candidate["id"] not in {x["id"] for x in packet["records"]}

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from second_brain.models import OWNER, EventInput, SearchInput
from second_brain.security import Denied


def test_concurrent_idempotent_capture(brain):
    event = EventInput(source="concurrent", source_id="one", text="Aynı olay")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: brain.events.ingest(event, OWNER), range(16)))
    assert len({r["id"] for r in results}) == 1
    assert sum(not r["duplicate"] for r in results) == 1


def test_entity_merge_preserves_assertions_and_rebuild(brain, make_memory):
    first = make_memory("Python", subject="Ada", predicate="language")
    second = make_memory("Ankara", subject="Ada Yılmaz", predicate="city")
    merged = brain.entities.merge("Ada", "Ada Yılmaz", OWNER)
    assert "Ada Yılmaz" in merged["aliases"]
    for _ in range(2):
        result = brain.retrieval.search(SearchInput(subject="Ada"), OWNER)
        assert {row["id"] for row in result["items"]} == {first["id"], second["id"]}
        assert brain.memory.get(second["id"], OWNER)["subject"] == "Ada Yılmaz"
        brain.memory.rebuild(OWNER)


def test_shared_raw_asset_erasure_closure(brain):
    brain.importer.submit(b"First paragraph\n" + b"A" * 8500, "shared.md", OWNER)
    assert brain.process_one()
    rows = brain.db.rows("SELECT id FROM memories")
    assert len(rows) == 2
    preview = brain.privacy.preview(rows[0]["id"], OWNER)
    assert preview["memories"] == 2 and preview["assets"] == 1
    brain.privacy.forget(rows[0]["id"], OWNER)
    assert brain.db.rows("SELECT * FROM memories") == []
    assert brain.db.rows("SELECT * FROM events") == []
    with pytest.raises(Denied):
        brain.importer.submit(b"First paragraph\n" + b"A" * 8500, "shared.md", OWNER)


def test_bad_backup_password_and_modified_ciphertext(brain, make_memory):
    make_memory("Açık tema")
    backup = brain.backups.create("long-synthetic-passphrase", OWNER)
    with pytest.raises(ValueError):
        brain.backups.verify(backup["id"], "wrong-long-passphrase", OWNER)
    content = bytearray(brain.backups.path(backup["id"]).read_bytes())
    content[-1] ^= 1
    brain.backups.path(backup["id"]).write_bytes(content)
    with pytest.raises(ValueError):
        brain.backups.verify(backup["id"], "long-synthetic-passphrase", OWNER)


@pytest.mark.parametrize("budget", [512, 700, 1000, 3000])
def test_context_never_exceeds_conservative_budget(brain, make_memory, budget):
    for i in range(5):
        make_memory("Uzun Türkçe tercih " * 20, predicate="preference" + str(i))
    packet = brain.dispatch("brain.prepare_context", {"query": "Beynimi tara", "budget": budget}, OWNER)
    assert (
        len(json.dumps(packet, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()) <= budget
    )


def test_historical_wrong_value_not_retrieved_through_any_lexical_engine(brain, make_memory):
    first = make_memory("Ankara")
    make_memory("İstanbul", valid_from="2026-05-01", supersedes=first["id"])
    for engine in ["fts", "bm25", "hybrid", "graph"]:
        assert not brain.retrieval.search(SearchInput(query="Ankara", engine=engine), OWNER)["items"]


def test_job_retry_dead_letter_and_resume(brain):
    job = brain.queue.enqueue("unknown", "failure", {}, OWNER)
    for attempt in range(4):
        claimed = brain.queue.claim()
        assert claimed and claimed["attempts"] == attempt + 1
        brain.queue.fail(claimed, "synthetic failure")
        with brain.db.transaction() as con:
            con.execute("UPDATE jobs SET available_at='2000-01-01' WHERE id=?", (job["id"],))
    assert brain.db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "dead"
    brain.queue.retry(job["id"], OWNER)
    assert brain.queue.claim()["attempts"] == 1

import json
import threading
import time

from second_brain.models import OWNER, SearchInput


def test_heavy_job_does_not_hold_database_lock(brain, make_memory, monkeypatch):
    make_memory("Kısa cevap", predicate="style")
    content = b"Heavy synthetic import"
    job = brain.importer.submit(content, "slow.md", OWNER)
    started, proceed = threading.Event(), threading.Event()

    def slow_import(claimed):
        started.set()
        assert proceed.wait(timeout=5)
        brain.queue.ensure_active(claimed["id"])
        return {"processed": True}

    monkeypatch.setattr(brain.importer, "process", slow_import)
    worker = threading.Thread(target=brain.process_one)
    worker.start()
    try:
        assert started.wait(timeout=3)
        instant = time.monotonic()
        assert brain.retrieval.search(SearchInput(query="cevap"), OWNER)["items"]
        assert time.monotonic() - instant < 1.5
        assert brain.queue.cancel(job["id"], OWNER)["state"] == "cancelled"
    finally:
        proceed.set()
        worker.join(timeout=5)
    assert not worker.is_alive()
    assert brain.db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "cancelled"


def test_cancel_mid_import_stops_later_messages_and_retry_dedups(brain, monkeypatch):
    content = json.dumps(
        [
            {
                "id": "cancel-conversation",
                "mapping": {
                    str(i): {
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["Synthetic message " + str(i)]},
                        }
                    }
                    for i in range(8)
                },
            }
        ]
    ).encode()
    job = brain.importer.submit(content, "conversations.json", OWNER)
    original = brain.events.ingest

    def ingest_then_cancel(event, principal):
        result = original(event, principal)
        brain.queue.cancel(job["id"], OWNER)
        return result

    monkeypatch.setattr(brain.events, "ingest", ingest_then_cancel)
    brain.process_one()
    assert brain.db.one("SELECT COUNT(*) AS n FROM events")["n"] == 1
    assert brain.db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "cancelled"
    monkeypatch.setattr(brain.events, "ingest", original)
    brain.queue.retry(job["id"], OWNER)
    brain.process_one()
    assert brain.db.one("SELECT COUNT(*) AS n FROM events")["n"] == 8
    result = json.loads(brain.db.one("SELECT result FROM jobs WHERE id=?", (job["id"],))["result"])
    assert result["duplicates"] == 1 and result["events"] == 7

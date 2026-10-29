import json

import pytest

from second_brain.models import OWNER, MemoryInput
from second_brain.security import Denied


def test_changed_export_cannot_reintroduce_erased_original(brain):
    data = [
        {
            "id": "conversation",
            "mapping": {
                "msg": {
                    "parent": None,
                    "children": [],
                    "message": {
                        "author": {"role": "user"},
                        "create_time": 1000,
                        "content": {"parts": ["Silinecek kayıt"]},
                    },
                }
            },
        }
    ]
    brain.importer.submit(json.dumps(data).encode(), "conversations.json", OWNER)
    assert brain.process_one()
    event = brain.db.one("SELECT id FROM events")
    record = brain.memory.propose(
        MemoryInput(predicate="fact", value="Silinecek kayıt", source_event_ids=[event["id"]]), OWNER
    )
    brain.privacy.forget(record["id"], OWNER)
    data[0]["title"] = "Metadata changed; message identity stayed the same"
    with pytest.raises(Denied):
        brain.importer.submit(json.dumps(data).encode(), "conversations.json", OWNER)
    assert brain.db.rows("SELECT * FROM assets") == []


def test_identical_unidentified_hooks_are_preserved_as_distinct_arrivals(brain):
    from second_brain.capture import normalize_hook

    payload = {"hook_event_name": "UserPromptSubmit", "session_id": "one", "prompt": "Tekrar dene"}
    first = brain.events.ingest(normalize_hook("codex", payload), OWNER)
    second = brain.events.ingest(normalize_hook("codex", payload), OWNER)
    assert first["id"] != second["id"]

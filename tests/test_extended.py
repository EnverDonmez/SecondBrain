import io

import pytest
from PIL import Image

from second_brain.db import Database
from second_brain.models import OWNER, SearchInput
from second_brain.security import Denied


def test_migration_upgrade_preserves_data(brain, make_memory):
    memory = make_memory("Türkçe")
    with brain.db.transaction() as con:
        for trigger in con.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'context_%'"
        ).fetchall():
            con.execute('DROP TRIGGER "' + trigger["name"] + '"')  # noqa: S608 -- fixed synthetic schema
        for table in ["statement_receipts", "identity_aliases", "context_clock"]:
            con.execute("DROP TABLE " + table)  # noqa: S608 -- fixed synthetic schema
        con.execute("DROP INDEX memory_property_lookup")
        con.execute("DROP INDEX memory_family_lookup")
        con.execute("DROP INDEX memory_future_known")
        con.execute("DROP INDEX event_future_occurrence")
        con.execute("ALTER TABLE memories DROP COLUMN subject_key")
        con.execute("ALTER TABLE memories DROP COLUMN predicate_key")
        for table in ["memory_routes", "memory_sources", "episode_index", "episode_fts"]:
            con.execute("DROP TABLE " + table)  # noqa: S608 -- fixed synthetic migration fixture
        for table in ["event", "skill"]:
            for operation in ["insert", "update", "delete"]:
                con.execute("DROP TRIGGER " + table + "_revision_" + operation)  # noqa: S608
        con.execute("DROP TRIGGER episode_delete")
        for index in ["conversation_lookup", "memory_future_start", "memory_future_end"]:
            con.execute("DROP INDEX " + index)  # noqa: S608
        con.execute("DROP TABLE tool_configs")
        con.execute("DROP TABLE vector_chunks")
        con.execute("DROP TABLE memory_links")
        con.execute("DROP TABLE memory_nodes")
        con.execute("DROP INDEX memory_active_lookup")
        con.execute("ALTER TABLE memories DROP COLUMN topics")
        con.execute("ALTER TABLE memories DROP COLUMN related_memory_ids")
        con.execute("DELETE FROM migrations WHERE version>1")
        con.execute("PRAGMA user_version=1")
    upgraded = Database(brain.db.root)
    assert upgraded.one("SELECT COUNT(*) AS n FROM tool_configs")["n"] == 0
    assert brain.memory.get(memory["id"], OWNER)["value"] == "Türkçe"
    with upgraded.transaction() as con:
        con.execute("PRAGMA user_version=999")
    with pytest.raises(RuntimeError):
        Database(brain.db.root)


def test_image_sidecar_keeps_original_and_cannot_be_user_policy(brain):
    content = io.BytesIO()
    Image.new("RGB", (30, 20), "white").save(content, format="PNG")
    brain.importer.submit(content.getvalue(), "screen.png", OWNER)
    assert brain.process_one()
    asset = brain.db.one("SELECT * FROM assets")
    result = brain.multimodal.derivative(asset["id"], "Sentetik ekran notu", OWNER, "caption", "image")
    assert result["candidate"]["memory_type"] == "EXTERNAL_KNOWLEDGE"
    assert result["candidate"]["status"] == "candidate"
    assert brain.vault.get(asset["id"]) == content.getvalue()
    brain.privacy.forget(result["candidate"]["id"], OWNER)
    assert not brain.vault.path(asset["id"]).exists()


def test_tool_inventory_does_not_grant_execution(brain):
    rows = brain.tools.register(
        "python", "binary", {"binary": "python", "description": "local version probe"}, OWNER
    )
    assert rows[0]["enabled"] == 0
    assert not brain.tools.set_state(rows[0]["id"], True, OWNER)["execution_granted"]
    with pytest.raises(Denied):
        brain.tools.register("unsafe", "binary", {"binary": "powershell", "command": "anything"}, OWNER)


def test_search_pagination_and_pending_status(brain, make_memory):
    for i in range(6):
        make_memory("Türkçe tercih", predicate="style-" + str(i))
    first = brain.retrieval.search(SearchInput(limit=2), OWNER)["items"]
    second = brain.retrieval.search(SearchInput(limit=2, offset=2), OWNER)["items"]
    assert {r["id"] for r in first}.isdisjoint({r["id"] for r in second})
    assert not brain.retrieval.search(SearchInput(status="candidate"), OWNER)["items"]


def test_lexical_context_keeps_long_source_tail_without_model(brain, make_memory):
    value = (
        "Bahçe bakımı ve ağaçların sulanması. " * 100
        + "Mavi mercan araştırması Kuzey Laboratuvarında tamamlandı."
    )
    row = make_memory(value, predicate="report", memory_type="EXTERNAL_KNOWLEDGE", actor="document")
    packet = brain.retrieval.prepare_context("Mavi mercan araştırması", OWNER, budget=3000)
    assert packet["records"]
    record = packet["records"][0]
    assert record["id"] == row["id"] and "Kuzey Laboratuvarında" in record["value"]
    span = record["source_span"]
    assert record["value_is_excerpt"] and value[span["start_char"] : span["end_char"]] == record["value"]

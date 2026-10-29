"""One coherent flow: freshness, identity, evidence reuse and safe erasure."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from second_brain.db import Database, dumps
from second_brain.models import OWNER, EventInput, Principal, SearchInput
from second_brain.security import Denied, NotFound


def reader(**updates):
    return Principal(
        id="connected-ai",
        role="agent",
        scopes=["global", "atlas"],
        clearance=1,
        permissions=["read", "capture", "propose"],
    ).model_copy(update=updates)


def context(brain, principal=None, **updates):
    return brain.dispatch(
        "brain.prepare_context",
        {"query": "Atlas", "scope": "atlas", "budget": 3000, **updates},
        principal or reader(),
    )


def save(brain, text, *, subject="user", predicate="education.year", source_id=None, **updates):
    return brain.dispatch(
        "brain.remember",
        {
            "source_text": text,
            "source_id": source_id or text,
            "actor": "user",
            "facts": [
                {
                    "assertion": "direct_user",
                    "subject": subject,
                    "predicate": predicate,
                    "memory_type": "USER_ASSERTED_FACT",
                    "value": text,
                }
            ],
            **updates,
        },
        reader(),
    )


def test_unchanged_context_uses_only_metadata_not_full_retrieval(brain, make_memory, monkeypatch):
    make_memory("Atlas uses SQLite", scope="atlas")
    first = context(brain)
    assert first["state"] and first["unchanged"] is False
    monkeypatch.setattr(
        brain.retrieval, "search", lambda *a, **k: pytest.fail("Full retrieval on unchanged state")
    )
    monkeypatch.setattr(
        brain.directory, "resources", lambda *a, **k: pytest.fail("Resource scan on unchanged state")
    )
    checked = context(brain, known_state=first["state"])
    assert checked["unchanged"] and "records" not in checked
    assert checked["policy_context_complete"] == first["policy_context_complete"]
    assert len(dumps(checked).encode()) == checked["estimated_tokens_upper_bound"] < 300


@pytest.mark.parametrize(
    "changed", [{"query": "Another task"}, {"scope": "global"}, {"budget": 2400}, {"graph_hops": 2}]
)
def test_state_is_bound_to_exact_request(brain, changed):
    first = context(brain)
    assert not context(brain, known_state=first["state"], **changed).get("unchanged")


@pytest.mark.parametrize(
    "principal", [reader(id="other"), reader(clearance=0), reader(tenant="other"), reader(scopes=["atlas"])]
)
def test_state_is_bound_to_exact_reader(brain, principal):
    first = context(brain)
    assert not context(brain, principal, known_state=first["state"]).get("unchanged")


def test_inaccessible_changes_do_not_expose_activity_or_invalidate_state(brain, make_memory):
    make_memory("Atlas SQLite", scope="atlas")
    first = context(brain)
    make_memory("Private data", scope="private")
    make_memory("Higher clearance", scope="atlas", sensitivity=2)
    assert context(brain, known_state=first["state"])["unchanged"]
    with pytest.raises(Denied):
        context(brain, scope="private", known_state=first["state"])


def test_global_policy_and_visible_source_changes_refresh_task_context(brain, make_memory):
    first = context(brain)
    policy = make_memory("Ask before publishing", memory_type="POLICY", predicate="publish")
    second = context(brain, known_state=first["state"])
    assert not second["unchanged"] and policy["id"] in {r["id"] for r in second["records"]}
    brain.events.ingest(
        EventInput(source="conversation", source_id="one", scope="atlas", text="Atlas milestone"), OWNER
    )
    assert not context(brain, known_state=second["state"])["unchanged"]


def test_skill_and_tool_changes_invalidate_global_capability_context(brain):
    from second_brain.skills import recall_skill_package

    first = context(brain)
    skill = brain.skills.register(recall_skill_package(), OWNER)
    brain.skills.state(skill["id"], True, OWNER)
    second = context(brain, known_state=first["state"])
    assert not second["unchanged"]
    tool = brain.tools.register("python", "binary", {"binary": "python"}, OWNER)[0]
    brain.tools.set_state(tool["id"], True, OWNER)
    assert not context(brain, known_state=second["state"])["unchanged"]


def test_future_transition_invalidates_without_a_new_write(brain, make_memory, monkeypatch):
    import second_brain.context_state as states
    import second_brain.retrieval as retrieval
    import second_brain.directory as directory

    instant = datetime.now(UTC)
    clock = [0]

    def frozen():
        return (instant + timedelta(seconds=clock[0])).isoformat(timespec="microseconds")

    for module in (states, retrieval, directory):
        monkeypatch.setattr(module, "now", frozen)
    future = make_memory(
        "Atlas future milestone", scope="atlas", valid_from=(instant + timedelta(seconds=5)).isoformat()
    )
    first = context(brain)
    assert future["id"] not in {r["id"] for r in first["records"]}
    assert context(brain, known_state=first["state"])["unchanged"]
    clock[0] = 6
    changed = context(brain, known_state=first["state"])
    assert not changed["unchanged"] and future["id"] in {r["id"] for r in changed["records"]}


def test_unchanged_reply_preserves_missing_policy_and_truncation_flags(brain, make_memory):
    make_memory("Never publish without asking. " * 100, memory_type="POLICY")
    first = context(brain, budget=800)
    assert not first["policy_context_complete"] and first["truncated"]
    second = context(brain, budget=800, known_state=first["state"])
    assert second["unchanged"] and not second["policy_context_complete"] and second["truncated"]
    assert len(dumps(second).encode()) <= 800


def test_historical_and_tiny_requests_do_not_reuse_live_state(brain):
    state = context(brain)["state"]
    for request in [{"valid_at": "2025-01-01"}, {"known_at": "2025-01-01"}, {"budget": 512}]:
        result = context(brain, known_state=state, **request)
        assert "state" not in result and not result.get("unchanged")
        assert len(dumps(result).encode()) <= result["budget"]


def test_invalid_state_and_restore_epoch_cannot_reuse_context(brain, make_memory):
    make_memory("Atlas SQLite", scope="atlas")
    first = context(brain)
    assert not context(brain, known_state="forged-state").get("unchanged")
    backup = brain.backups.create("long-synthetic-context-password", OWNER)
    brain.backups.restore(backup["id"], "long-synthetic-context-password", OWNER)
    assert not context(brain, known_state=first["state"])["unchanged"]


def test_property_aliases_and_case_do_not_create_another_active_family(brain):
    old = save(
        brain, "Ben 3. sınıfım.", subject="Kullanıcı", predicate="school_year", occurred_at="2025-01-01"
    )
    new = save(
        brain, "Artık 4. sınıfım.", subject="USER", predicate="Education.Year", occurred_at="2026-01-01"
    )
    assert not new["approval_required"]
    current = brain.retrieval.search(SearchInput(subject="self", predicate="class_year"), reader())["items"]
    assert [r["value"] for r in current] == ["Artık 4. sınıfım."]
    assert current[0]["subject_key"] == "user" and current[0]["predicate_key"] == "education.year"
    before = brain.memory.get(old["applied"][0]["id"], OWNER)
    assert current[0]["logical_id"] == before["logical_id"]
    assert brain.events.get(old["source_event_id"], OWNER)["text"] == "Ben 3. sınıfım."


def test_unrelated_properties_and_scopes_are_not_merged(brain):
    save(brain, "Ben 4. sınıfım.")
    save(brain, "Python kullanıyorum.", predicate="code.language")
    save(brain, "Atlas uses SQLite.", subject="Atlas", predicate="database", scope="atlas")
    values = brain.retrieval.search(SearchInput(query="", subject="user"), reader())["items"]
    assert len(values) == 2
    assert len({r["logical_id"] for r in values}) == 2


def test_exact_repeated_statement_reuses_claim_and_preserves_new_source(brain):
    first = save(brain, "Ben 4. sınıfım.", source_id="message-one", occurred_at="2025-01-01")
    second = save(brain, "Ben 4. sınıfım.", source_id="message-two", occurred_at="2026-01-01")
    identity = first["applied"][0]["id"]
    assert second["applied"][0]["id"] == identity and not second["approval_required"]
    assert brain.db.one("SELECT COUNT(*) n FROM memories")["n"] == 1
    assert brain.db.one("SELECT COUNT(*) n FROM events")["n"] == 2
    assert brain.db.one("SELECT COUNT(*) n FROM statement_receipts")["n"] == 2
    save(brain, "Artık 5. sınıfım.", source_id="message-three", occurred_at="2026-06-01")
    replay = save(brain, "Ben 4. sınıfım.", source_id="message-two", occurred_at="2026-01-01")
    assert replay["applied"][0]["id"] == identity and not replay["applied"][0]["current"]
    source = brain.dispatch("brain.read", {"kind": "event", "id": second["source_event_id"]}, reader())
    assert source["current_memory_refs"][0]["preview"] == "Artık 5. sınıfım."


@pytest.mark.parametrize("erase", ["claim", "repeated_source"])
def test_reused_evidence_is_in_erasure_closure_and_rebuild(brain, erase):
    first = save(brain, "Ben 4. sınıfım.", source_id="message-one")
    repeated = save(brain, "Ben 4. sınıfım.", source_id="message-two")
    brain.memory.rebuild(OWNER)
    target = first["applied"][0]["id"] if erase == "claim" else repeated["source_event_id"]
    closure = brain.privacy.closure(target, OWNER)
    assert len(closure["memories"]) == 1 and len(closure["events"]) == 2
    brain.privacy.forget(target, OWNER)
    assert not brain.db.one("SELECT 1 FROM statement_receipts")
    assert not brain.db.one("SELECT 1 FROM memories") and not brain.db.one("SELECT 1 FROM events")


def test_owner_entity_aliases_apply_to_writes_search_and_rebuild(brain, make_memory):
    first = make_memory("Ankara'da yaşıyorum.", subject="Ada", predicate="city")
    make_memory("Python kullanıyorum.", subject="Ada Yılmaz", predicate="language")
    brain.entities.merge("Ada", "Ada Yılmaz", OWNER)
    saved = save(brain, "İzmir'de yaşıyorum.", subject="Ada Yılmaz", predicate="CITY")
    assert not saved["approval_required"]
    new = brain.memory.get(saved["applied"][0]["id"], OWNER)
    assert new["logical_id"] == first["logical_id"]
    brain.memory.rebuild(OWNER)
    found = brain.retrieval.search(SearchInput(subject="ADA YILMAZ", predicate="city"), reader())["items"]
    # Turkish dotted/dotless letters are not guessed to be interchangeable.
    assert found == []
    found = brain.retrieval.search(
        SearchInput(subject="ADA YILMAZ".replace("I", "ı"), predicate="city"), reader()
    )["items"]
    assert found[0]["value"] == "İzmir'de yaşıyorum."


def test_alias_collision_does_not_choose_between_two_active_claims(brain, make_memory):
    first = make_memory("Ankara", subject="Ada", predicate="city")
    second = make_memory("İzmir", subject="Ada Yılmaz", predicate="city")
    brain.entities.merge("Ada", "Ada Yılmaz", OWNER)
    result = save(brain, "Bursa'da yaşıyorum.", subject="Ada", predicate="city")
    assert result["approval_required"] and not result["applied"]
    assert brain.memory.get(first["id"], OWNER)["known_to"] is None
    assert brain.memory.get(second["id"], OWNER)["known_to"] is None
    found = brain.retrieval.search(SearchInput(subject="Ada", predicate="city"), reader())["items"]
    assert len(found) == 2 and all(row["review_required"] for row in found)


def test_migration_preserves_original_names_and_builds_property_keys(tmp_path, brain, make_memory):
    first = make_memory("Ben 3. sınıfım.", predicate="education.year")
    row = brain.db.one("SELECT * FROM memories WHERE id=?", (first["id"],))
    row.pop("subject_key")
    row.pop("predicate_key")
    row.update(subject="Kullanıcı", predicate="class_year")
    event = brain.db.one("SELECT * FROM events WHERE id=?", (first["source_event_ids"][0],))
    root = tmp_path / "legacy-six"
    root.mkdir()
    with sqlite3.connect(root / "brain.sqlite3") as con:
        for migration in sorted(Path("second_brain/migrations").glob("*.sql"))[:6]:
            con.executescript(migration.read_text("utf-8"))
        con.execute(
            "INSERT INTO events (" + ",".join(event) + ") VALUES (" + ",".join("?" for _ in event) + ")",  # noqa: S608 -- columns from fixed synthetic schema
            tuple(event.values()),
        )
        from second_brain.memory import MemoryRegistry

        MemoryRegistry._insert(con, row)
        con.execute("PRAGMA user_version=6")
        con.commit()
    migrated = Database(root)
    saved = migrated.one("SELECT * FROM memories WHERE id=?", (first["id"],))
    assert saved["subject"] == "Kullanıcı" and saved["predicate"] == "class_year"
    assert saved["subject_key"] == "user" and saved["predicate_key"] == "education.year"
    assert migrated.one("PRAGMA user_version")["user_version"] == 7


def test_reserved_user_identity_cannot_be_merged_with_another_person(brain, make_memory):
    make_memory("A personal fact", subject="user")
    make_memory("A different person's fact", subject="Ada")
    with pytest.raises(ValueError):
        brain.entities.merge("Ada", "user", OWNER)


def test_projection_rebuild_invalidates_an_earlier_context(brain, make_memory):
    make_memory("Atlas SQLite", scope="atlas")
    first = context(brain)
    brain.memory.rebuild(OWNER)
    assert not context(brain, known_state=first["state"])["unchanged"]


def test_invalid_unicode_state_is_rejected_at_the_contract_boundary(brain):
    with pytest.raises(ValueError):
        context(brain, known_state="yanlış-🧠")


def test_normalized_duplicate_properties_are_rejected_before_source_capture(brain):
    with pytest.raises(ValueError):
        brain.dispatch(
            "brain.remember",
            {
                "source_text": "Ben 3. sınıftım, artık 4. sınıfım.",
                "actor": "user",
                "facts": [
                    {
                        "assertion": "direct_user",
                        "subject": s,
                        "predicate": p,
                        "memory_type": "USER_ASSERTED_FACT",
                        "value": v,
                    }
                    for s, p, v in [
                        ("user", "education.year", "3. sınıftım"),
                        ("Kullanıcı", "school_year", "4. sınıfım"),
                    ]
                ],
            },
            reader(),
        )
    assert not brain.db.one("SELECT 1 FROM events")


def test_links_follow_corrected_versions_and_expose_dependency_change(brain, make_memory):
    from second_brain.models import MemoryInput

    old = make_memory(
        "Quartz SQLite", subject="Atlas", predicate="database", scope="atlas", memory_type="DECISION"
    )
    source = brain.events.ingest(
        EventInput(source="fixture", source_id="backup", scope="atlas", text="Backup plan"), OWNER
    )
    linked = brain.memory.propose(
        MemoryInput(
            subject="Backup",
            predicate="plan",
            value="Backup plan",
            scope="atlas",
            source_event_ids=[source["id"]],
            related_memory_ids=[old["id"]],
        ),
        OWNER,
    )
    linked = brain.memory.commit(linked["id"], OWNER)
    new = make_memory(
        "Topaz PostgreSQL",
        subject="Atlas",
        predicate="database",
        scope="atlas",
        memory_type="DECISION",
        supersedes=old["id"],
    )
    found = brain.retrieval.search(SearchInput(query="Topaz", scope="atlas"), reader())["items"]
    neighbor = next(row for row in found if row["id"] == linked["id"])
    assert neighbor["related_version_changed"] and neighbor["via_memory_id"] == new["id"]
    opened = brain.dispatch("brain.read", {"id": linked["id"]}, reader())
    assert opened["related_current_refs"][0]["id"] == new["id"]
    assert brain.memory.get(linked["id"], OWNER)["related_memory_ids"] == [old["id"]]
    brain.memory.rebuild(OWNER)
    found = brain.retrieval.search(SearchInput(query="Topaz", scope="atlas"), reader())["items"]
    assert linked["id"] in {row["id"] for row in found}
    brain.privacy.forget(new["id"], OWNER)
    assert brain.memory.get(linked["id"], OWNER)["related_memory_ids"] == []


def test_core_read_can_open_skill_files_without_an_extra_tool(brain):
    import io
    import zipfile

    package = io.BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            "SKILL.md", "---\nname: source-reader\ndescription: Read sources\n---\nRead selected sources."
        )
        archive.writestr("references/example.txt", "Supporting text")
    skill = brain.skills.register(package.getvalue(), OWNER)
    brain.skills.state(skill["id"], True, OWNER)
    opened = brain.dispatch(
        "brain.read", {"kind": "skill", "id": skill["id"], "path": "references/example.txt"}, reader()
    )
    assert opened["text"] == "Supporting text" and not opened["executable"]
    with pytest.raises(ValueError):
        brain.dispatch(
            "brain.read", {"kind": "skill", "id": skill["id"], "path": "../../owner.token"}, reader()
        )
    brain.skills.state(skill["id"], False, OWNER)
    with pytest.raises((Denied, NotFound)):
        brain.dispatch(
            "brain.read", {"kind": "skill", "id": skill["id"], "path": "references/example.txt"}, reader()
        )


def test_core_startup_does_not_load_optional_numeric_or_media_modules(tmp_path):
    import subprocess
    import sys

    source = "import sys; from second_brain.core import Brain; b=Brain(sys.argv[1]); assert 'numpy' not in sys.modules; assert 'second_brain.local_media' not in sys.modules"
    subprocess.run(  # noqa: S603 -- fixed Python snippet and pytest-owned temp directory, no shell
        [sys.executable, "-c", source, str(tmp_path / "cold-core")],
        check=True,
        timeout=20,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def test_known_managed_legacy_allowlist_can_be_reduced_without_other_changes(tmp_path):
    import tomllib
    from second_brain.connection import activate, codex_entry, config_block
    from second_brain.tool_surface import CORE_TOOLS, LEGACY_TOOLS

    workspace = tmp_path / "project"
    token = workspace / "data/connections/codex/client.token"
    token.parent.mkdir(parents=True)
    token.write_text("synthetic-credential", encoding="utf-8")
    old = codex_entry(workspace, token)
    old["enabled_tools"] = list(LEGACY_TOOLS)
    original = 'model = "keep-existing"\n' + config_block(old) + '\n[mcp_servers.other]\ncommand = "other"\n'
    config = tmp_path / "config.toml"
    config.write_text(original, encoding="utf-8")
    result = activate(workspace, config)
    expected = tomllib.loads(original)
    expected["mcp_servers"]["second-brain"]["enabled_tools"] = CORE_TOOLS
    assert result["upgraded"] and result["removed_tools"]
    assert tomllib.loads(config.read_text("utf-8")) == expected
    assert (token.parent / "config.before-core.toml").read_text("utf-8") == original

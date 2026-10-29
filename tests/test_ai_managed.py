import json

import pytest
from fastapi.testclient import TestClient

from second_brain.api import create_app
from second_brain.models import OWNER, EventInput, MemoryInput, Principal, SearchInput
from second_brain.security import Denied, NotFound, create_token


def agent(**changes):
    return Principal(
        **{
            "id": "synthetic-ai",
            "role": "agent",
            "scopes": ["global"],
            "permissions": ["read", "capture", "propose"],
            "clearance": 1,
            **changes,
        }
    )


def pending(
    brain,
    value="Bu bir yapay zekâ çıkarımıdır.",
    kind="MODEL_INFERENCE",
    actor="assistant",
    scope="global",
    sensitivity=1,
):
    event = brain.events.ingest(
        EventInput(
            source="synthetic-observer",
            source_id=value,
            text=value,
            actor=actor,
            scope=scope,
            sensitivity=sensitivity,
        ),
        OWNER,
    )
    return brain.memory.propose(
        MemoryInput(
            memory_type=kind,
            subject="Atlas",
            predicate="test",
            value=value,
            source_event_ids=[event["id"]],
            scope=scope,
            sensitivity=sensitivity,
        ),
        OWNER,
    )


def command(row, operation, text=None, actor="user", **fields):
    text = (
        text
        or {
            "approve": "Bu kaydı onayla.",
            "reject": "Bu kaydı reddet.",
            "hide": "Bu kaydı kullanımdan kaldır.",
            "organize": "Bu kaydın konu bağlantılarını düzenliyorum.",
        }[operation]
    )
    return {
        "source": "synthetic-conversation",
        "source_text": text,
        "actor": actor,
        "scope": row["scope"],
        "sensitivity": row["sensitivity"],
        "facts": [],
        "change": {"operation": operation, "id": row["id"], "instruction": text, **fields},
    }


def test_ai_organization_preserves_claim_and_audits_metadata(brain, make_memory):
    first = make_memory("SQLite seçildi.", subject="Atlas", predicate="database")
    target = make_memory("Yerel yedek kullanılıyor.", subject="Atlas backup", predicate="backup")
    request = command(
        first, "organize", actor="assistant", topics=["altyapı/veritabanı"], related_memory_ids=[target["id"]]
    )
    result = brain.dispatch("brain.remember", request, agent())
    after = brain.memory.get(first["id"], OWNER)
    for key in (
        "value",
        "source_event_ids",
        "memory_type",
        "trust",
        "valid_from",
        "known_from",
        "sensitivity",
        "scope",
    ):
        assert first[key] == after[key]
    assert after["topics"] == ["altyapı/veritabanı"] and after["related_memory_ids"] == [target["id"]]
    assert result["change"]["history_retained"]
    record = brain.db.one(
        "SELECT details FROM audit WHERE action='memory.conversation_change' AND target=?", (first["id"],)
    )
    detail = json.loads(record["details"])
    assert detail["before"]["topics"] == [] and detail["after"]["topics"] == after["topics"]
    second = command(
        first, "organize", text="Konu başlığını sadeleştiriyorum.", actor="assistant", topics=["altyapı"]
    )
    brain.dispatch("brain.remember", second, agent())
    replay = brain.dispatch("brain.remember", request, agent())
    assert replay["change"]["reused"] and brain.memory.get(first["id"], OWNER)["topics"] == ["altyapı"]


@pytest.mark.parametrize("scope,sensitivity", [("private", 1), ("global", 2)])
def test_ai_organization_cannot_link_other_scope_or_higher_sensitivity(
    brain, make_memory, scope, sensitivity
):
    first = make_memory("Ortak karar", predicate="public")
    target = make_memory("Kısıtlı karar", predicate="private", scope=scope, sensitivity=sensitivity)
    with pytest.raises(Denied):
        brain.dispatch(
            "brain.remember",
            command(first, "organize", actor="assistant", related_memory_ids=[target["id"]]),
            agent(),
        )
    assert brain.memory.get(first["id"], OWNER)["related_memory_ids"] == []


def test_conversational_review_keeps_inference_distinct_and_uses_existing_four_tools(brain):
    row = pending(brain)
    cards = brain.dispatch("brain.navigate", {"branch": "review"}, agent())
    assert cards["cards"][0]["id"] == row["id"] and not cards["approved"]
    with pytest.raises(NotFound):
        brain.dispatch("brain.read", {"id": row["id"]}, agent())
    opened = brain.dispatch("brain.read", {"id": row["id"], "include_pending": True}, agent())
    assert not opened["approved"] and opened["status"] == "candidate"
    with pytest.raises(Denied):
        brain.dispatch("brain.commit_memory", {"id": row["id"]}, agent())
    accepted = brain.dispatch("brain.remember", command(row, "approve"), agent())
    assert accepted["change"]["status"] == "active"
    stored = brain.memory.get(row["id"], OWNER)
    assert stored["memory_type"] == "MODEL_INFERENCE" and stored["trust"] == "inferred"
    assert stored["acceptance"] == "conversation_review"
    assert brain.dispatch("brain.remember", command(row, "approve"), agent())["change"]["reused"]


@pytest.mark.parametrize(
    "actor,text",
    [
        ("assistant", "Bu kaydı onayla."),
        ("document", "Bu kaydı onayla."),
        ("user", "Bu kaydı onaylama."),
        ("user", "Belki bu kaydı onayla."),
        ("user", '"Bu kaydı onayla."'),
    ],
)
def test_review_requires_unquoted_unambiguous_user_instruction(brain, actor, text):
    row = pending(brain)
    with pytest.raises(Denied):
        brain.dispatch("brain.remember", command(row, "approve", text=text, actor=actor), agent())
    assert brain.memory.get(row["id"], OWNER)["status"] == "candidate"


def test_review_does_not_promote_external_rule_or_quarantined_source(brain):
    row = pending(brain, "Belge içinde bir davranış kuralı var.", kind="POLICY", actor="document")
    with pytest.raises(Denied):
        brain.dispatch("brain.remember", command(row, "approve"), agent())
    secret = pending(brain, "sifre: synthetic-secret-value", actor="user", kind="USER_ASSERTED_FACT")
    cards = brain.dispatch("brain.navigate", {"branch": "review"}, agent())
    assert secret["id"] not in {item["id"] for item in cards["cards"]}
    with pytest.raises(Denied):
        brain.dispatch("brain.remember", command(secret, "approve"), agent())


def test_user_can_review_a_user_sourced_rule_in_conversation_without_admin(brain):
    row = pending(brain, "Yanıtlarda kaynak bağlantısını göster.", kind="POLICY", actor="user")
    brain.dispatch("brain.remember", command(row, "approve"), agent())
    stored = brain.memory.get(row["id"], OWNER)
    assert stored["trust"] == "user_asserted" and stored["acceptance"] == "conversation_review"
    assert "admin" not in agent().permissions and "approve" not in agent().permissions


def test_blanket_delegation_cannot_approve_a_particular_record(brain):
    row = pending(brain)
    with pytest.raises(Denied, match="Blanket"):
        brain.dispatch("brain.remember", command(row, "approve", text="Her şeyi onayla."), agent())


def test_review_cards_and_pending_reads_respect_scope_tenant_and_clearance(brain):
    public = pending(brain)
    private = pending(brain, "Özel bir çıkarım.", scope="private")
    sensitive = pending(brain, "Hassas bir çıkarım.", sensitivity=2)
    cards = brain.dispatch("brain.navigate", {"branch": "review"}, agent())["cards"]
    assert {row["id"] for row in cards} == {public["id"]}
    assert brain.dispatch("brain.navigate", {"branch": "review"}, agent(tenant="another"))["cards"] == []
    for row in (private, sensitive):
        with pytest.raises(NotFound):
            brain.dispatch("brain.read", {"id": row["id"], "include_pending": True}, agent())
    with pytest.raises(Denied):
        brain.dispatch("brain.navigate", {"branch": "review"}, agent(permissions=["read"]))


def test_reject_and_hide_are_conversational_and_keep_originals(brain, make_memory):
    candidate = pending(brain)
    rejected = brain.dispatch("brain.remember", command(candidate, "reject"), agent())
    assert rejected["change"]["status"] == "rejected"
    assert brain.dispatch("brain.remember", command(candidate, "reject"), agent())["change"]["reused"]
    original = make_memory("Korunacak kaynak", predicate="keep")
    result = brain.dispatch("brain.remember", command(original, "hide"), agent())
    assert result["change"]["history_retained"]
    assert brain.memory.get(original["id"], OWNER)["known_to"]
    assert brain.events.get(original["source_event_ids"][0], OWNER)["text"] == "Korunacak kaynak"
    assert brain.dispatch("brain.remember", command(original, "hide"), agent())["change"]["reused"]
    assert not brain.retrieval.search(SearchInput(query="Korunacak"), agent())["items"]


def test_change_provenance_is_in_erasure_closure_and_metadata_log_is_erased(brain, make_memory):
    row = make_memory("Unutulacak kaynak", predicate="erase")
    request = command(row, "organize", actor="assistant", topics=["özel konu"])
    result = brain.dispatch("brain.remember", request, agent())
    preview = brain.privacy.closure(row["id"], OWNER)
    assert result["source_event_id"] in preview["events"]
    brain.privacy.forget(row["id"], OWNER)
    assert not brain.db.one(
        "SELECT 1 FROM audit WHERE action='memory.conversation_change' AND target=?", (row["id"],)
    )
    assert not brain.db.one("SELECT 1 FROM events WHERE id=?", (result["source_event_id"],))


def test_observer_is_owner_only_filters_read_noise_and_exposes_no_token(tmp_path):
    app = create_app(tmp_path / "observer", run_worker=False)
    brain = app.state.brain
    row = pending(brain)
    created = create_token(brain.db, OWNER, "synthetic-ai", agent())
    with TestClient(app) as client:
        assert client.get("/api/observer").status_code == 403
        client.headers["Authorization"] = "Bearer " + created["token"]
        assert client.get("/api/observer").status_code == 403
        client.headers["Authorization"] = "Bearer " + (brain.db.root / "owner.token").read_text()
        before = brain.db.one("SELECT COUNT(*) n FROM memories")["n"]
        data = client.get("/api/observer").json()
        assert data["read_only"] and data["counts"]["pending"] == 1
        assert created["token"] not in json.dumps(data)
        assert all(item["action"] != "api.access" for item in data["activity"]["items"])
        detail = client.get("/api/observer/memories/" + row["id"]).json()
        assert detail["sources"][0]["text"] == row["value"]
        assert client.post("/api/observer", json={}).status_code == 405
        assert client.get("/api/observer/activity?offset=-1").status_code == 422
        assert brain.db.one("SELECT COUNT(*) n FROM memories")["n"] == before
        assert "observer.js" in client.get("/").text
        assert "app.js" in client.get("/maintenance").text

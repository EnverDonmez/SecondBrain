import io
import json
import zipfile

import pytest

from second_brain.db import dumps
from second_brain.models import OWNER, EventInput, Principal, SearchInput
from second_brain.security import Denied, NotFound


def agent(**updates):
    return Principal(
        id="test-agent", role="agent", permissions=["read"], scopes=["global", "project"], **updates
    )


def test_project_and_task_context_keep_general_rules(brain, make_memory):
    rule = make_memory("Her tıklama öncesi kontrol", predicate="click", memory_type="POLICY")
    preference = make_memory("Kısa yanıt", predicate="style", memory_type="USER_PREFERENCE")
    project = make_memory("SQLite kararı", predicate="database", scope="project", memory_type="DECISION")
    make_memory("Gizli bütçe", predicate="budget", scope="private")
    for query in ["Beynimi tara", "SQLite"]:
        packet = brain.dispatch(
            "brain.prepare_context", {"query": query, "scope": "project", "budget": 8000}, agent()
        )
        assert {rule["id"], preference["id"], project["id"]} <= {r["id"] for r in packet["records"]}
        assert packet["policy_context_complete"]
        assert {r["scope"] for r in packet["records"]} == {"global", "project"}
        assert set(packet["sources"]) == {s for r in packet["records"] for s in r["source_event_ids"]}
    limited = agent().model_copy(update={"scopes": ["project"]})
    packet = brain.dispatch("brain.prepare_context", {"scope": "project", "budget": 8000}, limited)
    assert [r["id"] for r in packet["records"]] == [project["id"]]
    with pytest.raises(Denied):
        brain.dispatch("brain.prepare_context", {"scope": "private"}, limited)


def test_policy_budget_omission_is_explicit(brain, make_memory):
    make_memory("Bağımsız hedef kontrolü " * 150, predicate="click", memory_type="POLICY")
    for budget in [512, 700, 1000, 6000]:
        packet = brain.dispatch("brain.prepare_context", {"budget": budget}, agent())
        assert len(dumps(packet).encode()) == packet["estimated_tokens_upper_bound"] <= budget
        if not packet["records"]:
            assert not packet["policy_context_complete"]
            assert any("Policy context incomplete" in note for note in packet["uncertainties"])
        else:
            assert packet["policy_context_complete"]


def test_project_rules_are_not_limited_to_bootstrap_page(brain, make_memory):
    ids = {
        make_memory(
            "Proje kuralı " + str(i), predicate="rule-" + str(i), scope="project", memory_type="POLICY"
        )["id"]
        for i in range(20)
    }
    for query in ["Beynimi tara", "hiçbir kayıtla eşleşmeyen sorgu"]:
        packet = brain.dispatch(
            "brain.prepare_context", {"query": query, "scope": "project", "budget": 32000}, agent()
        )
        assert ids <= {r["id"] for r in packet["records"]}
        assert packet["policy_context_complete"]
        if query != "Beynimi tara":
            assert "No task-specific evidence found." in packet["uncertainties"]


def test_tool_discovery_hides_disabled_tenant_and_environment(brain):
    first = brain.tools.register(
        "python", "binary", {"binary": "python", "credential_env_names": ["PRIVATE_ENV_NAME"]}, OWNER
    )[0]
    brain.tools.set_state(first["id"], True, OWNER)
    brain.tools.register("hidden-tool", "mcp", {}, OWNER)
    result = brain.dispatch("brain.list_capabilities", {}, agent())
    assert [t["name"] for t in result["tools"]] == ["python"]
    assert not result["tools"][0]["execution_granted"]
    assert "PRIVATE_ENV_NAME" not in dumps(result)
    assert brain.tools.capabilities(agent().model_copy(update={"tenant": "other"})) == []
    assert brain.tools.capabilities(agent().model_copy(update={"scopes": ["project"]})) == []
    assert brain.tools.capabilities(agent(clearance=0)) == []
    for budget in [512, 1500, 3000]:
        packet = brain.dispatch("brain.prepare_context", {"budget": budget}, agent())
        assert len(dumps(packet).encode()) <= budget
    assert brain.dispatch("brain.prepare_context", {"budget": 3000}, agent())["tools"][0]["name"] == "python"
    exported = json.loads(brain.export(OWNER))
    assert len(exported["tool_configs"]) == 2
    assert any(
        json.loads(row)["table"] == "tool_configs" for row in brain.export(OWNER, "jsonl").splitlines()
    )


def extract(brain, text, source_id="one", actor="user"):
    event = brain.events.ingest(
        EventInput(source="preference-test", source_id=source_id, text=text, actor=actor), OWNER
    )
    return brain.importer.extract_explicit(event["id"], OWNER)["candidates"]


def test_independent_preferences_and_real_conflicts(brain):
    short = extract(brain, "Tercihim: Kısa cevap", "short")[0]
    theme = extract(brain, "Tercihim: Koyu tema", "theme")[0]
    long = extract(brain, "Tercihim: Uzun cevap", "long")[0]
    assert short["predicate"] != theme["predicate"]
    assert long["predicate"] == short["predicate"]
    assert brain.memory.commit(short["id"], OWNER)["status"] == "active"
    assert brain.memory.commit(theme["id"], OWNER)["status"] == "active"
    assert brain.memory.commit(long["id"], OWNER)["status"] == "disputed"


@pytest.mark.parametrize(
    "text,predicates",
    [
        ("Bana hep Türkçe ve kısa cevap ver.", {"reply.language", "reply.length"}),
        ("Uzun listeler yerine paragraf okumayı seviyorum.", {"reply.format"}),
        ("Hocam bir daha tıklamadan önce başka bir ajana kontrol ettir.", {"workflow.click_review"}),
        ("Kaynak göstermeden kesin konuşmanı istemiyorum.", {"reply.sources"}),
        ("Kod örneklerinde Python kullanmanı tercih ederim.", {"code.language"}),
        ("Arayüzlerde koyu tema seviyorum.", {"ui.theme"}),
        ("Benimle konuşurken gereksiz onay soruları sorma.", {"workflow.confirmation"}),
        ("Projelerimi kendi bilgisayarımda çalıştırmak istiyorum.", {"deployment.target"}),
    ],
)
def test_direct_turkish_preferences_remain_unapproved(brain, text, predicates):
    candidates = extract(brain, text)
    assert {c["predicate"] for c in candidates} == predicates
    assert all(c["status"] == "candidate" and c["source_event_ids"] for c in candidates)
    assert not brain.retrieval.search(SearchInput(), OWNER)["items"]


@pytest.mark.parametrize(
    "text",
    [
        "Türkçe cevap vermeni istiyor muyum?",
        'Birisi "Türkçe cevap ver" dedi.',
        "Örneğin koyu tema seviyorum diyebilirim.",
        "Türkçe cevap vermeni istemiyorum.",
        "Koyu tema sevmiyorum.",
        "Kaynak gösterme.",
    ],
)
def test_ambiguous_or_negative_statements_are_not_inverted(brain, text):
    assert not extract(brain, text)


def test_capture_proposes_without_activation_or_permission_escalation(brain):
    event = EventInput(source="capture-test", source_id="one", text="Bana Türkçe ve kısa cevap ver.")
    result = brain.capture(event, OWNER)
    assert len(result["candidates"]) == 2 and result["approval_required"]
    replay = brain.capture(event, OWNER)
    assert {r["id"] for r in result["candidates"]} == {r["id"] for r in replay["candidates"]}
    assert not brain.retrieval.search(SearchInput(), OWNER)["items"]
    capture_only = agent().model_copy(update={"permissions": ["capture"]})
    assert "candidates" not in brain.capture(event.model_copy(update={"source_id": "two"}), capture_only)
    assert not extract(brain, "Tercihim: Koyu tema", "document", actor="document")
    assert not extract(brain, "Tercihim: Koyu tema", "assistant", actor="assistant")


def test_explicit_negative_or_ambiguous_preferences_are_not_reinterpreted(brain):
    negative = extract(brain, "Tercihim: Kaynak gösterme.", "negative")[0]
    assert negative["value"] == "Kaynak gösterme." and negative["predicate"] != "reply.sources"
    assert not extract(brain, "Tercihim: Koyu tema mı?", "question")
    ambiguous = extract(brain, "Tercihim: Türkçe veya İngilizce yanıt", "choice")
    assert len(ambiguous) == 1 and ambiguous[0]["predicate"].startswith("preference.")


def test_chatgpt_import_proposes_only_direct_user_preferences(brain):
    data = [
        {
            "id": "synthetic-history",
            "mapping": {
                "u": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Arayüzlerde koyu tema seviyorum."]},
                    }
                },
                "a": {
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Tercihim: Türkçe kısa yanıt"]},
                    }
                },
            },
        }
    ]
    brain.importer.submit(json.dumps(data).encode(), "history.json", OWNER)
    assert brain.process_one()
    rows = brain.db.rows("SELECT * FROM memories")
    assert len(rows) == 1 and rows[0]["predicate"] == "ui.theme" and rows[0]["status"] == "candidate"
    brain.importer.submit(json.dumps(data).encode(), "history.json", OWNER)
    brain.process_one()
    assert brain.db.one("SELECT COUNT(*) n FROM memories")["n"] == 1


def test_skill_member_read_is_bounded_and_respects_state(brain):
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            "SKILL.md", "---\nname: file-test\ndescription: Read test files\n---\nRead supporting files."
        )
        archive.writestr("scripts/report.py", "print('synthetic report')\n")
        archive.writestr("large.txt", "x" * 65537)
    skill = brain.skills.register(package.getvalue(), OWNER)
    brain.skills.state(skill["id"], True, OWNER)
    result = brain.dispatch("brain.get_skill_file", {"id": skill["id"], "path": "scripts/report.py"}, agent())
    assert result["content"] == "print('synthetic report')\n" and not result["executable"]
    for path in [
        "../owner.token",
        "/owner.token",
        "scripts/../../data/master.key",
        "scripts\\report.py",
        "large.txt",
    ]:
        with pytest.raises(ValueError):
            brain.skills.file(skill["id"], path, agent())
    with pytest.raises(NotFound):
        brain.skills.file(skill["id"], "missing.txt", agent())
    assert brain.skills.list(agent(clearance=0)) == []
    brain.skills.state(skill["id"], False, OWNER)
    with pytest.raises(NotFound):
        brain.skills.file(skill["id"], "scripts/report.py", agent())

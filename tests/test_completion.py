import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from second_brain.models import OWNER, EventInput, Principal, SearchInput
from second_brain.providers import LocalEmbedder
from second_brain.semantic_runtime import SemanticWorker


def test_workflow_paraphrases_keep_sources_and_one_review_candidate(brain):
    phrases = [
        "Tıklamadan önce bağımsız alt ajana hedefi doğrulat.",
        "Her tıklama öncesinde başka bir ajan hedefi kontrol etsin.",
        "Bilgisayarda düğmeye basmadan evvel ikinci ajanın onayını al.",
    ]
    results = [brain.learning.feedback(p, "global", "correction", OWNER) for p in phrases]
    assert [r["evidence_count"] for r in results] == [1, 2, 3]
    lesson = results[-1]["candidate_lesson"]
    assert lesson["status"] == "candidate" and len(lesson["source_event_ids"]) == 3
    repeated = brain.learning.feedback(phrases[-1], "global", "correction", OWNER)
    assert repeated["candidate_lesson"]["id"] == lesson["id"]
    assert brain.db.one("SELECT COUNT(*) n FROM memories")["n"] == 1
    groups = brain.learning.list(OWNER)
    assert len(groups) == 1 and len(groups[0]["variants"]) == 3 and groups[0]["evidence_count"] == 4
    assert not brain.retrieval.search(SearchInput(), OWNER)["items"]


def test_learning_never_merges_scope_outcome_actor_or_sensitive_sources(brain):
    phrase = "Hata düzeltmesinden sonra ilgili testi çalıştır."
    a = brain.learning.feedback(phrase, "global", "correction", OWNER)
    b = brain.learning.feedback(phrase, "private", "correction", OWNER)
    c = brain.learning.feedback(phrase, "global", "failure", OWNER)
    model = Principal(id="model", role="agent", permissions=["read", "capture", "propose"], clearance=1)
    d = brain.learning.feedback(phrase, "global", "correction", model)
    source = brain.events.ingest(
        EventInput(source="sensitive", source_id="one", text=phrase, sensitivity=3), OWNER
    )
    e = brain.learning.feedback(phrase, "global", "correction", OWNER, source["id"])
    assert [r["evidence_count"] for r in [a, b, c, d, e]] == [1] * 5
    opposite = brain.learning.feedback(
        "Hata düzeltmesinden sonra testi çalıştırma.", "global", "correction", OWNER
    )
    assert opposite["evidence_count"] == 1


def test_lexical_cache_invalidates_on_correction_and_erasure(brain, make_memory):
    original = make_memory("SQLite veritabanı", predicate="database")
    query = SearchInput(query="SQLite", engine="bm25")
    assert brain.retrieval.search(query, OWNER)["items"]
    assert brain.retrieval._lexical_cache is not None
    make_memory(
        "PostgreSQL veritabanı", predicate="database", supersedes=original["id"], valid_from="2026-02-01"
    )
    assert not brain.retrieval.search(query, OWNER)["items"]
    current = brain.retrieval.search(SearchInput(query="PostgreSQL", engine="hybrid"), OWNER)["items"][0]
    brain.privacy.forget(current["id"], OWNER)
    assert brain.retrieval._lexical_cache is None and brain.retrieval._vocabulary_cache is None
    assert not brain.retrieval.search(SearchInput(query="PostgreSQL", engine="hybrid"), OWNER)["items"]


def test_vector_cache_is_filtered_and_invalidated(brain, make_memory, monkeypatch):
    public = make_memory("Ortak proje kararı", predicate="one")
    private = make_memory("Gizli proje kararı", predicate="two", scope="private")
    monkeypatch.setattr(LocalEmbedder, "__init__", lambda self, root: None)
    monkeypatch.setattr(LocalEmbedder, "embed", lambda self, texts: [[1, 0]] * len(texts))
    with brain.db.transaction() as con:
        for record in [public, private]:
            con.execute(
                "INSERT INTO vectors VALUES(?,?,?)", (record["id"], LocalEmbedder.model, json.dumps([1, 0]))
            )
    assert len(brain.retrieval.search(SearchInput(query="proje", engine="vector"), OWNER)["items"]) == 2
    reader = Principal(id="reader", role="reader", scopes=["global"], permissions=["read"], clearance=1)
    assert [
        r["id"] for r in brain.retrieval.search(SearchInput(query="proje", engine="vector"), reader)["items"]
    ] == [public["id"]]
    with brain.db.transaction() as con:
        con.execute("DELETE FROM vectors WHERE memory_id=?", (public["id"],))
    assert not brain.retrieval.search(SearchInput(query="proje", engine="vector"), reader)["items"]


@pytest.mark.skipif(not Path("data/models/ready.json").exists(), reason="Local model missing")
def test_worker_utf8_concurrency_idle_exit_and_reload():
    np = pytest.importorskip("numpy")
    worker = SemanticWorker(idle_seconds=0.2)
    directory = str(Path("data/models").resolve())
    try:
        expected = worker.embed(directory, LocalEmbedder.model, ["Türkçe kısa yanıt", "Türkçe kısa yanıt"])
        assert np.allclose(expected[0], expected[1], atol=1e-6)
        first_pid = worker.status()["pid"]
        interpreter_pid = worker.status()["last_usage"]["pid"]
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(
                pool.map(
                    lambda _: worker.embed(directory, LocalEmbedder.model, ["Türkçe kısa yanıt"]), range(3)
                )
            )
        assert all(np.dot(r[0], expected[0]) > 0.999 for r in results)
        deadline = time.monotonic() + 5
        while worker.status()["running"] and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not worker.status()["running"]
        if __import__("sys").platform == "win32":
            import ctypes
            from ctypes import wintypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            handle = kernel.OpenProcess(0x1000, False, interpreter_pid)
            if handle:
                try:
                    code = wintypes.DWORD()
                    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
                    assert kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value != 259
                finally:
                    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                    kernel.CloseHandle(handle)
        actual = worker.embed(directory, LocalEmbedder.model, ["Türkçe kısa yanıt"])
        assert np.dot(actual[0], expected[0]) > 0.999 and worker.status()["pid"] != first_pid
    finally:
        worker.close()


def test_semantic_learning_preserves_contradictions_and_numeric_values(brain, monkeypatch):
    monkeypatch.setenv("SB_MEMORY_MODE", "semantic")
    # Deterministic vectors exercise the grouping boundary independently of model quality.
    monkeypatch.setattr(LocalEmbedder, "__init__", lambda self, root: None)
    monkeypatch.setattr(LocalEmbedder, "embed", lambda self, texts: [[1, 0]] * len(texts))
    phrases = [
        "Dağıtım öncesi bağlantı testini çalıştır",
        "Dağıtım öncesi bağlantı testini uygula",
        "Dağıtım öncesi bağlantı testini doğrula",
    ]
    result = [brain.learning.feedback(p, "global", "correction", OWNER) for p in phrases]
    assert result[-1]["evidence_count"] == 3 and result[-1]["match_method"] == "semantic_complete_link"
    assert (
        brain.learning.feedback("Dağıtım öncesi bağlantı testini çalıştırma", "global", "correction", OWNER)[
            "evidence_count"
        ]
        == 1
    )
    assert (
        brain.learning.feedback(
            "Dağıtım öncesi bağlantı testini 2 kez çalıştır", "global", "correction", OWNER
        )["evidence_count"]
        == 1
    )


def test_codex_activation_preserves_existing_settings_and_limits_token(tmp_path, monkeypatch):
    import httpx
    import tomllib
    import second_brain.connection as connection

    workspace = tmp_path / "workspace"
    (workspace / "data").mkdir(parents=True)
    (workspace / "data/owner.token").write_text("synthetic-owner", encoding="utf-8")
    config = tmp_path / "host/config.toml"
    config.parent.mkdir()
    config.write_text(
        'model = "existing-model"\n[mcp_servers.other]\ncommand = "existing-command"\n', encoding="utf-8"
    )
    issued = []
    original_client = httpx.Client

    def handle(request):
        payload = json.loads(request.content)
        issued.append(payload)
        assert payload["principal"]["permissions"] == ["read", "propose", "capture"]
        assert payload["principal"]["scopes"] == ["global", "secondbrain"]
        assert payload["principal"]["clearance"] == 1
        return httpx.Response(200, json={"id": "test-credential", "token": "synthetic-restricted"})

    monkeypatch.setattr(
        connection.httpx,
        "Client",
        lambda **kwargs: original_client(**kwargs, transport=httpx.MockTransport(handle)),
    )
    result = connection.activate(workspace, config)
    assert result["configured"]
    parsed = tomllib.loads(config.read_text("utf-8"))
    assert (
        parsed["model"] == "existing-model"
        and parsed["mcp_servers"]["other"]["command"] == "existing-command"
    )
    entry = parsed["mcp_servers"]["second-brain"]
    assert "SB_TOKEN" not in entry["env"] and "synthetic-restricted" not in config.read_text("utf-8")
    assert {"brain.commit_memory", "brain.forget"}.isdisjoint(entry["enabled_tools"])
    assert connection.activate(workspace, config)["already_configured"] and len(issued) == 1
    assert (
        (workspace / "data/connections/codex/config.before.toml")
        .read_text("utf-8")
        .startswith('model = "existing-model"')
    )


def test_client_token_file_and_owner_key_guard(tmp_path, monkeypatch):
    from second_brain.credentials import client_token

    monkeypatch.delenv("SB_TOKEN", raising=False)
    restricted = tmp_path / "client.token"
    restricted.write_text("synthetic-restricted", encoding="utf-8")
    monkeypatch.setenv("SB_TOKEN_FILE", str(restricted))
    assert client_token() == "synthetic-restricted"
    owner = tmp_path / "owner.token"
    owner.write_text("synthetic-owner", encoding="utf-8")
    monkeypatch.setenv("SB_TOKEN_FILE", str(owner))
    with pytest.raises(ValueError):
        client_token()

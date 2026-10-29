from second_brain.models import OWNER, SearchInput


def test_bootstrap_profile_is_not_drowned_by_documents(brain, make_memory):
    preferred = make_memory("Türkçe kısa yanıt", predicate="style", memory_type="USER_PREFERENCE")
    for i in range(20):
        make_memory(
            "Yeni dış belge " + str(i),
            predicate="chunk" + str(i),
            subject="document",
            memory_type="EXTERNAL_KNOWLEDGE",
            actor="document",
        )
    packet = brain.dispatch("brain.prepare_context", {"query": "Beynimi tara", "budget": 3000}, OWNER)
    assert preferred["id"] in {row["id"] for row in packet["records"]}
    assert all(row["memory_type"] != "EXTERNAL_KNOWLEDGE" for row in packet["records"])


def test_hybrid_without_downloaded_model_keeps_lexical_branch(brain, make_memory):
    record = make_memory("Türkçe tercih")
    with brain.db.transaction() as con:
        con.execute("INSERT INTO vectors VALUES(?,?,?)", (record["id"], "old-model", "[1,0]"))
    result = brain.retrieval.search(SearchInput(query="Türkçe", engine="hybrid"), OWNER)
    assert result["items"] and result["warnings"]

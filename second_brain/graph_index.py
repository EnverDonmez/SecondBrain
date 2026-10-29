"""Disposable, indexed associations. No model or fuzzy inference at query time."""

import json

from .language import folded


def node_key(value):
    return " ".join(folded(value).split())


def project_associations(con, row):
    con.execute("DELETE FROM memory_nodes WHERE memory_id=?", (row["id"],))
    con.execute("DELETE FROM memory_links WHERE memory_id=?", (row["id"],))
    if row["status"] != "active":
        return
    nodes = {("topic:" + node_key(topic), "topic") for topic in json.loads(row["topics"])}
    # The generic user hub would connect every personal fact to every other fact.
    for value in (row.get("subject_key", row["subject"]), row["value"]):
        key = node_key(value)
        if key and len(key) <= 120 and key not in {"user", "kullanici", "global", "assistant"}:
            nodes.add(("entity:" + key, "entity"))
    con.executemany(
        "INSERT OR IGNORE INTO memory_nodes VALUES(?,?,?)",
        [(row["id"], key, kind) for key, kind in sorted(nodes)],
    )
    for target in json.loads(row["related_memory_ids"]):
        # A forgotten target is never recreated by reindexing an old reference.
        con.execute(
            "INSERT OR IGNORE INTO memory_links "
            "SELECT ?,current.id FROM memories anchor JOIN memories current ON current.logical_id=anchor.logical_id "
            "WHERE anchor.id=? AND anchor.tenant=? AND current.tenant=anchor.tenant "
            "AND current.scope=anchor.scope AND current.status='active' AND current.known_to IS NULL",
            (row["id"], target, row["tenant"]),
        )

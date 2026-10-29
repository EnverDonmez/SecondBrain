"""Incremental, disposable directory and source indexes; never generated knowledge."""

import json

from .graph_index import node_key
from .language import terms
from .security import normalize, risks


def project_routes(con, row):
    con.execute("DELETE FROM memory_routes WHERE memory_id=?", (row["id"],))
    con.execute("DELETE FROM memory_sources WHERE memory_id=?", (row["id"],))
    if row["status"] != "active":
        return
    con.executemany(
        "INSERT OR IGNORE INTO memory_sources VALUES(?,?,?)",
        [(row["id"], source, row["logical_id"]) for source in json.loads(row["source_event_ids"])],
    )
    routes = {}
    for topic in json.loads(row["topics"]):
        parts = [part.strip() for part in topic.split("/") if part.strip()][:6]
        parent = ""
        for part in parts:
            path = parent + "/" + node_key(part) if parent else node_key(part)
            routes[path] = (parent, part)
            parent = path
    con.executemany(
        "INSERT INTO memory_routes VALUES(?,?,?,?)",
        [(row["id"], path, parent, label) for path, (parent, label) in routes.items()],
    )


def project_episode(con, row):
    metadata = json.loads(row["metadata"])
    topics = metadata.get("topics", [])
    topics = [topic for topic in topics if isinstance(topic, str)] if isinstance(topics, list) else []
    hints = str(metadata.get("checkpoint") or "") + " " + " ".join(topics)
    text = row["text"] + " " + hints
    concepts = " ".join("sbconcept" + term[1:] for term in terms(text) if term.startswith("@"))
    con.execute("DELETE FROM episode_fts WHERE id=?", (row["id"],))
    con.execute("INSERT INTO episode_fts VALUES(?,?)", (row["id"], normalize(text + " " + concepts)))
    con.execute("INSERT OR REPLACE INTO episode_index VALUES(?,?)", (row["id"], int(bool(risks(text)))))

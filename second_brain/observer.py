"""Owner's read-only view, derived from canonical records and their audit trail."""

import json

from . import __version__
from .memory import decode
from .models import SearchInput, now
from .security import require


def activity(brain, principal, limit=30, offset=0):
    require(principal, "admin")
    rows = brain.db.rows(
        "SELECT a.*,m.subject,m.predicate,m.scope,m.value,m.memory_type,m.status,m.supersedes,"
        "e.source,e.actor AS source_actor FROM audit a "
        "LEFT JOIN memories m ON m.id=a.target AND m.tenant=a.tenant "
        "LEFT JOIN events e ON e.id=a.target AND e.tenant=a.tenant "
        "WHERE a.tenant=? AND a.action!='api.access' ORDER BY a.created_at DESC,a.id DESC LIMIT ? OFFSET ?",
        (principal.tenant, limit + 1, offset),
    )
    items = []
    for row in rows[:limit]:
        details = json.loads(row.pop("details"))
        item = {
            key: row[key]
            for key in (
                "id",
                "actor",
                "action",
                "target",
                "created_at",
                "subject",
                "predicate",
                "scope",
                "memory_type",
                "status",
                "source",
                "source_actor",
            )
        }
        # Never reconstruct forgotten record values from audit details.
        item["preview"] = row["value"][:240] if row["value"] else None
        item["correction"] = bool(row["supersedes"])
        if row["action"] == "memory.conversation_change":
            item["operation"] = details.get("operation")
        items.append(item)
    return {
        "items": items,
        "more": len(rows) > limit,
        "next_offset": offset + limit if len(rows) > limit else None,
    }


def overview(brain, principal):
    require(principal, "admin")
    instant = now()
    with brain.db.lock:
        current = brain.db.one(
            "SELECT COUNT(*) n FROM memories WHERE tenant=? AND status='active' AND known_to IS NULL "
            "AND valid_from<=? AND (valid_to IS NULL OR valid_to>?)",
            (principal.tenant, instant, instant),
        )["n"]
        pending = brain.db.one(
            "SELECT COUNT(*) n FROM memories WHERE tenant=? AND known_to IS NULL "
            "AND status IN ('candidate','disputed')",
            (principal.tenant,),
        )["n"]
        sources = brain.db.one("SELECT COUNT(*) n FROM events WHERE tenant=?", (principal.tenant,))["n"]
        issues = brain.db.rows(
            "SELECT id,kind,state,error,created_at FROM jobs WHERE tenant=? "
            "AND (state='dead' OR (state='pending' AND error IS NOT NULL)) ORDER BY created_at DESC LIMIT 5",
            (principal.tenant,),
        )
        queue = brain.db.rows(
            "SELECT state,COUNT(*) count FROM jobs WHERE tenant=? GROUP BY state", (principal.tenant,)
        )
        recent = activity(brain, principal, 8)
        connections = []
        for row in brain.db.rows("SELECT id,name,principal,revoked FROM tokens"):
            identity = json.loads(row["principal"])
            if identity["tenant"] != principal.tenant:
                continue
            seen = brain.db.one(
                "SELECT MAX(created_at) seen FROM audit WHERE tenant=? AND actor=? AND action='api.access'",
                (principal.tenant, identity["id"]),
            )["seen"]
            connections.append(
                {
                    "name": row["name"],
                    "enabled": not row["revoked"],
                    "last_seen": seen,
                    "scopes": identity["scopes"],
                }
            )
        attention = brain.db.rows(
            "SELECT id,subject,predicate,memory_type,scope,status,substr(value,1,180) preview "
            "FROM memories WHERE tenant=? AND known_to IS NULL AND status IN ('candidate','disputed') "
            "AND NOT EXISTS (SELECT 1 FROM json_each(memories.risks) r WHERE r.value IN ('possible_secret','instruction_injection')) "
            "ORDER BY created_at DESC,id LIMIT 5",
            (principal.tenant,),
        )
        return {
            "version": __version__,
            "read_only": True,
            "counts": {"current": current, "sources": sources, "pending": pending},
            "activity": recent,
            "attention": attention,
            "issues": issues,
            "queue": queue,
            "connections": connections,
            "memory_mode": "ai_managed",
            "updated_at": instant,
        }


def memories(brain, principal, query="", offset=0, limit=20):
    require(principal, "admin")
    result = brain.retrieval.search(
        SearchInput(query=query, offset=offset, limit=limit + 1, include_candidates=True), principal
    )
    result["more"] = len(result["items"]) > limit
    result["items"] = result["items"][:limit]
    return result


def detail(brain, principal, identity):
    require(principal, "admin")
    row = brain.memory.get(identity, principal)
    history = brain.db.rows(
        "SELECT * FROM memories WHERE tenant=? AND logical_id=? ORDER BY known_from DESC,version DESC,id LIMIT 21",
        (principal.tenant, row["logical_id"]),
    )
    sources = []
    ids = list(row["source_event_ids"])
    ids += [
        r["event_id"]
        for r in brain.db.rows(
            "SELECT event_id FROM statement_receipts WHERE tenant=? AND memory_id=?",
            (principal.tenant, identity),
        )
    ]
    changes = brain.db.rows(
        "SELECT actor,created_at,details FROM audit WHERE tenant=? AND target=? "
        "AND action='memory.conversation_change' ORDER BY created_at DESC LIMIT 20",
        (principal.tenant, identity),
    )
    for change in changes:
        change["details"] = json.loads(change["details"])
        if change["details"].get("source_event_id"):
            ids.append(change["details"]["source_event_id"])
    unique_sources = list(dict.fromkeys(ids))
    for source_id in unique_sources[:10]:
        source = brain.events.get(source_id, principal)
        sources.append(
            {
                **{key: source[key] for key in ("id", "actor", "source", "occurred_at")},
                "text": source["text"][:6000],
                "more": len(source["text"]) > 6000,
            }
        )
    return {
        "memory": row,
        "history": [decode(r) for r in history[:20]],
        "history_more": len(history) > 20,
        "sources_more": len(unique_sources) > 10,
        "sources": sources,
        "changes": changes,
        "read_only": True,
    }

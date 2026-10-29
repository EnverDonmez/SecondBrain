import hashlib
import json
import secrets

from .db import dumps
from .models import EventInput, Principal, now
from .security import Denied, NotFound, audit, require, source_identity


class EventStore:
    def __init__(self, db, vault):
        self.db, self.vault = db, vault

    def ingest(self, event: EventInput, principal: Principal) -> dict:
        require(principal, "capture", event.scope, event.sensitivity)
        data = event.model_dump()
        data.pop("attachments")
        digest = hashlib.sha256(dumps(data).encode()).hexdigest()
        with self.db.transaction() as con:
            if con.execute(
                "SELECT 1 FROM tombstones WHERE tenant=? AND kind='source_key' AND target=?",
                (principal.tenant, source_identity(event.source, event.source_id)),
            ).fetchone():
                return {"id": None, "duplicate": True, "forgotten": True}
            if con.execute(
                "SELECT 1 FROM tombstones WHERE tenant=? AND kind='event_hash' AND target=?",
                (principal.tenant, digest),
            ).fetchone():
                return {"id": None, "duplicate": True, "forgotten": True}
            existing = con.execute(
                "SELECT id FROM events WHERE tenant=? AND source=? AND source_id=? AND content_hash=?",
                (principal.tenant, event.source, event.source_id, digest),
            ).fetchone()
            if existing:
                for aid in event.attachments:
                    asset = con.execute(
                        "SELECT 1 FROM assets WHERE id=? AND tenant=? AND scope=? AND sensitivity<=?",
                        (aid, principal.tenant, event.scope, event.sensitivity),
                    ).fetchone()
                    if not asset:
                        raise Denied("Attachment unavailable")
                    con.execute("INSERT OR IGNORE INTO event_assets VALUES(?,?)", (existing["id"], aid))
                return {"id": existing["id"], "duplicate": True}
            for aid in event.attachments:
                asset = con.execute(
                    "SELECT * FROM assets WHERE id=? AND tenant=?", (aid, principal.tenant)
                ).fetchone()
                if not asset or asset["scope"] != event.scope or asset["sensitivity"] > event.sensitivity:
                    raise Denied("Attachment unavailable in event scope/clearance")
            identity = secrets.token_hex(16)
            created = now()
            con.execute(
                "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    identity,
                    principal.tenant,
                    event.source,
                    event.source_id,
                    event.event_type,
                    event.actor,
                    event.session_id,
                    event.conversation_id,
                    event.parent_id,
                    event.occurred_at or created,
                    created,
                    event.scope,
                    event.sensitivity,
                    event.text,
                    dumps(event.payload),
                    dumps(event.metadata),
                    dumps(event.attachments),
                    digest,
                    event.schema_version,
                ),
            )
            audit(con, principal, "event.ingested", identity, {"source": event.source})
            from .catalog_index import project_episode

            project_episode(con, con.execute("SELECT * FROM events WHERE id=?", (identity,)).fetchone())
            for aid in event.attachments:
                con.execute("INSERT OR IGNORE INTO event_assets VALUES(?,?)", (identity, aid))
        return {"id": identity, "duplicate": False}

    def get(self, identity: str, principal: Principal) -> dict:
        require(principal, "read")
        event = self.db.one("SELECT * FROM events WHERE id=? AND tenant=?", (identity, principal.tenant))
        if not event:
            raise NotFound("Event not found")
        require(principal, "read", event["scope"], event["sensitivity"])
        for field in ("payload", "metadata", "attachments"):
            event[field] = json.loads(event[field])
        event["attachments"] = [
            r["asset_id"]
            for r in self.db.rows("SELECT asset_id FROM event_assets WHERE event_id=?", (identity,))
        ]
        return event

    def list(self, principal: Principal, scope=None, limit=100, offset=0):
        require(principal, "read", scope)
        sql, args = (
            "SELECT * FROM events WHERE tenant=? AND sensitivity<=?",
            [principal.tenant, principal.clearance],
        )
        if "*" not in principal.scopes:
            sql += " AND scope IN (" + ",".join("?" for _ in principal.scopes) + ")"
            args += principal.scopes
        if scope:
            sql += " AND scope=?"
            args += [scope]
        sql += " ORDER BY occurred_at DESC,id LIMIT ? OFFSET ?"
        rows = self.db.rows(sql, (*args, min(limit, 1000), max(offset, 0)))
        for row in rows:
            for field in ("payload", "metadata", "attachments"):
                row[field] = json.loads(row[field])
        return rows

    def store_asset(
        self,
        content: bytes,
        name: str,
        mime: str,
        scope: str,
        sensitivity: int,
        principal: Principal,
        metadata=None,
    ):
        require(principal, "capture", scope, sensitivity)
        digest = hashlib.sha256(content).hexdigest()
        with self.db.transaction() as con:
            if con.execute(
                "SELECT 1 FROM tombstones WHERE tenant=? AND kind='asset_hash' AND target=?",
                (principal.tenant, digest),
            ).fetchone():
                raise Denied("Previously forgotten asset; automatic re-import refused")
            existing = con.execute(
                "SELECT * FROM assets WHERE tenant=? AND hash=? AND scope=?",
                (principal.tenant, digest, scope),
            ).fetchone()
            if existing:
                require(principal, "read", scope, existing["sensitivity"])
                if sensitivity < existing["sensitivity"]:
                    raise Denied("Asset sensitivity downgrade refused")
                return dict(existing)
            aid = secrets.token_hex(16)
            self.vault.put(content, aid)
            try:
                con.execute(
                    "INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        aid,
                        principal.tenant,
                        name,
                        mime,
                        len(content),
                        digest,
                        sensitivity,
                        scope,
                        now(),
                        dumps(metadata or {}),
                    ),
                )
            except BaseException:
                self.vault.erase(aid)
                raise
        return self.db.one("SELECT * FROM assets WHERE id=?", (aid,))

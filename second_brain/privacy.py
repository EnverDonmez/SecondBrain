import json
import os
import secrets
from typing import Callable

from .db import dumps
from .models import now
from .security import NotFound, audit, require, source_identity


class Privacy:
    def __init__(self, db, vault, memory):
        self.db, self.vault, self.memory = db, vault, memory
        self.ledger = db.root / "deletions.jsonl"
        self.projection_delete: Callable | None = None

    def closure(self, memory_id, principal):
        source_only = False
        try:
            record = self.memory.get(memory_id, principal)
        except NotFound:
            event = self.db.one("SELECT * FROM events WHERE id=? AND tenant=?", (memory_id, principal.tenant))
            if not event:
                raise NotFound("Memory or source not found") from None
            require(principal, "read", event["scope"], event["sensitivity"])
            record = {**event, "source_event_ids": [memory_id], "logical_id": None}
            source_only = True
        require(principal, "delete", record["scope"], record["sensitivity"])
        memories = self.db.rows("SELECT * FROM memories WHERE tenant=?", (principal.tenant,))
        support = self.receipts(principal.tenant)
        all_events = self.db.rows("SELECT * FROM events WHERE tenant=?", (principal.tenant,))
        links = self.db.rows(
            "SELECT ea.* FROM event_assets ea JOIN events e ON e.id=ea.event_id WHERE e.tenant=?",
            (principal.tenant,),
        )
        mids = set() if source_only else {memory_id}
        eids = set(record["source_event_ids"])
        logicals = set() if source_only else {record["logical_id"]}
        aids: set[str] = set()
        changed = True
        while changed:
            before = (len(mids), len(eids), len(aids), len(logicals))
            for link in links:
                if link["event_id"] in eids:
                    aids.add(link["asset_id"])
                if link["asset_id"] in aids:
                    eids.add(link["event_id"])
            for row in memories:
                sources = set(json.loads(row["source_event_ids"])) | support.get(row["id"], set())
                if row["logical_id"] in logicals or sources & eids:
                    mids.add(row["id"])
                    logicals.add(row["logical_id"])
                    eids.update(sources)
            changed = before != (len(mids), len(eids), len(aids), len(logicals))
        for row in all_events:
            if row["id"] in eids:
                require(principal, "delete", row["scope"], row["sensitivity"])
        assets = self.db.rows("SELECT * FROM assets WHERE tenant=?", (principal.tenant,))
        hashes = [r["content_hash"] for r in all_events if r["id"] in eids]
        source_keys = [source_identity(r["source"], r["source_id"]) for r in all_events if r["id"] in eids]
        asset_hashes = [r["hash"] for r in assets if r["id"] in aids]
        return {
            "memories": sorted(mids),
            "events": sorted(eids),
            "assets": sorted(aids),
            "event_hashes": hashes,
            "source_keys": source_keys,
            "asset_hashes": asset_hashes,
            "tenant": principal.tenant,
        }

    def preview(self, identity, principal):
        closure = self.closure(identity, principal)
        return {
            "memory_id": identity,
            "memories": len(closure["memories"]),
            "events": len(closure["events"]),
            "assets": len(closure["assets"]),
            "managed_backups_invalidated": len(list((self.db.root / "backups").glob("*.sbbackup"))),
            "warning": "Shared evidence and complete original export archives are erased as a unit; related memories are included. Copies outside this application's data directory cannot be erased.",
        }

    def receipts(self, tenant):
        support: dict[str, set[str]] = {}
        for row in self.db.rows(
            "SELECT memory_id,event_id FROM statement_receipts WHERE tenant=?", (tenant,)
        ):
            support.setdefault(row["memory_id"], set()).add(row["event_id"])
        for row in self.db.rows(
            "SELECT target,json_extract(details,'$.source_event_id') AS event_id FROM audit "
            "WHERE tenant=? AND action='memory.conversation_change'",
            (tenant,),
        ):
            if row["target"] and row["event_id"]:
                support.setdefault(row["target"], set()).add(row["event_id"])
        return support

    def forget(self, identity, principal):
        require(principal, "delete")
        with self.db.lock:
            closure = self.closure(identity, principal)
            entry = {"id": secrets.token_hex(16), "created_at": now(), **closure}
            # Write-ahead erasure log survives an interrupted database transaction and old restores.
            with self.ledger.open("a", encoding="utf-8") as stream:
                stream.write(dumps(entry) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            self.apply(entry)
            removed_backups = []
            for path in (self.db.root / "backups").glob("*.sbbackup"):
                path.unlink()
                removed_backups.append(path.name)
            with self.db.transaction() as con:
                audit(
                    con,
                    principal,
                    "memory.forgotten",
                    identity,
                    {"memory_count": len(closure["memories"]), "event_count": len(closure["events"])},
                )
            with self.db.connect() as con:
                con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                con.execute("VACUUM")
        return {
            "forgotten": identity,
            "counts": {k: len(closure[k]) for k in ("memories", "events", "assets")},
            "invalidated_backups": removed_backups,
            "external_copies": "unmanaged",
        }

    def entries(self):
        if not self.ledger.exists():
            return []
        return [json.loads(line) for line in self.ledger.read_text("utf-8").splitlines() if line.strip()]

    def replay(self):
        for entry in self.entries():
            self.apply(entry)

    def apply(self, entry):
        tenant = entry["tenant"]
        eids, mids, aids = set(entry["events"]), set(entry["memories"]), set(entry["assets"])
        with self.db.transaction() as con:
            # Also match event/asset hashes: identities from a re-imported snapshot may differ.
            for row in con.execute(
                "SELECT id,content_hash,source,source_id FROM events WHERE tenant=?", (tenant,)
            ):
                if row["content_hash"] in entry["event_hashes"] or source_identity(
                    row["source"], row["source_id"]
                ) in entry.get("source_keys", []):
                    eids.add(row["id"])
            for row in con.execute("SELECT id,hash FROM assets WHERE tenant=?", (tenant,)):
                if row["hash"] in entry["asset_hashes"]:
                    aids.add(row["id"])
            memories = con.execute(
                "SELECT id,logical_id,source_event_ids FROM memories WHERE tenant=?", (tenant,)
            ).fetchall()
            support = self.receipts(tenant)
            logicals: set[str] = set()
            changed = True
            while changed:
                before = (len(mids), len(eids), len(logicals))
                for row in memories:
                    sources = set(json.loads(row["source_event_ids"])) | support.get(row["id"], set())
                    if row["id"] in mids or row["logical_id"] in logicals or sources & eids:
                        mids.add(row["id"])
                        logicals.add(row["logical_id"])
                        eids.update(sources)
                changed = before != (len(mids), len(eids), len(logicals))
            for mid in mids:
                con.execute(
                    "DELETE FROM audit WHERE tenant=? AND action='memory.conversation_change' AND target=?",
                    (tenant, mid),
                )
                con.execute("DELETE FROM memories WHERE id=? AND tenant=?", (mid, tenant))
                con.execute("DELETE FROM memory_fts WHERE id=?", (mid,))
                con.execute("DELETE FROM vectors WHERE memory_id=?", (mid,))
                con.execute("DELETE FROM vector_chunks WHERE memory_id=?", (mid,))
                con.execute("DELETE FROM edges WHERE memory_id=?", (mid,))
            for row in con.execute(
                "SELECT id,related_memory_ids FROM memories WHERE tenant=?", (tenant,)
            ).fetchall():
                related = json.loads(row["related_memory_ids"])
                retained = [identity for identity in related if identity not in mids]
                if related != retained:
                    con.execute(
                        "UPDATE memories SET related_memory_ids=? WHERE id=?", (dumps(retained), row["id"])
                    )
            for eid in eids:
                con.execute("DELETE FROM events WHERE id=? AND tenant=?", (eid, tenant))
                con.execute("DELETE FROM event_assets WHERE event_id=?", (eid,))
                con.execute("DELETE FROM feedback WHERE event_id=? AND tenant=?", (eid, tenant))
            for aid in aids:
                con.execute("DELETE FROM assets WHERE id=? AND tenant=?", (aid, tenant))
                con.execute("DELETE FROM event_assets WHERE asset_id=?", (aid,))
                con.execute("DELETE FROM checkpoints WHERE tenant=? AND source=?", (tenant, "import:" + aid))
            for row in con.execute(
                "SELECT id,source_event_ids FROM skills WHERE tenant=?", (tenant,)
            ).fetchall():
                if set(json.loads(row["source_event_ids"])) & eids:
                    con.execute("DELETE FROM skills WHERE id=?", (row["id"],))
            for job in con.execute("SELECT id,payload,result FROM jobs WHERE tenant=?", (tenant,)).fetchall():
                serialized = job["payload"] + (job["result"] or "")
                if any(identity in serialized for identity in aids | eids | mids):
                    con.execute("DELETE FROM jobs WHERE id=?", (job["id"],))
            # Remove orphan derived names while preserving unrelated identity aliases on replay.
            con.execute(
                "DELETE FROM entities WHERE tenant=? AND NOT EXISTS (SELECT 1 FROM memories m WHERE m.tenant=entities.tenant AND (m.subject=entities.name OR substr(m.value,1,200)=entities.name))",
                (tenant,),
            )
            con.execute(
                "DELETE FROM identity_aliases WHERE tenant=? AND NOT EXISTS ("
                "SELECT 1 FROM memories m WHERE m.tenant=identity_aliases.tenant "
                "AND m.subject_key=identity_aliases.canonical_key)",
                (tenant,),
            )
            for kind, targets in [
                ("event_hash", entry["event_hashes"]),
                ("source_key", entry.get("source_keys", [])),
                ("asset_hash", entry["asset_hashes"]),
                ("memory", list(mids)),
                ("event", list(eids)),
                ("asset", list(aids)),
            ]:
                for target in targets:
                    tid = entry["id"] + ":" + kind + ":" + target
                    con.execute(
                        "INSERT OR IGNORE INTO tombstones VALUES(?,?,?,?,?)",
                        (tid, tenant, kind, target, entry["created_at"]),
                    )
        for aid in aids:
            self.vault.erase(aid)
        if self.projection_delete is not None:
            self.projection_delete(mids)

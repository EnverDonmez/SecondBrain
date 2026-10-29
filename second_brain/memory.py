import json
import secrets

from .db import dumps
from .models import MemoryInput, MemoryType, Principal, now
from .language import terms
from .graph_index import project_associations
from .identity import keys as identity_keys, project_keys
from .security import Denied, NotFound, audit, normalize, require, risks
from typing import Callable


def decode(row):
    record = dict(row)
    for key in ("source_event_ids", "risks", "topics", "related_memory_ids"):
        record[key] = json.loads(record[key])
    record["acceptance"] = acceptance(record)
    return record


def acceptance(row):
    accepted_by = row.get("approved_by") or ""
    return (
        "direct_user"
        if accepted_by.startswith("direct-user:")
        else "conversation_review"
        if accepted_by.startswith("conversation-user:")
        else "owner_review"
        if accepted_by
        else "pending_review"
    )


def search_text(row):
    text = " ".join(str(row[x]) for x in ("subject", "predicate", "value", "scope"))
    text += " " + " ".join(json.loads(row["topics"]))
    if "subject_key" in row.keys():
        text += " " + row["subject_key"] + " " + row["predicate_key"]
    concepts = " ".join("sbconcept" + term[1:] for term in terms(text) if term.startswith("@"))
    return normalize(text + " " + concepts)


def project(con, row, catalog=True):
    row = dict(row)
    if "subject_key" in row:
        row["subject_key"], row["predicate_key"] = project_keys(con, row)
    if catalog:
        from .catalog_index import project_routes

        project_routes(con, row)
    project_associations(con, row)
    con.execute("DELETE FROM memory_fts WHERE id=?", (row["id"],))
    con.execute("DELETE FROM edges WHERE memory_id=?", (row["id"],))
    if row["status"] != "active":
        return
    aliases = ""
    if "subject_key" in row:
        aliases = " ".join(
            r[0]
            for r in con.execute(
                "SELECT alias_key FROM identity_aliases WHERE tenant=? AND canonical_key=? ORDER BY alias_key",
                (row["tenant"], row["subject_key"]),
            )
        )
    con.execute("INSERT INTO memory_fts VALUES(?,?)", (row["id"], search_text(row) + " " + aliases))
    for name in (row["subject"], row["value"][:200]):
        con.execute(
            "INSERT OR IGNORE INTO entities VALUES(?,?,?,?,?)",
            (
                secrets.token_hex(16),
                row["tenant"],
                name,
                "subject" if name == row["subject"] else "value",
                "[]",
            ),
        )
    con.execute(
        "INSERT INTO edges VALUES(?,?,?,?,?,?)",
        (
            secrets.token_hex(16),
            row["tenant"],
            row["subject"],
            row["value"][:200],
            row["predicate"],
            row["id"],
        ),
    )


class MemoryRegistry:
    def __init__(self, db, events):
        self.db, self.events = db, events
        self.on_change: Callable | None = None

    def get(self, identity: str, principal: Principal):
        require(principal, "read")
        row = self.db.one("SELECT * FROM memories WHERE id=? AND tenant=?", (identity, principal.tenant))
        if not row:
            raise NotFound("Memory not found")
        require(principal, "read", row["scope"], row["sensitivity"])
        return decode(row)

    def propose(self, candidate: MemoryInput, principal: Principal):
        require(principal, "propose", candidate.scope, candidate.sensitivity)
        candidate = self.canonical_candidate(candidate, principal)
        evidence = [self.events.get(eid, principal) for eid in candidate.source_event_ids]
        if any(event["scope"] != candidate.scope for event in evidence):
            raise Denied("Memory scope must match its evidence")
        if candidate.sensitivity < max(event["sensitivity"] for event in evidence):
            raise Denied("Memory cannot lower evidence sensitivity")
        self.validate_links(candidate, principal)
        trust = "user_asserted" if all(e["actor"] == "user" for e in evidence) else "untrusted"
        if candidate.memory_type == MemoryType.MODEL_INFERENCE:
            trust = "inferred"
        detected = sorted(set(risks(candidate.value) + [risk for e in evidence for risk in risks(e["text"])]))
        if trust != "user_asserted":
            detected.append("untrusted_source")
        identity, created = secrets.token_hex(16), now()
        with self.db.transaction() as con:
            # Evidence may have been erased while the proposal was being validated.
            for eid in candidate.source_event_ids:
                if not con.execute(
                    "SELECT 1 FROM events WHERE id=? AND tenant=?", (eid, principal.tenant)
                ).fetchone():
                    raise NotFound("Evidence no longer exists")
            skey, pkey = identity_keys(con, principal.tenant, candidate.subject, candidate.predicate)
            duplicate = con.execute(
                "SELECT * FROM memories WHERE tenant=? AND scope=? AND subject_key=? AND predicate_key=? AND value=? AND memory_type=? AND source_event_ids=? AND status IN ('candidate','active') AND known_to IS NULL AND valid_from=? AND valid_to IS ?",
                (
                    principal.tenant,
                    candidate.scope,
                    skey,
                    pkey,
                    candidate.value,
                    candidate.memory_type,
                    dumps(candidate.source_event_ids),
                    candidate.valid_from or evidence[0]["occurred_at"],
                    candidate.valid_to,
                ),
            ).fetchone()
            if duplicate:
                return decode(duplicate)
            row = {
                "id": identity,
                "tenant": principal.tenant,
                "logical_id": identity,
                "version": 1,
                "memory_type": candidate.memory_type.value,
                "subject": candidate.subject,
                "predicate": candidate.predicate,
                "value": candidate.value,
                "scope": candidate.scope,
                "confidence": candidate.confidence,
                "sensitivity": candidate.sensitivity,
                "importance": candidate.importance,
                "valid_from": candidate.valid_from or evidence[0]["occurred_at"],
                "valid_to": candidate.valid_to,
                "known_from": created,
                "known_to": None,
                "source_event_ids": dumps(candidate.source_event_ids),
                "supersedes": candidate.supersedes,
                "status": "candidate",
                "trust": trust,
                "risks": dumps(detected),
                "created_at": created,
                "approved_by": None,
                "topics": dumps(candidate.topics),
                "related_memory_ids": dumps(candidate.related_memory_ids),
                "subject_key": skey,
                "predicate_key": pkey,
            }
            self._insert(con, row)
            audit(con, principal, "memory.proposed", identity)
        return self.get(identity, principal)

    def property_keys(self, candidate, principal):
        with self.db.connect() as con:
            return identity_keys(con, principal.tenant, candidate.subject, candidate.predicate)

    def canonical_candidate(self, candidate, principal):
        """Reuse one existing display spelling; scope and source text never change."""
        skey, pkey = self.property_keys(candidate, principal)
        rows = self.db.rows(
            "SELECT DISTINCT subject,predicate FROM memories WHERE tenant=? AND scope=? "
            "AND subject_key=? AND predicate_key=? AND known_to IS NULL AND status='active' "
            "AND sensitivity<=? LIMIT 2",
            (principal.tenant, candidate.scope, skey, pkey, min(principal.clearance, candidate.sensitivity)),
        )
        if len(rows) == 1:
            return candidate.model_copy(update=rows[0])
        return candidate.model_copy(
            update={
                "subject": "user" if skey == "user" else candidate.subject.strip(),
                "predicate": candidate.predicate.strip(),
            }
        )

    def validate_links(self, candidate, principal):
        for target in candidate.related_memory_ids:
            record = self.get(target, principal)
            if record["status"] != "active" or record["known_to"] is not None:
                raise Denied("Related memory must be a current approved version")
            if record["scope"] != candidate.scope or record["sensitivity"] > candidate.sensitivity:
                raise Denied("Links cannot expose another scope or lower a target's sensitivity")
        if candidate.supersedes:
            record = self.get(candidate.supersedes, principal)
            if record["scope"] != candidate.scope or (
                record["subject_key"],
                record["predicate_key"],
            ) != self.property_keys(candidate, principal):
                raise Denied("Correction target must have the same subject, predicate and scope")

    @staticmethod
    def _insert(con, row):
        if "subject_key" in row or con.execute("PRAGMA user_version").fetchone()[0] >= 7:
            row["subject_key"], row["predicate_key"] = identity_keys(
                con, row["tenant"], row["subject"], row["predicate"]
            )
        con.execute(
            "INSERT INTO memories (" + ",".join(row) + ") VALUES (" + ",".join("?" for _ in row) + ")",
            tuple(row.values()),
        )

    def commit(self, identity: str, principal: Principal):
        require(principal, "approve")
        return self._activate(identity, principal)

    def find_source_statement(self, candidate, principal):
        require(principal, "read", candidate.scope, candidate.sensitivity)
        skey, pkey = self.property_keys(candidate, principal)
        row = self.db.one(
            "SELECT m.id FROM memories m WHERE m.tenant=? AND m.scope=? AND m.subject_key=? AND m.predicate_key=? "
            "AND m.memory_type=? AND m.value=? AND (m.source_event_ids=? OR EXISTS ("
            "SELECT 1 FROM statement_receipts r WHERE r.memory_id=m.id AND r.event_id=?)) ORDER BY m.version,m.id LIMIT 1",
            (
                principal.tenant,
                candidate.scope,
                skey,
                pkey,
                candidate.memory_type,
                candidate.value,
                dumps(candidate.source_event_ids),
                candidate.source_event_ids[0] if len(candidate.source_event_ids) == 1 else "",
            ),
        )
        return self.get(row["id"], principal) if row else None

    def accept_user_statement(self, identity: str, principal: Principal):
        for permission in ("read", "capture", "propose"):
            require(principal, permission)
        return self._activate(identity, principal, direct_user=True)

    def _activate(self, identity: str, principal: Principal, direct_user=False, conversation_source=None):
        with self.db.transaction() as con:
            source = con.execute(
                "SELECT * FROM memories WHERE id=? AND tenant=?", (identity, principal.tenant)
            ).fetchone()
            if not source:
                raise NotFound("Memory not found")
            row = dict(source)
            conversation_before = (
                {key: decode(row)[key] for key in ("status", "known_to", "topics", "related_memory_ids")}
                if conversation_source
                else None
            )
            for permission in (
                ("read", "capture", "propose") if direct_user or conversation_source else ("approve",)
            ):
                require(principal, permission, row["scope"], row["sensitivity"])
            if conversation_source:
                # Revalidate the persisted user authorization, never trust a
                # boolean sent by a model or an authority copied from a record.
                from .changes import validate_authorization

                validate_authorization(
                    self.events.get(conversation_source[0], principal), conversation_source[1], row, "approve"
                )
            if row["status"] == "active":
                return decode(row)
            if direct_user:
                reason = self._statement_review_reason(con, row, principal)
                if reason:
                    return {**decode(row), "review_reason": reason}
            if row["status"] not in ("candidate", "disputed"):
                raise Denied("This version cannot be approved")
            detected = json.loads(row["risks"])
            if "possible_secret" in detected or "instruction_injection" in detected:
                raise Denied("Quarantined secret/instruction content cannot become active memory")
            if row["trust"] != "user_asserted" and row["memory_type"] in {
                "POLICY",
                "USER_PREFERENCE",
                "USER_ASSERTED_FACT",
                "SKILL",
                "PROCEDURE",
            }:
                raise Denied(
                    "External/inferred content cannot become an asserted user rule or skill; record a direct user assertion"
                )
            current = con.execute(
                "SELECT * FROM memories WHERE tenant=? AND scope=? AND subject_key=? AND predicate_key=? AND known_to IS NULL AND status='active' AND valid_from < COALESCE(?, '9999') AND COALESCE(valid_to,'9999') > ?",
                (
                    principal.tenant,
                    row["scope"],
                    row["subject_key"],
                    row["predicate_key"],
                    row["valid_to"],
                    row["valid_from"],
                ),
            ).fetchall()
            instant = now()
            if direct_user and current:
                target = current[0]
                if (
                    len(current) != 1
                    or target["memory_type"] != row["memory_type"]
                    or target["sensitivity"] > row["sensitivity"]
                    or target["sensitivity"] > principal.clearance
                    or target["valid_from"] > row["valid_from"]
                    or (row["supersedes"] and row["supersedes"] != target["id"])
                ):
                    return {**decode(row), "review_reason": "update_target_requires_review"}
                if row["value"] == target["value"] and target["valid_to"] is None:
                    # The fresh source remains archived, but an identical
                    # statement need not create another assertion version.
                    con.execute("DELETE FROM memories WHERE id=?", (identity,))
                    self._receipt(con, target, json.loads(row["source_event_ids"])[0], instant)
                    audit(con, principal, "memory.statement_reused", target["id"])
                    return {**decode(target), "statement_reused": True}
                row["supersedes"] = target["id"]
                con.execute("UPDATE memories SET supersedes=? WHERE id=?", (target["id"], identity))
            elif direct_user and row["supersedes"]:
                return {**decode(row), "review_reason": "stale_update_target"}
            if current and not row["supersedes"]:
                con.execute("UPDATE memories SET status='disputed' WHERE id=?", (identity,))
                audit(con, principal, "memory.conflict", identity)
                return decode(con.execute("SELECT * FROM memories WHERE id=?", (identity,)).fetchone())
            if row["supersedes"]:
                old = con.execute(
                    "SELECT * FROM memories WHERE id=? AND tenant=?", (row["supersedes"], principal.tenant)
                ).fetchone()
                if not old or old["status"] != "active" or old["known_to"] is not None:
                    raise Denied("Correction target must be the current transaction version")
                if any(old[k] != row[k] for k in ("subject_key", "predicate_key", "scope")):
                    raise Denied("Correction target must have the same subject, predicate and scope")
                if (old["valid_to"] and row["valid_from"] >= old["valid_to"]) or (
                    row["valid_to"] and row["valid_to"] <= old["valid_from"]
                ):
                    raise Denied("Correction interval must overlap the target interval")
                if any(c["id"] != old["id"] for c in current):
                    raise Denied("Correction overlaps additional assertions; resolve their intervals first")
                row["logical_id"] = old["logical_id"]
                row["version"] = con.execute(
                    "SELECT MAX(version)+1 FROM memories WHERE tenant=? AND logical_id=?",
                    (row["tenant"], old["logical_id"]),
                ).fetchone()[0]
                con.execute("UPDATE memories SET known_to=? WHERE id=?", (instant, old["id"]))
                # Preserve the old valid interval as it is understood after this correction.
                for start, end in [
                    (old["valid_from"], min(row["valid_from"], old["valid_to"] or "9999")),
                    (row["valid_to"], old["valid_to"]),
                ]:
                    if (
                        not start
                        or (end is not None and start >= end)
                        or (
                            start == row["valid_to"]
                            and (old["valid_to"] is not None and start >= old["valid_to"])
                        )
                    ):
                        continue
                    preserved = dict(old)
                    preserved.update(
                        id=secrets.token_hex(16),
                        valid_from=start,
                        valid_to=None if end == "9999" else end,
                        known_from=instant,
                        known_to=None,
                        version=row["version"],
                        supersedes=old["id"],
                    )
                    self._insert(con, preserved)
                    project(con, preserved)
                    if self.on_change:
                        self.on_change(con, preserved, principal)
                    row["version"] += 1
            row.update(
                status="active",
                known_from=instant,
                approved_by="direct-user:" + principal.id
                if direct_user
                else "conversation-user:" + principal.id
                if conversation_source
                else principal.id,
            )
            con.execute(
                "UPDATE memories SET logical_id=?,version=?,status=?,known_from=?,approved_by=? WHERE id=?",
                (row["logical_id"], row["version"], row["status"], instant, row["approved_by"], identity),
            )
            project(con, row)
            if row["supersedes"]:
                # Preserve original references; refresh only the disposable
                # graph projection to this property's valid-time versions.
                con.execute(
                    "INSERT OR IGNORE INTO memory_links "
                    "SELECT l.memory_id,current.id FROM memories anchor "
                    "JOIN memory_links l ON l.target_id=anchor.id "
                    "JOIN memories current ON current.logical_id=anchor.logical_id AND current.tenant=anchor.tenant "
                    "WHERE anchor.tenant=? AND anchor.logical_id=? "
                    "AND current.status='active' AND current.known_to IS NULL",
                    (row["tenant"], row["logical_id"]),
                )
                con.execute(
                    "DELETE FROM memory_links WHERE target_id IN (SELECT id FROM memories "
                    "WHERE tenant=? AND logical_id=? AND known_to IS NOT NULL)",
                    (row["tenant"], row["logical_id"]),
                )
            if direct_user:
                self._receipt(con, row, json.loads(row["source_event_ids"])[0], instant)
            audit(
                con,
                principal,
                "memory.user_statement_accepted" if direct_user else "memory.approved",
                identity,
                {"source_event_id": conversation_source[0]} if conversation_source else None,
            )
            if conversation_source:
                audit(
                    con,
                    principal,
                    "memory.conversation_change",
                    identity,
                    {
                        "operation": "approve",
                        "source_event_id": conversation_source[0],
                        "fingerprint": conversation_source[2],
                        "before": conversation_before,
                        "after": {
                            key: decode(row)[key]
                            for key in ("status", "known_to", "topics", "related_memory_ids")
                        },
                    },
                )
            if self.on_change:
                self.on_change(con, row, principal)
        return self.get(identity, principal)

    @staticmethod
    def _receipt(con, row, event_id, instant):
        con.execute(
            "INSERT OR IGNORE INTO statement_receipts VALUES(?,?,?,?)",
            (row["tenant"], event_id, row["id"], instant),
        )

    def _statement_review_reason(self, con, row, principal):
        from .assertions import DIRECT_TYPES, statement_reason

        if (
            row["status"] != "candidate"
            or row["known_to"] is not None
            or row["memory_type"] not in DIRECT_TYPES
        ):
            return "memory_type_or_state_requires_review"
        if row["valid_from"] > now() or row["valid_to"] is not None:
            return "effective_dates_require_review"
        evidence = [self.events.get(eid, principal) for eid in json.loads(row["source_event_ids"])]
        reason = statement_reason(row["value"], evidence)
        if reason:
            return reason
        disputed = con.execute(
            "SELECT 1 FROM memories WHERE tenant=? AND scope=? AND subject_key=? AND predicate_key=? "
            "AND status='disputed' AND known_to IS NULL AND (valid_to IS NULL OR valid_to>?) LIMIT 1",
            (row["tenant"], row["scope"], row["subject_key"], row["predicate_key"], row["valid_from"]),
        ).fetchone()
        return "unresolved_alternative" if disputed else None

    def reject(self, identity: str, principal: Principal):
        row = self.get(identity, principal)
        require(principal, "approve", row["scope"])
        if row["status"] not in ("candidate", "disputed"):
            raise Denied("Only pending memories can be rejected")
        with self.db.transaction() as con:
            con.execute("UPDATE memories SET status='rejected' WHERE id=?", (identity,))
            audit(con, principal, "memory.rejected", identity)
        return self.get(identity, principal)

    def hide(self, identity: str, principal: Principal):
        row = self.get(identity, principal)
        require(principal, "delete", row["scope"])
        with self.db.transaction() as con:
            con.execute(
                "UPDATE memories SET known_to=? WHERE tenant=? AND logical_id=? AND known_to IS NULL",
                (now(), principal.tenant, row["logical_id"]),
            )
            audit(con, principal, "memory.hidden", identity)
        return {"hidden": identity, "history_retained": True}

    def rebuild(self, principal):
        require(principal, "admin")
        with self.db.transaction() as con:
            con.execute("DELETE FROM memory_fts")
            con.execute("DELETE FROM edges")
            rows = con.execute("SELECT * FROM memories WHERE status='active'").fetchall()
            for row in rows:
                project(con, row)
            con.execute(
                "INSERT INTO context_clock SELECT tenant,scope,sensitivity,'projection',1 FROM memories "
                "WHERE 1 GROUP BY tenant,scope,sensitivity "
                "ON CONFLICT(tenant,scope,sensitivity,kind) DO UPDATE SET revision=revision+1"
            )
            audit(con, principal, "projection.rebuilt", details={"records": len(rows)})
        return {"records": len(rows)}

"""Scoped memory organization and explicit user review through the existing writer."""

import hashlib
import json
import re

from .assertions import statement_reason
from .db import dumps
from .memory import project
from .language import folded
from .models import MemoryInput, now
from .security import Denied, audit, require, risks


def validate_authorization(source, instruction, row, operation=None):
    if source["scope"] != row["scope"] or source["sensitivity"] < row["sensitivity"]:
        raise Denied("Conversation authorization must cover this record's scope and sensitivity")
    if statement_reason(instruction, [source]):
        raise Denied("An explicit, complete user instruction from the conversation is required")
    if operation:
        text = folded(instruction)
        if re.search(r"\b(?:hepsini|her seyi|tum kayitlari|everything|all records)\b", text):
            raise Denied("Blanket delegation is not a specific record review")
        if re.search(
            r"\b(?:onaylama|onaylamiyorum|reddetme|reddetmiyorum|gizleme|kaldirma|istemiyorum|kabul etme|do not|dont)\b",
            text,
        ):
            raise Denied("A negated instruction cannot authorize this action")
        patterns = {
            "approve": r"\b(?:onayla|onayliyorum|kabul et|kabul ediyorum|approve|accept)\b",
            "reject": r"\b(?:reddet|reddediyorum|reject)\b",
            "hide": r"\b(?:kullanimdan kaldir|gizle|hide|artik kullanma)\b",
        }
        if not re.search(patterns[operation], text) and not (
            operation == "approve" and text.strip(" .!\n") == "evet"
        ):
            raise Denied("The user instruction does not clearly authorize the selected operation")


def preflight(brain, request, principal, validate_target=False):
    change = request.change
    row = brain.memory.get(change.id, principal)
    for permission in ("read", "capture", "propose"):
        require(principal, permission, row["scope"], row["sensitivity"])
    if row["scope"] != request.scope or row["sensitivity"] > request.sensitivity:
        raise Denied("Changes cannot cross the source scope or lower its sensitivity")
    if risks(request.source_text) or risks(change.instruction):
        raise Denied("Quarantined source cannot authorize memory changes")
    if change.operation == "organize":
        if change.instruction not in request.source_text or request.actor not in {"user", "assistant"}:
            raise Denied("Organization needs a matching user or assistant source explanation")
        if validate_target and (row["known_to"] is not None or row["status"] == "rejected"):
            raise Denied("Organize the current record, not a historical or rejected version")
        proposal = MemoryInput(**{key: row[key] for key in MemoryInput.model_fields if key in row})
        proposal = proposal.model_copy(
            update={
                key: getattr(change, key)
                for key in ("topics", "related_memory_ids")
                if getattr(change, key) is not None
            }
        )
        if row["id"] in proposal.related_memory_ids:
            raise ValueError("A record cannot link to itself")
        if validate_target:
            brain.memory.validate_links(proposal, principal)
    else:
        validate_authorization(
            {
                "actor": request.actor,
                "text": request.source_text,
                "scope": request.scope,
                "sensitivity": request.sensitivity,
            },
            change.instruction,
            row,
            change.operation,
        )
    return row


def apply_change(brain, request, principal, source_id):
    change = request.change
    row = brain.memory.get(change.id, principal)
    fingerprint = hashlib.sha256(dumps(change.model_dump()).encode()).hexdigest()
    previous = brain.db.one(
        "SELECT details FROM audit WHERE tenant=? AND action='memory.conversation_change' "
        "AND target=? AND json_extract(details,'$.source_event_id')=? ORDER BY created_at LIMIT 1",
        (principal.tenant, row["id"], source_id),
    )
    if previous:
        if json.loads(previous["details"])["fingerprint"] != fingerprint:
            raise ValueError(
                "This source already authorized a different change; use the actual new instruction"
            )
        return {"id": row["id"], "operation": change.operation, "reused": True, "status": row["status"]}
    row = preflight(brain, request, principal, validate_target=True)
    before = {key: row[key] for key in ("status", "known_to", "topics", "related_memory_ids")}
    if change.operation == "approve":
        result = brain.memory._activate(
            row["id"], principal, conversation_source=(source_id, change.instruction, fingerprint)
        )
    else:
        with brain.db.transaction() as con:
            if change.operation == "organize":
                updated = {
                    key: getattr(change, key) if getattr(change, key) is not None else row[key]
                    for key in ("topics", "related_memory_ids")
                }
                con.execute(
                    "UPDATE memories SET topics=?,related_memory_ids=? WHERE id=? AND tenant=?",
                    (
                        dumps(updated["topics"]),
                        dumps(updated["related_memory_ids"]),
                        row["id"],
                        principal.tenant,
                    ),
                )
                raw = con.execute("SELECT * FROM memories WHERE id=?", (row["id"],)).fetchone()
                project(con, raw)
            elif change.operation == "reject":
                if row["status"] not in {"candidate", "disputed"} or row["known_to"] is not None:
                    raise Denied("Only current pending records can be rejected")
                con.execute("UPDATE memories SET status='rejected' WHERE id=?", (row["id"],))
            else:
                if row["status"] != "active" or row["known_to"] is not None:
                    raise Denied("Only a current active record can be hidden; history is retained")
                con.execute(
                    "UPDATE memories SET known_to=? WHERE tenant=? AND logical_id=? AND known_to IS NULL",
                    (now(), principal.tenant, row["logical_id"]),
                )
            # Use this transaction's row, not another connection before commit.
            from .memory import decode

            result = decode(con.execute("SELECT * FROM memories WHERE id=?", (row["id"],)).fetchone())
            after = {key: result[key] for key in before}
            audit(
                con,
                principal,
                "memory.conversation_change",
                row["id"],
                {
                    "operation": change.operation,
                    "source_event_id": source_id,
                    "fingerprint": fingerprint,
                    "before": before,
                    "after": after,
                },
            )
    return {
        "id": row["id"],
        "operation": change.operation,
        "status": result["status"],
        "history_retained": True,
        "reused": False,
    }

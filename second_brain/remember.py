"""Capture assistant-selected evidence and compact candidates without extraction calls."""

import hashlib

from .db import dumps
from .models import EventInput, MemoryInput, RememberInput, now
from .security import Denied, require


def remember(brain, request: RememberInput, principal):
    require(principal, "capture", request.scope, request.sensitivity)
    require(principal, "propose", request.scope, request.sensitivity)
    require(principal, "read", request.scope, request.sensitivity)
    if request.actor != "user" and any(
        fact.memory_type in {"POLICY", "USER_PREFERENCE", "USER_ASSERTED_FACT", "PROCEDURE", "SKILL"}
        for fact in request.facts
    ):
        raise Denied("User assertions require a verbatim user source; label model conclusions as inferences")
    # Validate the complete batch before persisting any evidence. Only this local
    # API process writes; the database lock also protects against owner erasure.
    with brain.db.lock:
        if request.change:
            from .changes import preflight

            preflight(brain, request, principal)
        candidates = [
            brain.memory.canonical_candidate(
                MemoryInput(
                    **fact.model_dump(exclude={"assertion"}),
                    scope=request.scope,
                    sensitivity=request.sensitivity,
                    source_event_ids=["pending-validation"],
                    valid_from=request.occurred_at,
                ),
                principal,
            )
            for fact in request.facts
        ]
        for candidate in candidates:
            brain.memory.validate_links(candidate, principal)
        direct_keys = [
            brain.memory.property_keys(candidate, principal)
            for fact, candidate in zip(request.facts, candidates, strict=True)
            if fact.assertion == "direct_user"
        ]
        if len(set(direct_keys)) != len(direct_keys):
            raise ValueError("Only one direct user statement per subject/predicate is allowed in one batch")
        source_id = (
            request.source_id
            or "excerpt-sha256:"
            + hashlib.sha256(
                dumps(
                    [
                        principal.id,
                        request.source,
                        request.scope,
                        request.actor,
                        request.source_text,
                        request.occurred_at,
                        request.conversation_id,
                    ]
                ).encode("utf-8")
            ).hexdigest()
        )
        source = brain.events.ingest(
            EventInput(
                source=request.source,
                source_id=source_id,
                text=request.source_text,
                actor=request.actor,
                occurred_at=request.occurred_at,
                scope=request.scope,
                sensitivity=request.sensitivity,
                event_type="conversation.memory_excerpt",
                conversation_id=request.conversation_id,
                metadata={
                    "capture_path": "assistant_selected_excerpt",
                    "actor_is_client_reported": True,
                    "source_identity_kind": "client_id" if request.source_id else "excerpt_hash",
                    "checkpoint": request.checkpoint,
                    **({"change": request.change.model_dump()} if request.change else {}),
                    "topics": request.topics,
                },
            ),
            principal,
        )
        if not source.get("id"):
            raise Denied("Previously forgotten evidence cannot be saved again automatically")
        records = []
        change_result = None
        if request.change:
            from .changes import apply_change

            change_result = apply_change(brain, request, principal, source["id"])
        for fact, candidate in zip(request.facts, candidates, strict=True):
            candidate = candidate.model_copy(update={"source_event_ids": [source["id"]]})
            # Retrying old evidence must not undo a later correction, including
            # when its original active version has since become historical.
            existing = (
                brain.memory.find_source_statement(candidate, principal)
                if fact.assertion == "direct_user"
                else None
            )
            if existing:
                row = existing
                if row["status"] == "candidate" and row["known_to"] is None:
                    row = brain.memory.accept_user_statement(row["id"], principal)
            else:
                row = brain.memory.propose(candidate, principal)
                if fact.assertion == "direct_user":
                    row = brain.memory.accept_user_statement(row["id"], principal)
            records.append(row)
    return {
        **({"change": change_result} if change_result else {}),
        "source_event_id": source["id"],
        "source_duplicate": source["duplicate"],
        "candidates": [{"id": row["id"], "status": row["status"]} for row in records],
        "approval_required": any(row["status"] != "active" for row in records)
        or bool(
            change_result and change_result["operation"] == "approve" and change_result["status"] != "active"
        ),
        "applied": [
            {
                "id": row["id"],
                "acceptance": row["acceptance"],
                "current": row["known_to"] is None
                and row["valid_from"] <= now()
                and (row["valid_to"] is None or row["valid_to"] > now()),
            }
            for row in records
            if row["status"] == "active"
        ],
        "review": [
            {"id": row["id"], "reason": row.get("review_reason", "candidate_requires_review")}
            for row in records
            if row["status"] != "active"
        ],
        "additional_model_calls": 0,
        "source_searchable": not brain.db.one(
            "SELECT quarantined FROM episode_index WHERE event_id=?", (source["id"],)
        )["quarantined"],
    }

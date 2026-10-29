import hashlib
import secrets


from .models import EventInput, MemoryInput, MemoryType, now
from .security import normalize, require
from .security import Denied
from .language import lesson_key, polarity, terms, compatible_values


class Learning:
    def __init__(self, core):
        self.core = core

    def feedback(self, text, scope, outcome, principal, source_event_id=None):
        require(principal, "propose", scope)
        if outcome not in {"correction", "success", "failure"}:
            raise ValueError("Outcome must be correction, success or failure")
        if not 1 <= len(text) <= 10000:
            raise ValueError("Feedback length must be between 1 and 10000")
        if source_event_id:
            event = self.core.events.get(source_event_id, principal)
            if event["scope"] != scope:
                raise ValueError("Feedback scope must match source")
        else:
            source_event_id = self.core.events.ingest(
                EventInput(
                    source="feedback",
                    source_id=secrets.token_hex(16),
                    actor="user" if principal.role == "owner" else "assistant",
                    event_type="user.correction" if outcome == "correction" else "experience." + outcome,
                    text=text,
                    scope=scope,
                ),
                principal,
            )["id"]
        event = self.core.events.get(source_event_id, principal)
        canonical = lesson_key(text)
        identity = canonical or normalize(text)
        fingerprint = hashlib.sha256(
            (scope + "\0" + event["actor"] + "\0" + str(event["sensitivity"]) + "\0" + identity).encode()
        ).hexdigest()
        match_method = "workflow_equivalence" if canonical else "exact"
        # Exact/workflow groups are deterministic. Semantic matching is optional,
        # scope/trust/clearance bounded and complete-link to prevent chain drift.
        history = self.core.db.rows(
            "SELECT f.*,e.sensitivity,e.actor FROM feedback f JOIN events e ON e.id=f.event_id "
            "WHERE f.tenant=? AND f.scope=? AND f.outcome=? AND e.sensitivity=? AND e.actor=? "
            "ORDER BY f.created_at DESC LIMIT 200",
            (principal.tenant, scope, outcome, event["sensitivity"], event["actor"]),
        )
        exact = next((r for r in history if normalize(r["lesson"]) == normalize(text)), None)
        if exact:
            fingerprint = exact["fingerprint"]
        elif not canonical and not any(r["fingerprint"] == fingerprint for r in history):
            fingerprint, match_method = self._semantic_group(text, history, fingerprint)
        with self.core.db.transaction() as con:
            existing = con.execute(
                "SELECT id FROM feedback WHERE tenant=? AND event_id=? AND fingerprint=? AND outcome=?",
                (principal.tenant, source_event_id, fingerprint, outcome),
            ).fetchone()
            if not existing:
                con.execute(
                    "INSERT INTO feedback VALUES(?,?,?,?,?,?,?,?)",
                    (
                        secrets.token_hex(16),
                        principal.tenant,
                        source_event_id,
                        text,
                        scope,
                        outcome,
                        fingerprint,
                        now(),
                    ),
                )
        records = self.core.db.rows(
            "SELECT DISTINCT f.event_id,e.sensitivity,e.occurred_at FROM feedback f JOIN events e ON e.id=f.event_id "
            "WHERE f.tenant=? AND f.scope=? AND f.fingerprint=? AND f.outcome=? AND e.sensitivity<=? AND e.actor=? "
            "ORDER BY e.occurred_at,f.event_id",
            (principal.tenant, scope, fingerprint, outcome, principal.clearance, event["actor"]),
        )
        lesson = None
        if len(records) >= 3 and outcome != "failure":
            existing_lesson = self.core.db.one(
                "SELECT * FROM memories WHERE tenant=? AND scope=? AND predicate=? AND memory_type='LESSON' "
                "AND status IN ('candidate','active','disputed','rejected') ORDER BY created_at LIMIT 1",
                (principal.tenant, scope, "lesson:" + fingerprint[:16]),
            )
            if existing_lesson:
                lesson = self.core.memory.get(existing_lesson["id"], principal)
            else:
                lesson = self.core.memory.propose(
                    MemoryInput(
                        memory_type=MemoryType.LESSON,
                        predicate="lesson:" + fingerprint[:16],
                        value=text,
                        source_event_ids=[r["event_id"] for r in records],
                        scope=scope,
                        confidence=min(0.95, 0.5 + len(records) * 0.1),
                        sensitivity=max(r["sensitivity"] for r in records),
                        valid_from=records[0]["occurred_at"],
                    ),
                    principal,
                )
        return {
            "evidence_count": len(records),
            "candidate_lesson": lesson,
            "approval_required": True,
            "failure_recorded": outcome == "failure",
            "match_method": match_method,
        }

    def _semantic_group(self, text, history, fallback):
        import os

        if not history or os.environ.get("SB_MEMORY_MODE", "economy") != "semantic":
            return fallback, "exact"
        # Negation and numbers are protected: embedding closeness alone cannot
        # equate opposing instructions or different concrete values.
        import re
        from .providers import LocalEmbedder

        compatible = [
            r
            for r in history
            if polarity(text) == polarity(r["lesson"])
            and compatible_values(text, r["lesson"])
            and re.findall(r"\d+", text) == re.findall(r"\d+", r["lesson"])
            and len(set(terms(text)) & set(terms(r["lesson"]))) >= 2
        ]
        if not compatible:
            return fallback, "exact"
        import numpy as np

        texts = list(dict.fromkeys(r["lesson"] for r in compatible))
        try:
            vectors = np.asarray(LocalEmbedder(self.core.db.root).embed([text] + texts), dtype=np.float32)
        except Denied:
            return fallback, "exact"
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
        similarities = dict(zip(texts, (vectors[1:] @ vectors[0]).tolist(), strict=True))
        matches = []
        for fingerprint in {r["fingerprint"] for r in compatible}:
            group = [r for r in history if r["fingerprint"] == fingerprint]
            if all(similarities.get(r["lesson"], 0) >= 0.88 for r in group):
                matches.append((min(similarities[r["lesson"]] for r in group), fingerprint))
        if len(matches) == 1:
            return matches[0][1], "semantic_complete_link"
        return fallback, "exact"

    def list(self, principal):
        require(principal, "approve")
        rows = self.core.db.rows(
            "SELECT f.* FROM feedback f JOIN events e ON e.id=f.event_id WHERE f.tenant=? AND e.sensitivity<=? ORDER BY f.created_at DESC",
            (principal.tenant, principal.clearance),
        )
        groups: dict[tuple, dict] = {}
        for row in rows:
            if not principal.permits_scope(row["scope"]):
                continue
            key = (row["fingerprint"], row["scope"], row["outcome"])
            group = groups.setdefault(
                key,
                {
                    "fingerprint": row["fingerprint"],
                    "lesson": row["lesson"],
                    "scope": row["scope"],
                    "outcome": row["outcome"],
                    "last_seen": row["created_at"],
                    "variants": [],
                    "source_event_ids": [],
                },
            )
            if row["lesson"] not in group["variants"]:
                group["variants"].append(row["lesson"])
            if row["event_id"] not in group["source_event_ids"]:
                group["source_event_ids"].append(row["event_id"])
        return [{**group, "evidence_count": len(group["source_event_ids"])} for group in groups.values()]

"""Small conditional context checks, scoped to the exact reader and request."""

import base64
import hmac
import secrets

from .db import dumps
from .models import now
from .security import require


class ContextState:
    def __init__(self, core):
        self.core = core
        self.invalidate()

    def invalidate(self):
        # Restart/restore never accepts a state from an earlier database epoch.
        self.nonce = secrets.token_bytes(16)

    def fingerprint(self, request, principal):
        require(principal, "read", request.scope)
        if (
            request.budget < 800
            or request.engine not in {"economy", "fts", "graph"}
            or any((request.valid_at, request.known_at, request.since, request.until))
        ):
            return None
        where, args = "tenant=? AND sensitivity<=?", [principal.tenant, principal.clearance]
        scopes: list[str] | None
        if request.scope is not None:
            scopes = [request.scope]
            if principal.permits_scope("global") and "global" not in scopes:
                scopes.append("global")
        else:
            scopes = None if "*" in principal.scopes else sorted(set(principal.scopes))
        if scopes is not None:
            where += " AND scope IN (" + ",".join("?" for _ in scopes) + ")"
            args += scopes
        clock = self.core.db.rows(
            "SELECT scope,sensitivity,kind,revision FROM context_clock WHERE "
            + where
            + " ORDER BY scope,sensitivity,kind",
            args,
        )
        instant = now()
        boundary = self.core.db.one(
            "SELECT MIN(t) AS t FROM ("
            "SELECT MIN(valid_from) t FROM memories WHERE "
            + where
            + " AND status='active' AND known_to IS NULL AND valid_from>? UNION ALL "
            "SELECT MIN(valid_to) FROM memories WHERE "
            + where
            + " AND status='active' AND known_to IS NULL AND valid_to>? UNION ALL "
            "SELECT MIN(known_from) FROM memories WHERE "
            + where
            + " AND status='active' AND known_to IS NULL AND known_from>? UNION ALL "
            "SELECT MIN(occurred_at) FROM events WHERE " + where + " AND occurred_at>?)",
            (*args, instant, *args, instant, *args, instant, *args, instant),
        )["t"]
        body = {
            "reader": principal.model_dump(mode="json"),
            "clock": clock,
            "next_boundary": boundary,
            "request": request.model_dump(mode="json", exclude={"known_state"}),
        }
        return hmac.digest(self.core.vault.key, self.nonce + dumps(body).encode(), "sha256")

    def token(self, fingerprint, policy_complete, truncated):
        flags = bytes([int(policy_complete), int(truncated)])
        digest = hmac.digest(self.core.vault.key, fingerprint + flags, "sha256")
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def match(self, known_state, fingerprint):
        if not known_state or fingerprint is None:
            return None
        for complete in (True, False):
            for truncated in (True, False):
                if hmac.compare_digest(known_state, self.token(fingerprint, complete, truncated)):
                    return complete, truncated
        return None

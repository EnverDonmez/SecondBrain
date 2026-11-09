"""Small conditional context checks, scoped to the exact reader and request."""

import base64
import binascii
import hmac
import secrets
import time

from .db import dumps
from .language import is_continuity_query
from .models import ContextInput, ContextSection, NavigateInput, Principal, now
from .retrieval import measure_context
from .security import require

STATE_TTL = 600
SECTION_RESERVE = 560
SECTIONS: tuple[ContextSection, ...] = ("records", "sources", "episodes", "handoffs", "skills", "tools")


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
        handoffs = []
        if is_continuity_query(request.query):
            clock = [row for row in clock if row["kind"] == "memory"]
            handoffs = [
                row["id"]
                for row in self.core.directory.handoffs(NavigateInput(scope=request.scope), principal)
            ]
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
            "handoffs": handoffs,
            "next_boundary": boundary,
            "request": request.model_dump(mode="json", exclude={"known_state", "known_sections"}),
        }
        return hmac.digest(self.core.vault.key, self.nonce + dumps(body).encode(), "sha256")

    def token(self, fingerprint, policy_complete, truncated):
        header = int(time.time()).to_bytes(4, "big") + bytes([int(policy_complete), int(truncated)])
        digest = hmac.digest(self.core.vault.key, fingerprint + header, "sha256")
        return base64.urlsafe_b64encode(header + digest).decode().rstrip("=")

    def match(self, known_state, fingerprint):
        if not known_state or fingerprint is None:
            return None
        try:
            raw = base64.urlsafe_b64decode(known_state + "=" * (-len(known_state) % 4))
        except (ValueError, binascii.Error):
            return None
        if len(raw) != 38 or not 0 <= int(time.time()) - int.from_bytes(raw[:4], "big") < STATE_TTL:
            return None
        if hmac.compare_digest(raw[6:], hmac.digest(self.core.vault.key, fingerprint + raw[:6], "sha256")):
            return bool(raw[4]), bool(raw[5])
        return None

    def apply_sections(self, packet, request: ContextInput, principal: Principal):
        retained = request.known_sections or {}
        context = dumps(
            {
                "reader": principal.model_dump(mode="json"),
                "request": request.model_dump(mode="json", exclude={"known_state", "known_sections"}),
            }
        ).encode()
        key = hmac.digest(self.core.vault.key, self.nonce + context, "sha256")
        packet["budget"] = request.budget
        packet["section_states"], packet["unchanged_sections"] = {}, []
        for section in SECTIONS:
            if section not in packet:
                continue
            digest = hmac.digest(key, dumps([section, packet[section]]).encode(), "sha256")
            previous = retained.get(section)
            if previous and self.match(previous, digest) is not None:
                packet["section_states"][section] = previous
                packet["unchanged_sections"].append(section)
                del packet[section]
            else:
                packet["section_states"][section] = self.token(digest, False, False)
        measure_context(packet)
        return packet

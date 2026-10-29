import hashlib
import re
import secrets
import unicodedata

from .db import dumps
from .models import Principal, now


class Denied(Exception):
    pass


class NotFound(Exception):
    pass


def source_identity(source: str, source_id: str) -> str:
    return hashlib.sha256(dumps([source, source_id]).encode()).hexdigest()


def require(principal: Principal, permission: str, scope: str | None = None, sensitivity: int = 0):
    if permission not in principal.permissions:
        raise Denied(f"Permission required: {permission}")
    if scope is not None and not principal.permits_scope(scope):
        raise Denied("Scope access denied")
    if sensitivity > principal.clearance:
        raise Denied("Sensitivity clearance exceeded")


def normalize(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı").casefold()
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def risks(text: str) -> list[str]:
    normalized = normalize(text)
    found = []
    if re.search(
        r"(?i)(sk-[a-z0-9_-]{16,}|AKIA[A-Z0-9]{16}|-----BEGIN .*PRIVATE KEY|(?:api[_ -]?key|password|sifre|token)\s*[:=]\s*\S{8,})",
        text,
    ):
        found.append("possible_secret")
    if re.search(
        r"ignore.{0,40}(previous|instructions)|system prompt|onceki.{0,30}talimat.{0,30}(unut|yok say)|tum dosyalar.{0,30}sil|disable.{0,20}(security|auth)",
        normalized,
    ):
        found.append("instruction_injection")
    return found


def audit(con, principal: Principal, action: str, target: str | None = None, details: dict | None = None):
    con.execute(
        "INSERT INTO audit VALUES(?,?,?,?,?,?,?)",
        (secrets.token_hex(16), principal.tenant, principal.id, action, target, now(), dumps(details or {})),
    )


def create_token(db, owner: Principal, name: str, principal: Principal) -> dict:
    require(owner, "admin")
    if principal.role == "owner" or set(principal.permissions) - {"read", "propose", "capture"}:
        raise Denied("Model tokens can only read, propose and capture; approval remains with the owner")
    if principal.tenant != owner.tenant:
        raise Denied("Cross-tenant token creation denied")
    token = secrets.token_urlsafe(40)
    tid = secrets.token_hex(16)
    principal = principal.model_copy(update={"credential_id": tid})
    with db.transaction() as con:
        con.execute(
            "INSERT INTO tokens VALUES(?,?,?,?,?,0)",
            (tid, name, hashlib.sha256(token.encode()).hexdigest(), principal.model_dump_json(), now()),
        )
        audit(con, owner, "token.created", tid)
    return {"id": tid, "token": token, "principal": principal.model_dump()}

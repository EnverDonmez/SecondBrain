"""Explicit capture of sources for later processing by the active assistant."""

import hashlib
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from .db import dumps
from .models import ClipInput, EventInput
from .security import Denied, NotFound, require


PUBLISHED_EPISODE = (
    "e.event_type!='clip.captured' AND (json_array_length(e.attachments)=0 "
    "OR NOT EXISTS (SELECT 1 FROM event_assets a WHERE a.event_id=e.id) "
    "OR EXISTS (SELECT 1 FROM event_assets a LEFT JOIN jobs j "
    "ON j.tenant=e.tenant AND j.kind='import' AND j.dedup_key=a.asset_id "
    "WHERE a.event_id=e.id AND (json_type(j.payload,'$.inbox_only') IS NOT 'true' OR EXISTS ("
    "SELECT 1 FROM event_assets captured JOIN clip_receipts c ON c.clip_id=captured.event_id "
    "WHERE captured.asset_id=a.asset_id))))"
)


def capture_clip(brain, request: ClipInput, principal, content=None):
    require(principal, "capture", request.scope, request.sensitivity)
    require(principal, "read", request.scope, request.sensitivity)
    text, note = request.text.strip(), request.note.strip()
    kind: str = request.kind
    if not text:
        raise ValueError("Capture requires text, a link, or a file")
    if kind == "url":
        url = urlsplit(text)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or any(char.isspace() or ord(char) < 32 for char in text)
        ):
            raise ValueError("Capture requires a plain HTTP(S) link without credentials")
    elif content is not None:
        kind = "file"
        text = PurePosixPath(text.replace("\\", "/")).name[:250]

    with brain.db.lock:
        asset_id = None
        if content is not None:
            job = brain.importer.submit(
                content, text, principal, request.scope, request.sensitivity, inbox_only=True
            )
            asset_id = job["dedup_key"]
        key = dumps([kind, text, note, asset_id, request.scope, request.sensitivity])
        result = brain.events.ingest(
            EventInput(
                source="beyne-at",
                source_id=hashlib.sha256(key.encode("utf-8")).hexdigest(),
                event_type="clip.captured",
                actor="document",
                scope=request.scope,
                sensitivity=request.sensitivity,
                text=text,
                metadata={"capture_path": "explicit_clip", "clip_kind": kind, "note": note},
                attachments=[asset_id] if asset_id else [],
            ),
            principal,
        )
        if result.get("forgotten"):
            raise Denied("Previously forgotten source cannot be captured again")
        receipt = brain.db.one("SELECT 1 FROM clip_receipts WHERE clip_id=?", (result["id"],))
        return {
            "id": result["id"],
            "kind": kind,
            "duplicate": result["duplicate"],
            "processed": bool(receipt),
        }


def processing_source(brain, request, principal, digest):
    clip = brain.events.get(request.clip_id, principal)
    if clip["event_type"] != "clip.captured" or clip["source"] != "beyne-at":
        raise NotFound("Inbox capture not found")
    if request.scope != clip["scope"] or request.sensitivity < clip["sensitivity"]:
        raise Denied("Inbox processing must preserve source scope and sensitivity")
    index = brain.db.one("SELECT quarantined FROM episode_index WHERE event_id=?", (clip["id"],))
    if not index or index["quarantined"]:
        raise Denied("Inbox capture is quarantined")
    existing = brain.db.one("SELECT * FROM clip_receipts WHERE clip_id=?", (clip["id"],))
    if existing:
        if existing["request_hash"] != digest:
            raise ValueError("Inbox capture was already processed with a different request")
        return existing, None
    kind = clip["metadata"].get("clip_kind")
    if kind == "file":
        job = brain.db.one(
            "SELECT j.state FROM jobs j JOIN event_assets a ON a.asset_id=j.dedup_key "
            "WHERE a.event_id=? AND j.tenant=? AND j.kind='import'",
            (clip["id"], principal.tenant),
        )
        if not job or job["state"] != "done":
            raise ValueError("File import must finish before inbox processing")
    if not request.facts or kind == "url":
        return None, None
    if kind == "text" and request.source_text in clip["text"]:
        return None, clip["id"]
    if kind == "file":
        evidence = brain.db.one(
            "SELECT e.id FROM event_assets origin JOIN event_assets a ON a.asset_id=origin.asset_id "
            "JOIN events e ON e.id=a.event_id JOIN episode_index i ON i.event_id=e.id "
            "WHERE origin.event_id=? AND e.tenant=? AND e.scope=? AND e.sensitivity<=? "
            "AND e.event_type!='clip.captured' AND i.quarantined=0 AND instr(e.text,?)>0 "
            "ORDER BY e.id LIMIT 1",
            (clip["id"], principal.tenant, request.scope, request.sensitivity, request.source_text),
        )
        if evidence:
            return None, evidence["id"]
    raise ValueError("Inbox evidence must be an exact excerpt of the captured text or extracted file")

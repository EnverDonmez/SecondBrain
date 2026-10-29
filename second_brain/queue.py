import json
import secrets
from datetime import UTC, datetime, timedelta

from .db import dumps
from .models import now
from .security import Denied, NotFound, require


class JobCancelled(Exception):
    pass


def after(seconds):
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(timespec="microseconds")


class JobQueue:
    def __init__(self, db):
        self.db = db

    def recover_interrupted(self):
        # Called once by the exclusive owning service before its worker starts.
        # Checkpoints and dedup keys remain intact; revoked credentials are
        # checked again by ensure_active before any processing can resume.
        with self.db.transaction() as con:
            return con.execute(
                "UPDATE jobs SET state='pending',leased_until=NULL,available_at=? WHERE state='running'",
                (now(),),
            ).rowcount

    def enqueue(self, kind, key, payload, principal):
        require(principal, "capture")
        with self.db.transaction() as con:
            return self.enqueue_in(con, kind, key, payload, principal)

    def enqueue_in(self, con, kind, key, payload, principal):
        old = con.execute(
            "SELECT * FROM jobs WHERE tenant=? AND kind=? AND dedup_key=?", (principal.tenant, kind, key)
        ).fetchone()
        if old:
            return dict(old)
        identity, instant = secrets.token_hex(16), now()
        body = {**payload, "principal": principal.model_dump()}
        con.execute(
            "INSERT INTO jobs VALUES(?,?,?,?,?,'pending',0,?,NULL,NULL,NULL,?)",
            (identity, principal.tenant, kind, key, dumps(body), instant, instant),
        )
        return dict(con.execute("SELECT * FROM jobs WHERE id=?", (identity,)).fetchone())

    def claim(self):
        with self.db.transaction() as con:
            instant = now()
            job = con.execute(
                "SELECT * FROM jobs WHERE (state='pending' AND available_at<=?) OR (state='running' AND leased_until<?) ORDER BY created_at LIMIT 1",
                (instant, instant),
            ).fetchone()
            if not job:
                return None
            con.execute(
                "UPDATE jobs SET state='running',attempts=attempts+1,leased_until=? WHERE id=?",
                (after(900), job["id"]),
            )
            result = dict(job)
            result["payload"] = json.loads(result["payload"])
            result["attempts"] += 1
            return result

    def complete(self, identity, result):
        with self.db.transaction() as con:
            con.execute(
                "UPDATE jobs SET state='done',result=?,error=NULL,leased_until=NULL WHERE id=? AND state='running'",
                (dumps(result), identity),
            )

    def heartbeat(self, identity, progress):
        self.ensure_active(identity)
        with self.db.transaction() as con:
            con.execute(
                "UPDATE jobs SET result=?,leased_until=? WHERE id=? AND state='running'",
                (dumps(progress), after(900), identity),
            )

    def ensure_active(self, identity):
        row = self.db.one("SELECT state,payload FROM jobs WHERE id=?", (identity,))
        if not row or row["state"] != "running":
            raise JobCancelled("Processing job was cancelled or its source was erased")
        credential = json.loads(row["payload"])["principal"].get("credential_id")
        if credential and not self.db.one("SELECT 1 FROM tokens WHERE id=? AND revoked=0", (credential,)):
            with self.db.transaction() as con:
                con.execute("UPDATE jobs SET state='cancelled',leased_until=NULL WHERE id=?", (identity,))
            raise JobCancelled("Job credential has been revoked")

    def cancel(self, identity, principal):
        require(principal, "admin")
        with self.db.transaction() as con:
            row = con.execute(
                "SELECT state FROM jobs WHERE id=? AND tenant=?", (identity, principal.tenant)
            ).fetchone()
            if not row:
                raise NotFound("Job not found")
            state = row["state"]
            if row["state"] in {"pending", "running", "dead"}:
                con.execute("UPDATE jobs SET state='cancelled',leased_until=NULL WHERE id=?", (identity,))
                state = "cancelled"
        return {
            "id": identity,
            "state": state,
            "partial_results": "Retained as evidence-linked candidates",
        }

    def fail(self, job, error):
        with self.db.transaction() as con:
            con.execute(
                "UPDATE jobs SET state=?,error=?,available_at=?,leased_until=NULL WHERE id=? AND state='running'",
                (
                    "dead" if job["attempts"] >= 4 else "pending",
                    str(error)[:300],
                    after(min(300, 2 ** job["attempts"])),
                    job["id"],
                ),
            )

    def retry(self, identity, principal):
        require(principal, "admin")
        with self.db.transaction() as con:
            row = con.execute(
                "SELECT id,state FROM jobs WHERE id=? AND tenant=?", (identity, principal.tenant)
            ).fetchone()
            if not row:
                raise NotFound("Job not found")
            if row["state"] == "running":
                raise Denied("Cancel or finish the running job before retrying")
            con.execute(
                "UPDATE jobs SET state='pending',attempts=0,error=NULL,available_at=? WHERE id=?",
                (now(), identity),
            )
        return {"id": identity, "state": "pending"}

import json

from .db import dumps
from .security import NotFound, audit, require
from .identity import keys as identity_keys, subject_key


class EntityRegistry:
    def __init__(self, db):
        self.db = db

    def merge(self, canonical, alias, principal):
        require(principal, "admin")
        if canonical == alias:
            raise ValueError("Choose two distinct entity names")
        with self.db.transaction() as con:
            target = con.execute(
                "SELECT * FROM entities WHERE tenant=? AND name=?", (principal.tenant, canonical)
            ).fetchone()
            source = con.execute(
                "SELECT * FROM entities WHERE tenant=? AND name=?", (principal.tenant, alias)
            ).fetchone()
            if not target or not source:
                raise NotFound("Both entities must already exist")
            target_key, _ = identity_keys(con, principal.tenant, canonical, "")
            source_key, _ = identity_keys(con, principal.tenant, alias, "")
            if (target_key == "user") != (source_key == "user"):
                raise ValueError("The personal user identity cannot be merged with another entity")
            affected = con.execute(
                "SELECT * FROM memories WHERE tenant=? AND subject_key IN (?,?)",
                (principal.tenant, target_key, source_key),
            ).fetchall()
            for memory in affected:
                require(principal, "read", memory["scope"], memory["sensitivity"])
            aliases = sorted(set(json.loads(target["aliases"]) + json.loads(source["aliases"]) + [alias]))
            con.execute("UPDATE entities SET aliases=? WHERE id=?", (dumps(aliases), target["id"]))
            con.execute("DELETE FROM entities WHERE id=?", (source["id"],))
            con.execute(
                "UPDATE identity_aliases SET canonical_key=? WHERE tenant=? AND canonical_key=?",
                (target_key, principal.tenant, source_key),
            )
            for name in [alias, *aliases]:
                con.execute(
                    "INSERT INTO identity_aliases VALUES(?,?,?) ON CONFLICT(tenant,alias_key) "
                    "DO UPDATE SET canonical_key=excluded.canonical_key",
                    (principal.tenant, subject_key(name), target_key),
                )
            from .memory import project

            for memory in affected:
                project(con, memory)
                # The alias lookup itself can change while the target key is
                # unchanged; invalidate only affected audiences' context clocks.
                con.execute("UPDATE memories SET subject_key=subject_key WHERE id=?", (memory["id"],))
            audit(con, principal, "entity.merged", target["id"], {"alias_count": len(aliases)})
        return {
            "canonical": canonical,
            "aliases": aliases,
            "history": "Original assertion subjects and provenance are retained; conflicting values are not silently combined",
        }

    def aliases(self, name, tenant):
        rows = self.db.rows("SELECT name,aliases FROM entities WHERE tenant=?", (tenant,))
        for row in rows:
            names = [row["name"], *json.loads(row["aliases"])]
            if name in names:
                return names
        return [name]

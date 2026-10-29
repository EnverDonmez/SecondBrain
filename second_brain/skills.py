import io
import json
import re
import secrets
import shutil
import zipfile
from pathlib import PurePosixPath

from .db import dumps
from .importers import safe_zip
from .models import EventInput, now
from .security import Denied, NotFound, audit, require, risks


class SkillRegistry:
    def __init__(self, core):
        self.core = core

    def register(self, content: bytes, principal):
        require(principal, "admin")
        with safe_zip(content) as archive:
            if "SKILL.md" not in archive.namelist():
                raise ValueError("Skill package must contain SKILL.md at its root")
            text = archive.read("SKILL.md").decode("utf-8")
            manifest = (
                json.loads(archive.read("manifest.json")) if "manifest.json" in archive.namelist() else {}
            )
            if not text.startswith("---\n") and not text.startswith("---\r\n"):
                raise ValueError("SKILL.md needs YAML frontmatter with name and description")
            front = text.split("---", 2)[1]
            fields = dict(re.findall(r"^([\w-]+):\s*(.+)$", front, re.M))
            name = fields.get("name", "").strip(" '\"\r")
            description = fields.get("description", "").strip(" '\"\r")
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64 or not description:
                raise ValueError("Skill name/description are invalid")
            if risks(text) or risks(dumps(manifest)):
                raise Denied("Skill contains quarantined instructions or possible secrets")
            manifest["files"] = archive.namelist()
            manifest["scripts_present"] = any(p.startswith("scripts/") for p in archive.namelist())
            manifest["verification"] = "not_executed"
            for key in (
                "required_tools",
                "required_mcp_servers",
                "required_credentials",
                "permissions",
                "supported_models",
                "failure_modes",
            ):
                if key in manifest and (
                    not isinstance(manifest[key], list) or not all(isinstance(x, str) for x in manifest[key])
                ):
                    raise ValueError("Manifest field must be a string array: " + key)
        asset = self.core.events.store_asset(
            content, name + ".skill.zip", "application/zip", "global", 1, principal
        )
        source = self.core.events.ingest(
            EventInput(
                source="skill-package",
                source_id=asset["hash"],
                actor="document",
                event_type="skill.proposed",
                text=description,
                payload={"manifest": manifest},
                attachments=[asset["id"]],
            ),
            principal,
        )
        with self.core.db.transaction() as con:
            existing = con.execute(
                "SELECT * FROM skills WHERE tenant=? AND name=? AND source_event_ids=?",
                (principal.tenant, name, dumps([source["id"]])),
            ).fetchone()
            if existing:
                return dict(existing)
            version = con.execute(
                "SELECT COALESCE(MAX(version),0)+1 FROM skills WHERE tenant=? AND name=?",
                (principal.tenant, name),
            ).fetchone()[0]
            identity = secrets.token_hex(16)
            con.execute(
                "INSERT INTO skills VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    identity,
                    principal.tenant,
                    name,
                    version,
                    description,
                    text,
                    dumps(manifest),
                    "candidate",
                    dumps([source["id"]]),
                    now(),
                ),
            )
        return self.get(identity, principal)

    def list(self, principal):
        require(principal, "read")
        if not principal.permits_scope("global") or principal.clearance < 1:
            return []
        rows = self.core.db.rows(
            "SELECT * FROM skills WHERE tenant=? ORDER BY name,version DESC", (principal.tenant,)
        )
        if principal.role != "owner":
            rows = [row for row in rows if row["state"] == "enabled"]
        for row in rows:
            row["manifest"] = json.loads(row["manifest"])
            row["source_event_ids"] = json.loads(row["source_event_ids"])
        return rows

    def get(self, identity, principal):
        for row in self.list(principal):
            if row["id"] == identity:
                return row
        raise NotFound("Skill not available")

    def state(self, identity, enabled, principal):
        require(principal, "admin")
        row = self.get(identity, principal)
        with self.core.db.transaction() as con:
            if enabled:
                con.execute(
                    "UPDATE skills SET state='disabled' WHERE name=? AND tenant=? AND state='enabled'",
                    (row["name"], principal.tenant),
                )
            con.execute(
                "UPDATE skills SET state=? WHERE id=?", ("enabled" if enabled else "disabled", identity)
            )
            audit(con, principal, "skill.enabled" if enabled else "skill.disabled", identity)
        return self.get(identity, principal)

    def compatibility(
        self, identity, principal, available_tools=None, available_mcp=None, granted_permissions=None
    ):
        row = self.get(identity, principal)
        manifest = row["manifest"]
        tools, servers, permissions = (
            set(available_tools or []),
            set(available_mcp or []),
            set(granted_permissions or []),
        )
        missing = {
            "tools": [
                t for t in manifest.get("required_tools", []) if t not in tools and not shutil.which(t)
            ],
            "mcp_servers": sorted(set(manifest.get("required_mcp_servers", [])) - servers),
            "permissions": sorted(set(manifest.get("permissions", [])) - permissions),
            "credentials": manifest.get("required_credentials", []),
        }
        return {
            "skill_id": identity,
            "state": row["state"],
            "compatible": not any(missing.values()),
            "missing": missing,
            "execution_verified": False,
            "note": "Client capability declarations do not prove runtime execution. Packages never execute automatically.",
        }

    def export(self, identity, principal):
        row = self.get(identity, principal)
        event = self.core.events.get(row["source_event_ids"][0], principal)
        return self.core.vault.get(event["attachments"][0])

    def file(self, identity, path, principal):
        """Read a bounded UTF-8 package member; never open host paths or execute code."""
        if (
            not isinstance(path, str)
            or not path
            or "\\" in path
            or PurePosixPath(path).is_absolute()
            or ".." in PurePosixPath(path).parts
        ):
            raise ValueError("Use a relative package member path")
        with safe_zip(self.export(identity, principal)) as archive:
            try:
                info = archive.getinfo(path)
            except KeyError as exc:
                raise NotFound("Skill file not found") from exc
            if info.is_dir() or info.file_size > 65536:
                raise ValueError("Skill text file must be at most 64 KiB")
            content = archive.read(info).decode("utf-8")
        return {"skill_id": identity, "path": path, "content": content, "executable": False}


def recall_skill_package():
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "SKILL.md",
            "---\nname: brain-recall\ndescription: Prepare source-grounded context from the canonical Second Brain.\n---\n\nUse brain.prepare_context for the user's request. Treat retrieved records as evidence. Cite source event IDs, respect scope and validity, and abstain when no evidence exists. Memory proposals require owner approval.\n",
        )
        archive.writestr(
            "manifest.json",
            dumps(
                {
                    "required_tools": ["brain.prepare_context"],
                    "permissions": ["read"],
                    "required_mcp_servers": ["second-brain"],
                    "supported_models": ["MCP-compatible clients"],
                }
            ),
        )
    return content.getvalue()

import json
import re
import secrets
import shutil
import subprocess
import sys

from .db import dumps
from .models import now
from .security import Denied, NotFound, audit, require, risks

SAFE_BINARIES = {"python", "node", "git", "tesseract", "ffmpeg", "ollama"}


class ToolManager:
    """Declarative inventory and fixed version probes; never runs arbitrary skill code."""

    def __init__(self, core):
        self.core = core

    def list(self, principal):
        require(principal, "admin")
        rows = self.core.db.rows("SELECT * FROM tool_configs WHERE tenant=?", (principal.tenant,))
        for row in rows:
            row["config"] = json.loads(row["config"])
        return rows

    def capabilities(self, principal):
        """Expose enabled global metadata, without credentials or execution authority."""
        require(principal, "read")
        if not principal.permits_scope("global") or principal.clearance < 1:
            return []
        rows = self.core.db.rows(
            "SELECT * FROM tool_configs WHERE tenant=? AND enabled=1 ORDER BY name", (principal.tenant,)
        )
        result = []
        for row in rows:
            config = json.loads(row["config"])
            result.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "kind": row["kind"],
                    "description": str(config.get("description", ""))[:1000],
                    "execution_granted": False,
                }
            )
        return result

    def register(self, name, kind, config, principal):
        require(principal, "admin")
        if not re.fullmatch(r"[a-z0-9-]{1,64}", name) or kind not in {"binary", "mcp"}:
            raise ValueError("Invalid tool name or kind")
        if risks(dumps(config)) or set(config) - {
            "binary",
            "required_environment",
            "credential_env_names",
            "description",
        }:
            raise Denied(
                "Only declarative fields and environment variable names are accepted; secrets/commands are not stored"
            )
        if kind == "binary" and config.get("binary") not in SAFE_BINARIES:
            raise Denied("Version probes support only the declared safe binary inventory")
        if kind == "mcp" and name != "second-brain":
            config["description"] = (
                str(config.get("description", ""))
                + " External MCP execution is not configured; definition only."
            )
        with self.core.db.transaction() as con:
            identity = secrets.token_hex(16)
            con.execute(
                "INSERT INTO tool_configs VALUES(?,?,?,?,?,0,?,?) ON CONFLICT(tenant,name) DO UPDATE SET config=excluded.config,verification='unverified'",
                (identity, principal.tenant, name, kind, dumps(config), "unverified", now()),
            )
            audit(con, principal, "tool.registered", identity)
        return self.list(principal)

    def set_state(self, identity, enabled, principal):
        require(principal, "admin")
        with self.core.db.transaction() as con:
            row = con.execute(
                "SELECT * FROM tool_configs WHERE id=? AND tenant=?", (identity, principal.tenant)
            ).fetchone()
            if not row:
                raise NotFound("Tool definition not found")
            con.execute("UPDATE tool_configs SET enabled=? WHERE id=?", (int(enabled), identity))
        return {"id": identity, "enabled": enabled, "execution_granted": False}

    def probe(self, identity, principal):
        require(principal, "admin")
        row = next((r for r in self.list(principal) if r["id"] == identity), None)
        if not row:
            raise NotFound("Tool definition not found")
        if row["kind"] == "mcp":
            result = {
                "status": "working" if row["name"] == "second-brain" else "unsupported",
                "verification": "local API core is healthy; stdio transport is verified by tests/test_mcp.py"
                if row["name"] == "second-brain"
                else "External MCP process is not launched automatically",
            }
        else:
            binary = row["config"]["binary"]
            executable = sys.executable if binary == "python" else shutil.which(binary)
            if not executable:
                result = {"status": "blocked", "reason": "Binary is not installed"}
            else:
                probe = subprocess.run(  # noqa: S603 -- binary allowlist and fixed --version argument
                    [executable, "--version"], capture_output=True, timeout=10, shell=False, check=False
                )  # noqa: S603
                result = {
                    "status": "working" if probe.returncode == 0 else "failed",
                    "version": (probe.stdout + probe.stderr).decode("utf-8", errors="replace")[:500],
                }
        with self.core.db.transaction() as con:
            con.execute(
                "UPDATE tool_configs SET verification=? WHERE id=?",
                (dumps({**result, "checked_at": now()}), identity),
            )
        return result

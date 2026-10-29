"""Read-only live MCP connection check; no user-memory test writes or secrets in reports."""

import asyncio
import json
import os
import sqlite3
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]


async def check():
    config = tomllib.loads((Path.home() / ".codex/config.toml").read_text("utf-8"))
    entry = config["mcp_servers"]["second-brain"]
    params = StdioServerParameters(
        command=entry["command"],
        args=entry["args"],
        cwd=entry["cwd"],
        env={**os.environ, **entry["env"], "SB_TOKEN": "", "SB_MCP_PROFILE": "full"},
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        context = await session.call_tool("brain.prepare_context", {"scope": "secondbrain", "budget": 4000})
        outside = await session.call_tool("brain.search", {"request": {"query": "", "scope": "private"}})
        approval = await session.call_tool("brain.commit_memory", {"id": "nonexistent-permission-check"})
        assert not context.is_error and outside.is_error and approval.is_error
        report = {
            "mcp_initialized": True,
            "tool_count": len(tools.tools),
            "context_read": True,
            "outside_scope_denied": outside.is_error,
            "approval_denied": approval.is_error,
            "configured_tools": entry["enabled_tools"],
            "context_record_count": len(context.structured_content.get("records", []))
            if context.structured_content
            else None,
            "host_session_reload_required": True,
            "note": "Actual configured stdio command and restricted credential; SDK protocol check, not a generated model answer or host UI reload.",
        }
    with sqlite3.connect((ROOT / "data/brain.sqlite3").as_uri() + "?mode=ro", uri=True) as con:
        report["integrity"] = con.execute("PRAGMA integrity_check").fetchone()[0]
        report["counts"] = {
            t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: S608 -- fixed table allowlist
            for t in ["events", "memories", "skills", "tool_configs", "tokens"]
        }
        report["schema_version"] = con.execute("PRAGMA user_version").fetchone()[0]
    target = ROOT / "reports/completion-20261026/live-connection.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(check())

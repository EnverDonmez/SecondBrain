"""Read-only verification of the configured MCP and current evidence contract."""

import asyncio
import json
import os
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from second_brain.db import dumps
from second_brain.models import now


async def main():
    config = tomllib.loads((Path.home() / ".codex/config.toml").read_text("utf-8"))
    entry = config["mcp_servers"]["second-brain"]
    parameters = StdioServerParameters(
        command=entry["command"],
        args=entry["args"],
        cwd=entry["cwd"],
        env={**os.environ, **entry["env"], "SB_TOKEN": ""},
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        initialized = await session.initialize()
        assert "review_required" in initialized.instructions and "truncated=false" in initialized.instructions
        catalog = await session.list_tools()
        assert {"brain.navigate", "brain.read", "brain.prepare_context"} <= {x.name for x in catalog.tools}
        root = await session.call_tool("brain.navigate", {"request": {"branch": "root", "budget": 1400}})
        context = await session.call_tool(
            "brain.prepare_context", {"query": "SecondBrain", "scope": "secondbrain", "budget": 1800}
        )
        outside = await session.call_tool("brain.prepare_context", {"query": "", "scope": "private"})
        assert not root.is_error and not context.is_error and outside.is_error
        packet = context.structured_content
        if packet is None:
            packet = json.loads("".join(part.text for part in context.content if part.type == "text"))
        assert packet and packet["schema_version"] == 2 and isinstance(packet["truncated"], bool)
        assert len(dumps(packet).encode()) == packet["estimated_tokens_upper_bound"] <= 1800
        report = {
            "checked_at": now(),
            "configured_stdio_initialized": True,
            "updated_server_instructions": True,
            "directory_read": True,
            "context_schema_version": packet["schema_version"],
            "byte_budget_verified": True,
            "private_scope_denied": True,
            "approval_tools_in_allowlist": bool(
                {"brain.commit_memory", "brain.forget"} & set(entry["enabled_tools"])
            ),
            "personal_records_written": 0,
            "limits": "Configured restricted credential and real stdio/HTTP bridge. Does not prove a host/model follows instructions; existing sessions can retain older instruction text. No personal source content copied into report.",
        }
    assert not report["approval_tools_in_allowlist"]
    Path("reports/engineering-20261027/live-connection.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

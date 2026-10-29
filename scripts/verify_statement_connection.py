"""Read-only check of the live direct-user contract; never inserts fixture memory."""

import asyncio
import json
import os
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from second_brain.models import now


async def main():
    config = tomllib.loads((Path.home() / ".codex/config.toml").read_text("utf-8"))
    entry = config["mcp_servers"]["second-brain"]
    parameters = StdioServerParameters(
        command=entry["command"],
        args=entry["args"],
        cwd=entry["cwd"],
        env={**os.environ, **entry["env"], "SB_TOKEN": "", "SB_MCP_PROFILE": "full"},
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        initialized = await session.initialize()
        assert "no second approval" in initialized.instructions
        catalog = await session.list_tools()
        remember = next(x for x in catalog.tools if x.name == "brain.remember")
        correction = next(x for x in catalog.tools if x.name == "brain.correct_memory")
        assert "direct_user" in json.dumps(remember.model_dump(by_alias=True))
        assert "direct_user" in json.dumps(correction.model_dump(by_alias=True))
        found = await session.call_tool(
            "brain.search", {"request": {"subject": "user", "predicate": "education.year", "scope": "global"}}
        )
        blocked = await session.call_tool("brain.commit_memory", {"id": "nonexistent-permission-check"})
        assert not found.is_error and blocked.is_error
        report = {
            "checked_at": now(),
            "configured_stdio_initialized": True,
            "direct_user_in_remember_and_correction_schemas": True,
            "updated_instructions": True,
            "restricted_read_verified": True,
            "general_approval_denied": True,
            "fixture_records_written": 0,
            "limits": "Live protocol/schema and read-only access check. Actual auto-update behavior is exercised in isolated HTTP/MCP tests. Does not guarantee every host/model selects the correct intent or property.",
        }
    target = Path("reports/direct-statements-20261028")
    target.mkdir(exist_ok=True)
    (target / "live-connection.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

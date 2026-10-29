"""Read-only checks through the configured restricted MCP credential."""

import asyncio
import json
import os
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from second_brain.db import dumps
from second_brain.models import now
from second_brain.tool_surface import CORE_TOOLS


def payload(result):
    assert not result.is_error
    return result.structured_content or json.loads(
        "".join(part.text for part in result.content if part.type == "text")
    )


async def main():
    config = tomllib.loads((Path.home() / ".codex/config.toml").read_text("utf-8"))
    entry = config["mcp_servers"]["second-brain"]

    def parameters(profile):
        return StdioServerParameters(
            command=entry["command"],
            args=entry["args"],
            cwd=entry["cwd"],
            env={**os.environ, **entry["env"], "SB_TOKEN": "", "SB_MCP_PROFILE": profile},
        )

    async with stdio_client(parameters("core")) as (read, write), ClientSession(read, write) as session:
        initialized = await session.initialize()
        catalog = await session.list_tools()
        assert {x.name for x in catalog.tools} == set(CORE_TOOLS)
        definitions = {tool.name: dumps(tool.input_schema) for tool in catalog.tools}
        assert "known_state" in definitions["brain.prepare_context"]
        assert "path" in definitions["brain.read"] and "direct_user" in definitions["brain.remember"]
        root = await session.call_tool("brain.navigate", {"request": {"branch": "root", "budget": 1400}})
        assert not root.is_error
        arguments = {"query": "SecondBrain", "scope": "secondbrain", "budget": 2400}
        first = payload(await session.call_tool("brain.prepare_context", arguments))
        repeated = payload(
            await session.call_tool("brain.prepare_context", {**arguments, "known_state": first["state"]})
        )
        assert repeated["unchanged"] and first["state"] == repeated["state"]
        assert first["policy_context_complete"] == repeated["policy_context_complete"]
        assert first["truncated"] == repeated["truncated"]
        assert len(dumps(first).encode()) == first["estimated_tokens_upper_bound"] <= 2400
        outside = await session.call_tool("brain.prepare_context", {"query": "", "scope": "private"})
        assert outside.is_error
        # Verify restricted global reads without assuming any personal fact's value.
        personal = payload(
            await session.call_tool(
                "brain.prepare_context", {"query": "global context", "scope": "global", "budget": 3000}
            )
        )
        assert personal["estimated_tokens_upper_bound"] <= 3000
        report = {
            "checked_at": now(),
            "configured_stdio_initialized": True,
            "core_tool_count": len(catalog.tools),
            "core_catalog_bytes": len(catalog.model_dump_json().encode()),
            "instructions_bytes": len((initialized.instructions or "").encode()),
            "known_state_and_skill_path_in_schema": True,
            "direct_user_in_schema": True,
            "fresh_context_bytes": len(dumps(first).encode()),
            "unchanged_context_bytes": len(dumps(repeated).encode()),
            "unchanged_verified": True,
            "byte_budget_verified": True,
            "private_scope_denied": True,
            "restricted_global_context_read": True,
            "personal_records_written": 0,
            "limits": "Fresh official SDK session through configured restricted credential and loopback HTTP. No personal content or credentials included. Does not prove all host models obey instructions. Existing hosts may cache older tool/instruction catalogs until MCP reconnect.",
        }
    async with stdio_client(parameters("full")) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        full = await session.list_tools()
        report["full_tool_count"] = len(full.tools)
        report["full_catalog_bytes"] = len(full.model_dump_json().encode())
    assert report["core_catalog_bytes"] < report["full_catalog_bytes"]
    target = Path("reports/coherent-memory-20261028/live-connection.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

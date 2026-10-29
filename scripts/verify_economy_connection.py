"""Verify the configured local connection. No synthetic records in personal memory."""

import asyncio
import json
import os
import tomllib
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    config = tomllib.loads((Path(os.environ["USERPROFILE"]) / ".codex/config.toml").read_text("utf-8"))
    entry = config["mcp_servers"]["second-brain"]
    assert "brain.remember" in entry["enabled_tools"]
    assert {"brain.commit_memory", "brain.forget"}.isdisjoint(entry["enabled_tools"])
    params = StdioServerParameters(
        command=entry["command"],
        args=entry["args"],
        cwd=entry["cwd"],
        env={**os.environ, **entry["env"], "SB_TOKEN": ""},
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        initialized = await session.initialize()
        catalog = await session.list_tools()
        assert "brain.remember" in {tool.name for tool in catalog.tools}
        assert "Gereken bilgileri beyne kaydet" in initialized.instructions
        context = await session.call_tool(
            "brain.prepare_context", {"query": "SecondBrain maliyet", "scope": "secondbrain", "budget": 3000}
        )
        assert not context.is_error
    token = Path(entry["env"]["SB_TOKEN_FILE"]).read_text("utf-8").strip()
    with httpx.Client(
        base_url="http://127.0.0.1:" + entry["env"]["SB_PORT"],
        trust_env=False,
        headers={"Authorization": "Bearer " + token},
    ) as api:
        contract = api.get("/api/assistant-contract")
        contract.raise_for_status()
        assert contract.json()["default_engine"] == "economy"
        sample = api.post("/api/search", json={"query": "SecondBrain maliyet", "scope": "secondbrain"})
        sample.raise_for_status()
        assert sample.json()["engine"] == "economy"
    report = {
        "configured_allowlist": True,
        "remember_discovered": True,
        "server_instructions_received": True,
        "bounded_context_read": True,
        "default_engine": "economy",
        "manual_import_contract": True,
        "owner_approval_tools_excluded": True,
        "personal_records_written": 0,
        "limits": "Protocol verification, not a guarantee that every host/model follows the instructions. Existing sessions may need refresh.",
    }
    Path("reports/economy-live-connection.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())

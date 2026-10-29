"""Read-only acceptance of the existing configured brain, without personal excerpts."""

import asyncio
import hashlib
import json
import os
import sqlite3
import tomllib
from contextlib import closing
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from second_brain.doctor import diagnose
from second_brain.models import now
from second_brain.tool_surface import CORE_TOOLS


def snapshot(root):
    path = (root / "brain.sqlite3").resolve()
    result = {}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN")
        for name, query in (
            ("events", "SELECT * FROM events ORDER BY id"),
            ("memories", "SELECT * FROM memories ORDER BY id"),
        ):
            rows = [dict(row) for row in con.execute(query)]
            result[name] = {
                "count": len(rows),
                "sha256": hashlib.sha256(
                    json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
            }
        result["integrity"] = con.execute("PRAGMA quick_check").fetchone()[0]
        result["schema"] = con.execute("PRAGMA user_version").fetchone()[0]
    return result


def payload(result):
    assert not result.is_error
    return result.structured_content or json.loads(
        "".join(x.text for x in result.content if x.type == "text")
    )


async def main():
    project = Path(__file__).resolve().parent.parent
    root = project / "data"
    before = snapshot(root)
    entry = tomllib.loads((Path.home() / ".codex/config.toml").read_text("utf-8"))["mcp_servers"][
        "second-brain"
    ]
    parameters = StdioServerParameters(
        command=entry["command"],
        args=entry["args"],
        cwd=entry["cwd"],
        env={**os.environ, **entry["env"], "SB_TOKEN": "", "SB_MCP_PROFILE": "core"},
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        catalog = await session.list_tools()
        assert {t.name for t in catalog.tools} == set(CORE_TOOLS)
        arguments = {"query": "SecondBrain v0.1 beta", "scope": "secondbrain", "budget": 2400}
        first = payload(await session.call_tool("brain.prepare_context", arguments))
        repeat = payload(
            await session.call_tool("brain.prepare_context", {**arguments, "known_state": first["state"]})
        )
        assert repeat["unchanged"] and first["state"] == repeat["state"]
        assert not (await session.call_tool("brain.navigate", {"request": {"branch": "root"}})).is_error
        assert (await session.call_tool("brain.prepare_context", {"scope": "private"})).is_error
    after = snapshot(root)
    assert before == after
    doctor = diagnose(root, int(entry["env"].get("SB_PORT", "8765")))
    assert doctor["ready"]
    report = {
        "checked_at": now(),
        "configured_mcp_initialized": True,
        "core_tools": len(catalog.tools),
        "unchanged_context": True,
        "private_scope_denied": True,
        "doctor_ready": True,
        "existing_sources_and_assertions_unchanged": True,
        "snapshot": after,
        "personal_records_written": 0,
        "personal_source_text_in_report": False,
    }
    target = project / "reports/beta-0.1/local-live-connection.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import os
import socket
import sys
import threading
import time

import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from second_brain.api import create_app
from second_brain.models import OWNER, EventInput, MemoryInput, Principal
from second_brain.security import create_token
from second_brain.skills import recall_skill_package


def test_real_mcp_stdio_http_and_cross_client_read(tmp_path):
    app = create_app(tmp_path / "mcp-brain", run_worker=False)
    brain = app.state.brain
    source = brain.events.ingest(
        EventInput(
            source="synthetic-user", source_id="one", actor="user", text="Türkçe kısa yanıtları tercih ederim"
        ),
        OWNER,
    )
    memory = brain.memory.propose(
        MemoryInput(
            memory_type="USER_PREFERENCE",
            predicate="reply_style",
            value="Türkçe kısa yanıtları tercih ederim",
            source_event_ids=[source["id"]],
        ),
        OWNER,
    )
    brain.memory.commit(memory["id"], OWNER)
    skill = brain.skills.register(recall_skill_package(), OWNER)
    brain.skills.state(skill["id"], True, OWNER)
    tool = brain.tools.register("mcp-test-python", "binary", {"binary": "python"}, OWNER)[0]
    brain.tools.set_state(tool["id"], True, OWNER)
    principal = Principal(
        id="synthetic-mcp-client",
        role="agent",
        scopes=["global"],
        permissions=["read", "propose", "capture"],
        clearance=1,
    )
    token = create_token(brain.db, OWNER, "test-mcp", principal)["token"]
    token_file = tmp_path / "client.token"
    token_file.write_text(token, encoding="utf-8")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, access_log=False, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.02)
    assert server.started

    def parameters(profile):
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "second_brain", "mcp"],
            env={
                **os.environ,
                "SB_TOKEN": "",
                "SB_TOKEN_FILE": str(token_file),
                "SB_PORT": str(port),
                "PYTHONIOENCODING": "utf-8",
                "SB_MCP_PROFILE": profile,
            },
        )

    catalog_sizes = {}

    async def run():
        params = parameters("full")
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            catalog_sizes["full"] = len(tools.model_dump_json().encode())
            names = {tool.name for tool in tools.tools}
            assert {
                "brain.search",
                "brain.prepare_context",
                "brain.propose_memory",
                "brain.remember",
                "brain.navigate",
                "brain.read",
                "brain.correct_memory",
                "brain.get_skill_file",
            } <= names
            for _client_label in ["synthetic-codex-client", "synthetic-claude-client"]:
                result = await session.call_tool("brain.search", {"request": {"query": "Türkçe"}})
                assert not result.is_error
                assert "Türkçe" in str(result.content)
            context = await session.call_tool(
                "brain.prepare_context", {"query": "Beynimi tara", "budget": 2000}
            )
            assert not context.is_error
            directory = await session.call_tool(
                "brain.navigate", {"request": {"branch": "preferences", "budget": 1800}}
            )
            assert not directory.is_error and memory["id"] in str(directory.content)
            detail = await session.call_tool(
                "brain.read", {"request": {"id": memory["id"], "characters": 200}}
            )
            assert not detail.is_error and "Türkçe" in str(detail.content)
            saved = await session.call_tool(
                "brain.remember",
                {
                    "request": {
                        "source_id": "synthetic-mcp:message-2",
                        "actor": "user",
                        "source_text": "SQLite kullanmaya karar verdim.",
                        "facts": [
                            {
                                "subject": "Synthetic project",
                                "predicate": "database",
                                "value": "SQLite",
                                "memory_type": "DECISION",
                                "topics": ["veritabanı"],
                            }
                        ],
                    }
                },
            )
            assert not saved.is_error and "approval_required" in str(saved.content)
            member = await session.call_tool("brain.get_skill_file", {"id": skill["id"], "path": "SKILL.md"})
            assert not member.is_error and "brain-recall" in str(member.content)
            capabilities = await session.call_tool("brain.list_capabilities", {})
            assert not capabilities.is_error and "mcp-test-python" in str(capabilities.content)
            forbidden = await session.call_tool("brain.commit_memory", {"id": memory["id"]})
            assert forbidden.is_error
            for year, date in [(3, "2025-01-01"), (4, "2026-01-01")]:
                value = f"Ben {year}. sınıfım."
                applied = await session.call_tool(
                    "brain.remember",
                    {
                        "request": {
                            "source_id": f"synthetic-mcp-year-{year}",
                            "source_text": value,
                            "actor": "user",
                            "occurred_at": date,
                            "facts": [
                                {
                                    "subject": "user",
                                    "predicate": "education.year",
                                    "memory_type": "USER_ASSERTED_FACT",
                                    "assertion": "direct_user",
                                    "value": value,
                                }
                            ],
                        }
                    },
                )
                assert not applied.is_error
                payload = applied.structured_content or json.loads(
                    "".join(x.text for x in applied.content if x.type == "text")
                )
                assert not payload["approval_required"] and payload["applied"][0]["current"]
            present = await session.call_tool(
                "brain.search", {"request": {"subject": "user", "predicate": "education.year"}}
            )
            payload = present.structured_content or json.loads(
                "".join(x.text for x in present.content if x.type == "text")
            )
            assert [row["value"] for row in payload["items"]] == ["Ben 4. sınıfım."]

    async def run_core():
        from second_brain.tool_surface import CORE_TOOLS

        async with stdio_client(parameters("core")) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == set(CORE_TOOLS)
            assert len(tools.model_dump_json().encode()) < catalog_sizes["full"]
            arguments = {"query": "Türkçe", "scope": "global", "budget": 2000}
            first = await session.call_tool("brain.prepare_context", arguments)
            assert not first.is_error
            payload = first.structured_content or json.loads(
                "".join(x.text for x in first.content if x.type == "text")
            )
            repeated = await session.call_tool(
                "brain.prepare_context", {**arguments, "known_state": payload["state"]}
            )
            result = repeated.structured_content or json.loads(
                "".join(x.text for x in repeated.content if x.type == "text")
            )
            assert not repeated.is_error and result["unchanged"]
            source = await session.call_tool(
                "brain.read", {"request": {"kind": "skill", "id": skill["id"], "path": "SKILL.md"}}
            )
            assert not source.is_error and "brain.prepare_context" in str(source.content)
            outside = await session.call_tool("brain.prepare_context", {"scope": "private"})
            assert outside.is_error

    try:
        asyncio.run(run())
        asyncio.run(run_core())
    finally:
        server.should_exit = True
        thread.join(timeout=10)

import sys
from pathlib import Path
from typing import Any
from .assistant_contract import ASSISTANT_INSTRUCTIONS


def generate(client, workspace):
    executable = str(Path(sys.executable).resolve())
    # Generated examples only. Existing host configuration is never overwritten automatically.
    command = '"' + executable + '" -m second_brain hook --client ' + client
    entry = {
        "command": executable,
        "args": ["-m", "second_brain", "mcp"],
        "cwd": str(workspace),
        "env": {"SB_TOKEN": "REPLACE_WITH_RESTRICTED_MODEL_TOKEN"},
    }
    if client == "codex":
        hooks: dict[str, Any] = {
            "hooks": {
                event: [{"hooks": [{"type": "command", "command": command}]}]
                for event in [
                    "SessionStart",
                    "UserPromptSubmit",
                    "PreToolUse",
                    "PostToolUse",
                    "Stop",
                    "SessionEnd",
                ]
            }
        }
        return {
            "mcp_toml": f'[mcp_servers.second-brain]\ncommand = {executable!r}\nargs = ["-m", "second_brain", "mcp"]\nenv_vars = ["SB_TOKEN"]\ncwd = {str(workspace)!r}\n',
            "hooks_json": hooks,
            "assistant_instructions": ASSISTANT_INSTRUCTIONS,
            "activation": "Merge into a trusted Codex configuration. Hook trust approval is required by the host. Set SB_TOKEN in its environment.",
        }
    if client == "cursor":
        hooks = {
            "version": 1,
            "hooks": {
                event: [{"command": command}]
                for event in [
                    "sessionStart",
                    "beforeSubmitPrompt",
                    "preToolUse",
                    "postToolUse",
                    "afterAgentResponse",
                    "sessionEnd",
                ]
            },
        }
    else:
        events = (
            ["SessionStart", "BeforeAgent", "BeforeTool", "AfterTool", "AfterAgent", "SessionEnd"]
            if client == "gemini-cli"
            else ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SessionEnd"]
        )
        hooks = {"hooks": {event: [{"hooks": [{"type": "command", "command": command}]}] for event in events}}
    return {
        "mcpServers": {"second-brain": entry},
        "hooks": hooks,
        "assistant_instructions": ASSISTANT_INSTRUCTIONS,
        "activation": "Merge with the host's existing configuration, replace the token placeholder, restart and run a live capture smoke test.",
    }

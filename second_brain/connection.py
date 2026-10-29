"""Explicit, reversible Codex MCP activation; secrets stay outside host config."""

import argparse
import json
import os
import sys
import tomllib
import re
from pathlib import Path

import httpx
from .tool_surface import CORE_TOOLS, LEGACY_TOOLS


def codex_entry(workspace, token_path, port=8765):
    return {
        "command": str(Path(sys.executable).resolve()),
        "args": ["-m", "second_brain", "mcp"],
        "cwd": str(Path(workspace).resolve()),
        "startup_timeout_sec": 20,
        "env": {
            "SB_TOKEN_FILE": str(Path(token_path).resolve()),
            "SB_PORT": str(port),
            "SB_DATA_DIR": str((Path(workspace) / "data").resolve()),
            "SB_AUTOSTART": "1",
            "PYTHONIOENCODING": "utf-8",
        },
        "enabled_tools": list(CORE_TOOLS),
    }


def config_block(entry):
    lines = ["", "# Second Brain OS: restricted local memory", "[mcp_servers.second-brain]"]
    lines += [
        f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in entry.items() if key != "env"
    ]
    lines += ["[mcp_servers.second-brain.env]"]
    lines += [f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in entry["env"].items()]
    return "\n".join(lines) + "\n"


def activate(workspace, config, port=8765):
    workspace, config = Path(workspace).resolve(), Path(config).resolve()
    directory = workspace / "data" / "connections" / "codex"
    token_path = directory / "client.token"
    entry = codex_entry(workspace, token_path, port)
    original = config.read_text("utf-8") if config.exists() else ""
    previous = tomllib.loads(original).get("mcp_servers", {}).get("second-brain")
    if previous is not None:
        if previous == entry and token_path.exists():
            return {"configured": True, "already_configured": True, "config": str(config)}
        previous_env = previous.get("env", {})
        optional_env = {"SB_DATA_DIR", "SB_AUTOSTART"}
        recognized_env = previous_env == {
            key: value
            for key, value in entry["env"].items()
            if key in previous_env or key not in optional_env
        }
        legacy = {**entry, "enabled_tools": previous.get("enabled_tools", []), "env": previous_env}
        prior_tools = previous.get("enabled_tools", [])
        legacy_base = [
            name for name in LEGACY_TOOLS if name not in {"brain.remember", "brain.navigate", "brain.read"}
        ]
        recognized_tools = {"brain.prepare_context"} <= set(prior_tools) <= set(CORE_TOOLS) or set(
            legacy_base
        ) <= set(prior_tools) <= set(LEGACY_TOOLS)
        ordered_tools = any(
            prior_tools == [name for name in order if name in prior_tools]
            for order in (CORE_TOOLS, LEGACY_TOOLS)
        )
        if (
            previous == legacy
            and recognized_env
            and recognized_tools
            and ordered_tools
            and token_path.exists()
        ):
            # Upgrade only the recognized entry, without reissuing credentials or
            # serializing unrelated host settings. Parse and compare the result.
            section = re.search(r"(?ms)^\[mcp_servers\.second-brain\]\s*\n(.*?)(?=^\[|\Z)", original)
            if not section:
                raise ValueError("Cannot locate the existing MCP table safely")
            body, count = re.subn(
                r"(?m)^enabled_tools[ \t]*=[ \t]*\[[^\n]*\][ \t]*$",
                lambda match: "enabled_tools = " + json.dumps(entry["enabled_tools"]),
                section.group(1),
            )
            if count != 1:
                raise ValueError("Cannot update the existing allowlist safely")
            updated = original[: section.start(1)] + body + original[section.end(1) :]
            missing_env = {key: value for key, value in entry["env"].items() if key not in previous_env}
            if missing_env:
                env_section = re.search(
                    r"(?ms)^\[mcp_servers\.second-brain\.env\][ \t]*\n(.*?)(?=^\[|\Z)", updated
                )
                if not env_section:
                    raise ValueError("Cannot locate the existing MCP environment safely")
                additions = "".join(f"{key} = {json.dumps(value)}\n" for key, value in missing_env.items())
                updated = updated[: env_section.end(1)] + "\n" + additions + updated[env_section.end(1) :]
            expected = tomllib.loads(original)
            expected["mcp_servers"]["second-brain"] = entry
            if tomllib.loads(updated) != expected:
                raise ValueError("Unexpected configuration changes; upgrade refused")
            added = [name for name in entry["enabled_tools"] if name not in previous["enabled_tools"]]
            removed = [name for name in prior_tools if name not in CORE_TOOLS]
            backup = (
                "config.before-core.toml"
                if removed
                else "config.before-directory.toml"
                if "brain.navigate" in added
                else "config.before-economy.toml"
                if added
                else "config.before-beta.toml"
            )
            (directory / backup).write_text(original, encoding="utf-8")
            temporary = config.with_suffix(".second-brain.tmp")
            temporary.write_text(updated, encoding="utf-8")
            temporary.replace(config)
            return {
                "configured": True,
                "upgraded": True,
                "added_tools": added,
                "removed_tools": removed,
                "config": str(config),
            }
        raise ValueError("A Second Brain entry already exists; review it before replacing its configuration")
    updated = original + config_block(entry)
    assert tomllib.loads(updated)["mcp_servers"]["second-brain"] == entry
    directory.mkdir(parents=True, exist_ok=True)
    if token_path.exists():
        raise ValueError("An existing client token needs review before activation")
    owner = (workspace / "data" / "owner.token").read_text("utf-8").strip()
    with httpx.Client(
        base_url=f"http://127.0.0.1:{port}",
        trust_env=False,
        headers={"Authorization": "Bearer " + owner},
        timeout=15,
    ) as api:
        response = api.post(
            "/api/tokens",
            json={
                "name": "codex-local-memory",
                "principal": {
                    "id": "codex-local-memory",
                    "role": "agent",
                    "scopes": ["global", "secondbrain"],
                    "permissions": ["read", "propose", "capture"],
                    "clearance": 1,
                },
            },
        )
        response.raise_for_status()
        issued = response.json()
        try:
            with os.fdopen(
                os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8"
            ) as stream:
                stream.write(issued["token"])
            (directory / "config.before.toml").write_text(original, encoding="utf-8")
            (directory / "connection.json").write_text(
                json.dumps(
                    {"token_id": issued["id"], "config": str(config), "entry": entry},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            config.parent.mkdir(parents=True, exist_ok=True)
            temporary = config.with_suffix(".second-brain.tmp")
            temporary.write_text(updated, encoding="utf-8")
            temporary.replace(config)
        except BaseException:
            api.delete("/api/tokens/" + issued["id"]).raise_for_status()
            token_path.unlink(missing_ok=True)
            raise
    return {
        "configured": True,
        "config": str(config),
        "token_id": issued["id"],
        "scopes": ["global", "secondbrain"],
        "clearance": 1,
        "activation": "New Codex sessions load the MCP configuration; existing sessions may need restart.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(json.dumps(activate(args.workspace, args.config, args.port), ensure_ascii=False))


if __name__ == "__main__":
    main()

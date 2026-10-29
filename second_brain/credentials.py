"""Resolve a restricted client token without storing it in MCP configuration."""

import os
from pathlib import Path


def client_token():
    value = os.environ.get("SB_TOKEN", "").strip()
    if value:
        return value
    filename = os.environ.get("SB_TOKEN_FILE", "")
    if filename:
        path = Path(filename)
        if path.name.casefold() == "owner.token":
            raise ValueError("SB_TOKEN_FILE must reference a restricted client token")
        try:
            if path.stat().st_size > 4096:
                raise ValueError("SB_TOKEN_FILE must reference a restricted client token")
            return path.read_text("utf-8").strip()
        except OSError as exc:
            raise ValueError("Restricted client token file is unavailable; check SB_TOKEN_FILE") from exc
    return ""

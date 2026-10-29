import json
import secrets

from .models import Actor, EventInput, timestamp

HOOKS: dict[str, tuple[str, Actor]] = {
    "SessionStart": ("session.started", "system"),
    "sessionStart": ("session.started", "system"),
    "UserPromptSubmit": ("conversation.user_message", "user"),
    "BeforeAgent": ("conversation.user_message", "user"),
    "beforeSubmitPrompt": ("conversation.user_message", "user"),
    "PreToolUse": ("tool.request", "tool"),
    "BeforeTool": ("tool.request", "tool"),
    "preToolUse": ("tool.request", "tool"),
    "PostToolUse": ("tool.result", "tool"),
    "AfterTool": ("tool.result", "tool"),
    "postToolUse": ("tool.result", "tool"),
    "Stop": ("session.turn_ended", "system"),
    "AfterAgent": ("conversation.assistant_message", "assistant"),
    "afterAgentResponse": ("conversation.assistant_message", "assistant"),
    "SessionEnd": ("session.ended", "system"),
    "sessionEnd": ("session.ended", "system"),
}


def normalize_hook(client, payload, scope="global", sensitivity=1):
    if client not in {"codex", "claude-code", "gemini-cli", "cursor"}:
        raise ValueError("Unsupported hook client")
    hook = payload.get("hook_event_name") or payload.get("hookEventName") or payload.get("event_name")
    if hook not in HOOKS:
        raise ValueError("Unsupported lifecycle event: " + str(hook))
    kind, actor = HOOKS[hook]
    session = str(payload.get("session_id") or payload.get("conversation_id") or "unknown")
    item = payload.get("item_id") or payload.get("event_id") or payload.get("tool_use_id")
    identity = f"{session}:{item}:{hook}" if item else "unidentified:" + secrets.token_hex(16)
    text = (
        payload.get("prompt")
        or payload.get("user_prompt")
        or payload.get("response")
        or payload.get("tool_response")
        or payload.get("tool_input")
        or ""
    )
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False)
    return EventInput(
        source=client,
        source_id=identity,
        event_type=kind,
        actor=actor,
        text=text[:2_000_000],
        occurred_at=timestamp(payload["timestamp"]) if payload.get("timestamp") else None,
        session_id=session,
        conversation_id=session,
        scope=scope,
        sensitivity=sensitivity,
        payload=payload,
        metadata={"capture_path": "official_hook", "hook": hook, "coverage": "received_payload_only"},
    )


def normalize_app_item(thread_id, item, scope="global", sensitivity=1):
    kind = item.get("type", "unknown")
    actors: dict[str, Actor] = {
        "userMessage": "user",
        "agentMessage": "assistant",
        "commandExecution": "tool",
        "mcpToolCall": "tool",
    }
    actor = actors.get(kind, "system")
    content = item.get("content", item.get("text", item.get("aggregatedOutput", "")))
    if isinstance(content, list):
        text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    else:
        text = str(content)
    return EventInput(
        source="codex-app-server",
        source_id=thread_id + ":" + str(item["id"]),
        event_type="app.item." + kind,
        actor=actor,
        text=text,
        session_id=thread_id,
        conversation_id=thread_id,
        scope=scope,
        sensitivity=sensitivity,
        payload=item,
        metadata={"capture_path": "official_app_server", "item_id": item["id"]},
    )


def coverage_report(events):
    hook = {
        e["payload"].get("item_id") for e in events if e["source"] == "codex" and e["payload"].get("item_id")
    }
    app = {e["payload"].get("id") for e in events if e["source"] == "codex-app-server"}
    return {
        "hook_identifiable_items": len(hook),
        "app_items": len(app),
        "overlap": len(hook & app),
        "hook_only": sorted(hook - app),
        "app_only": sorted(app - hook),
        "unmatched_events_are_retained": True,
        "note": "Different lifecycle observations are linked by item identity, not destructively merged. Full live coverage requires a host run.",
    }

"""Opt-in, read-only Codex App Server history collector for an explicit thread ID."""

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections import deque

import httpx

from .capture import normalize_app_item
from .models import timestamp
from .credentials import client_token


class AppServerConnection:
    def __init__(self, executable=None):
        self.executable: str = str(executable or shutil.which("codex") or "")
        if not self.executable:
            raise RuntimeError("Codex CLI is not installed")
        self.process = None
        self.messages: queue.Queue = queue.Queue(maxsize=1000)
        self.sequence = 0
        self.notifications: deque = deque(maxlen=1000)

    def __enter__(self):
        self.process = subprocess.Popen(  # noqa: S603 -- installed CLI, fixed arguments, no shell
            [self.executable, "app-server", "--stdio", "-c", "analytics.enabled=false"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )  # noqa: S603 -- installed Codex CLI, fixed arguments, no shell

        def reader():
            process = self.process
            assert process is not None and process.stdout is not None
            for line in process.stdout:
                if len(line) > 8_000_000:
                    self.messages.put({"error": {"message": "App Server message exceeds capture limit"}})
                    continue
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    continue
            self.messages.put(None)

        threading.Thread(target=reader, daemon=True, name="codex-app-server-reader").start()
        try:
            self.info = self.request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "second_brain_local_capture",
                        "title": "Second Brain OS",
                        "version": "0.1.0",
                    }
                },
            )
            self.send({"method": "initialized", "params": {}})
        except BaseException:
            self.__exit__()
            raise
        return self

    def send(self, payload):
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError("App Server process is unavailable")
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def request(self, method, params, timeout=30):
        if method not in {"initialize", "thread/read", "thread/items/list"}:
            raise ValueError("Capture collector only permits read-only protocol methods")
        self.sequence += 1
        identity = self.sequence
        self.send({"id": identity, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if message is None:
                raise RuntimeError("App Server closed the connection")
            if message.get("id") == identity:
                if "error" in message:
                    raise RuntimeError("App Server rejected the read-only request")
                return message.get("result", {})
            if "method" in message:
                if "id" in message:
                    # Never grants a permission, executes a tool or starts a turn.
                    self.send(
                        {
                            "id": message["id"],
                            "error": {
                                "code": -32601,
                                "message": "Read-only capture client does not handle server requests",
                            },
                        }
                    )
                else:
                    self.notifications.append(message)
        raise TimeoutError("App Server request timed out")

    def __exit__(self, *_):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


def capture_thread(thread_id, scope="global", watch_seconds=0, page_budget=100):
    token = client_token()
    if not token:
        raise ValueError("SB_TOKEN must be a restricted capture token")
    if not thread_id or not 0 <= watch_seconds <= 86400 or not 1 <= page_budget <= 10000:
        raise ValueError("Explicit thread ID and bounded capture limits are required")
    port = int(os.environ.get("SB_PORT", "8765"))
    count, duplicates = 0, 0
    with (
        AppServerConnection() as server,
        httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + token},
            trust_env=False,
            timeout=30,
        ) as api,
    ):
        server.request("thread/read", {"threadId": thread_id, "includeTurns": False})
        deadline = time.monotonic() + watch_seconds
        while True:
            cursor = None
            for _ in range(page_budget):
                page = server.request(
                    "thread/items/list", {"threadId": thread_id, "limit": 100, "cursor": cursor}
                )
                for entry in page.get("data", []):
                    event = normalize_app_item(thread_id, entry["item"], scope)
                    event.metadata["app_server_entry"] = {k: v for k, v in entry.items() if k != "item"}
                    if entry.get("startedAtMs") is not None:
                        event.occurred_at = timestamp(entry["startedAtMs"] / 1000)
                    response = api.post("/api/events", json=event.model_dump(mode="json"))
                    response.raise_for_status()
                    result = response.json()
                    duplicates += int(result["duplicate"])
                    count += int(not result["duplicate"])
                cursor = page.get("nextCursor")
                if not cursor:
                    break
            else:
                raise RuntimeError(
                    "Page budget reached; completed events are durable, re-run to resume idempotently"
                )
            if watch_seconds == 0 or time.monotonic() >= deadline:
                break
            time.sleep(min(2, max(0, deadline - time.monotonic())))
    return {
        "events": count,
        "duplicates": duplicates,
        "capture_mode": "explicit-thread read-only backfill/poll",
        "note": "No turn/start, tool execution, approval grant or model generation",
    }

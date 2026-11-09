import argparse
import json
import os
import sys
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(prog="second-brain")
    parser.add_argument("--data", default=os.environ.get("SB_DATA_DIR", "data"))
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    start = sub.add_parser("start", help="Start or reuse the local background service")
    start.add_argument("--port", type=int, default=8765)
    doctor = sub.add_parser("doctor", help="Read-only database and connection checks")
    doctor.add_argument("--port", type=int, default=8765)
    sub.add_parser("mcp")
    sub.add_parser("rotate-owner-key", help="Replace the local owner key while the service is stopped")
    sub.add_parser("model-install")
    sub.add_parser("speech-model-install")
    app_server = sub.add_parser("codex-capture")
    app_server.add_argument("--thread-id", required=True)
    app_server.add_argument("--scope", default="global")
    app_server.add_argument("--watch-seconds", type=int, default=0)
    benchmark = sub.add_parser("benchmark")
    benchmark.add_argument(
        "--split", choices=["development", "validation", "test", "all"], default="validation"
    )
    benchmark.add_argument("--performance", action="store_true")
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--scope")
    clip = sub.add_parser("clip", help="Capture a link, text, or file for the assistant's inbox")
    clip_source = clip.add_mutually_exclusive_group(required=True)
    clip_source.add_argument("--url")
    clip_source.add_argument("--text")
    clip_source.add_argument("--stdin", action="store_true", help="Read UTF-8 clipboard text or a link")
    clip_source.add_argument("--file", type=Path)
    clip.add_argument("--scope", default=os.environ.get("SB_SCOPE", "global"))
    clip.add_argument("--sensitivity", type=int, choices=range(4), default=1)
    clip.add_argument("--note", default="")
    hook = sub.add_parser("hook")
    hook.add_argument("--client", required=True, choices=["codex", "claude-code", "gemini-cli", "cursor"])
    hook.add_argument("--scope", default=os.environ.get("SB_SCOPE", "global"))
    hook.add_argument("--project-root", type=Path, default=os.environ.get("SB_PROJECT_ROOT"))
    hook.add_argument(
        "--context-only", action="store_true", help="Read continuity context without capturing events"
    )
    setup = sub.add_parser("client-config")
    setup.add_argument("--client", required=True, choices=["codex", "claude-code", "gemini-cli", "cursor"])
    args = parser.parse_args()
    if args.command == "serve":
        from .api import create_app
        from .service import service_lock
        import uvicorn

        root = Path(args.data).resolve()
        try:
            if not 1 <= args.port <= 65535:
                parser.error("Port must be between 1 and 65535")
            with service_lock(root):
                print(f"Second Brain OS: http://127.0.0.1:{args.port}")
                print(f"Owner login key: {root / 'owner.token'} (never share this key with models)")
                uvicorn.run(
                    create_app(root),
                    host="127.0.0.1",
                    port=args.port,
                    access_log=False,
                    log_level="warning",
                    proxy_headers=False,
                )
        except RuntimeError as exc:
            parser.error(str(exc))
    elif args.command == "rotate-owner-key":
        from secrets import token_urlsafe

        from .service import service_lock
        from .vault import write_private

        root = Path(args.data).resolve()
        with service_lock(root):
            key_path = root / "owner.token"
            if not key_path.is_file():
                parser.error("Owner key is unavailable in this data directory")
            write_private(key_path, token_urlsafe(48).encode("ascii"))
        print("Owner key rotated. Restart the service and sign in again.")
    elif args.command == "start":
        from .service import ensure_service

        try:
            print(json.dumps(ensure_service(args.data, args.port), ensure_ascii=False))
        except (RuntimeError, ValueError, OSError) as exc:
            parser.error(str(exc))
    elif args.command == "doctor":
        from .doctor import diagnose

        report = diagnose(args.data, args.port)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["ready"] else 1)
    elif args.command == "mcp":
        from .mcp_server import main as mcp_main

        mcp_main()
    elif args.command == "codex-capture":
        from .app_server import capture_thread

        print(json.dumps(capture_thread(args.thread_id, args.scope, args.watch_seconds), ensure_ascii=False))
    elif args.command == "speech-model-install":
        from .local_media import install_speech_model

        result = install_speech_model(Path(args.data))
        print(
            json.dumps(
                {
                    "repository": result["repository"],
                    "revision": result["revision"],
                    "files": len(result["sha256"]),
                }
            )
        )
    elif args.command == "model-install":
        from .providers import install_model

        print(json.dumps(install_model(Path(args.data)), ensure_ascii=False))
    elif args.command == "benchmark":
        from .benchmark import run_evaluation, run_performance

        result = (
            run_performance(Path(args.data) / "performance")
            if args.performance
            else run_evaluation(Path(args.data) / "evaluation", split=args.split)
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "client-config":
        from .client_config import generate

        print(json.dumps(generate(args.client, Path.cwd()), ensure_ascii=False, indent=2))
    else:
        from .credentials import client_token

        payload = None
        if args.command == "hook":
            payload = json.loads(sys.stdin.buffer.read(2_000_001).decode("utf-8-sig"))
            if payload.get("no_memory") is True:
                print("{}")
                return
            if args.project_root:
                cwd = payload.get("cwd")
                if (
                    not isinstance(cwd, str)
                    or not Path(cwd).is_absolute()
                    or not Path(cwd).resolve().is_relative_to(args.project_root.resolve())
                ):
                    print("{}")
                    return
        token = client_token()
        if not token:
            if args.command == "hook" and args.context_only:
                print("{}")
                return
            parser.error("SB_TOKEN must contain a restricted API token")
        port = int(os.environ.get("SB_PORT", "8765"))
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + token},
            trust_env=False,
            timeout=30,
        ) as client:
            if args.command == "clip":
                clip_request(client, args)
            elif args.command == "hook":
                assert payload is not None
                if not args.context_only:
                    response = client.post(
                        "/api/capture/" + args.client, params={"scope": args.scope}, json=payload
                    )
                    response.raise_for_status()
                event_name = (
                    payload.get("hook_event_name")
                    or payload.get("hookEventName")
                    or payload.get("event_name")
                )
                if event_name in {"SessionStart", "sessionStart"}:
                    try:
                        response = client.post(
                            "/api/action/brain.prepare_context",
                            json={"query": "Nerede kalmıştık?", "scope": args.scope, "budget": 2000},
                            timeout=2,
                        )
                        response.raise_for_status()
                        context = response.json()
                    except (httpx.HTTPError, ValueError):
                        # Normal MCP retrieval can still resume the project when the hook is unavailable.
                        print("{}")
                        return
                    print(
                        json.dumps(
                            {
                                "hookSpecificOutput": {
                                    "hookEventName": event_name,
                                    "additionalContext": json.dumps(context, ensure_ascii=False),
                                }
                            },
                            ensure_ascii=False,
                        )
                    )
                else:
                    print("{}")
            else:
                response = client.post("/api/search", json={"query": args.query, "scope": args.scope})
                response.raise_for_status()
                print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def clip_request(client, args):
    options = {"scope": args.scope, "sensitivity": args.sensitivity, "note": args.note}
    if args.file is not None:
        from .importers import MAX_FILE

        with args.file.open("rb") as source:
            if not 0 < os.fstat(source.fileno()).st_size <= MAX_FILE:
                raise ValueError("File must be between 1 byte and 100 MiB")
            response = client.post("/api/inbox/file", data=options, files={"file": (args.file.name, source)})
    else:
        value = sys.stdin.buffer.read(96_004).decode("utf-8-sig") if args.stdin else args.url or args.text
        value = value.strip()
        is_url = args.url is not None or (
            args.stdin
            and value.lower().startswith(("https://", "http://"))
            and not any(c.isspace() for c in value)
        )
        response = client.post(
            "/api/inbox", json={**options, "text": value, "kind": "url" if is_url else "text"}
        )
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False))


if __name__ == "__main__":
    main()

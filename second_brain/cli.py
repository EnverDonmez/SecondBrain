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
    hook = sub.add_parser("hook")
    hook.add_argument("--client", required=True, choices=["codex", "claude-code", "gemini-cli", "cursor"])
    hook.add_argument("--scope", default="global")
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
                    create_app(root), host="127.0.0.1", port=args.port, access_log=False, log_level="warning"
                )
        except RuntimeError as exc:
            parser.error(str(exc))
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

        token = client_token()
        if not token:
            parser.error("SB_TOKEN must contain a restricted API token")
        port = int(os.environ.get("SB_PORT", "8765"))
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + token},
            trust_env=False,
            timeout=30,
        ) as client:
            if args.command == "hook":
                payload = json.loads(sys.stdin.buffer.read(2_000_001).decode("utf-8"))
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
                    context = client.post(
                        "/api/action/brain.prepare_context",
                        json={"query": "Beynimi tara", "scope": args.scope},
                    ).json()
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


if __name__ == "__main__":
    main()

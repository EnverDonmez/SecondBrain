"""Additional product acceptance evidence, using disposable synthetic brains only."""

import argparse
import hashlib
import io
import json
import os
import secrets
import shutil
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import zipfile

from goal_audit import record
from second_brain.capture import normalize_hook
from second_brain.core import Brain
from second_brain.db import dumps
from second_brain.models import OWNER, EventInput, Principal, SearchInput, now
from second_brain.runtime import process_usage
from second_brain.security import Denied, NotFound


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "goal-audit-20261026" / "final"


def skill_package(version):
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            "SKILL.md",
            "---\nname: audit-report\ndescription: Synthetic report procedure\n---\n"
            + f"Validate input and prepare report, version {version}.",
        )
        archive.writestr("scripts/report.py", f"print('synthetic version {version}')\n")
    return package.getvalue()


def snapshot(brain):
    return {
        "events": brain.events.list(OWNER, limit=100),
        "memories": brain.retrieval.search(SearchInput(limit=100), OWNER)["items"],
        "skills": brain.skills.list(OWNER),
        "tools": brain.tools.list(OWNER),
        "feedback": brain.learning.list(OWNER),
    }


def supplemental():
    report = {"created_at": now(), "synthetic_only": True, "checks": []}

    def check(name, passed, evidence, priority="P1"):
        report["checks"].append(
            {"name": name, "passed": bool(passed), "priority": priority, "evidence": evidence}
        )

    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        brain = Brain(directory)
        preference = record(brain, "Kısa Türkçe cevap", "reply_style")
        policy = record(brain, "Her tıklamadan önce bağımsız ajan kontrolü", "click_rule", "POLICY")
        project = record(brain, "SQLite kullan", "database", "DECISION", "audit-project")
        for _index in range(3):
            brain.learning.feedback("Test sonrası sonucu kaydet.", "global", "success", OWNER)
        packages = [skill_package(1), skill_package(2)]
        skills = [brain.skills.register(package, OWNER) for package in packages]
        brain.skills.state(skills[0]["id"], True, OWNER)
        brain.skills.state(skills[1]["id"], True, OWNER)
        tool = brain.tools.register("audit-python", "binary", {"binary": "python"}, OWNER)[0]
        brain.tools.set_state(tool["id"], True, OWNER)
        agent = Principal(
            id="audit-agent", role="agent", scopes=["global", "audit-project"], permissions=["read"]
        )
        expected = {"events": 8, "memories": 3, "skills": 2, "tools": 1}
        code = (
            "import json,sys; from second_brain.core import Brain; "
            "from second_brain.models import OWNER,SearchInput; b=Brain(sys.argv[1]); "
            "print(json.dumps({'events':len(b.events.list(OWNER)),"
            "'memories':len(b.retrieval.search(SearchInput(),OWNER)['items']),"
            "'skills':len(b.skills.list(OWNER)),'tools':len(b.tools.list(OWNER))}))"
        )
        child = subprocess.run(  # noqa: S603 -- fixed interpreter and read-only synthetic child
            [sys.executable, "-c", code, directory],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        counts = json.loads(child.stdout)
        check("restart_in_separate_process", counts == expected, {"expected": expected, "actual": counts})
        check(
            "skill_latest_version_selection",
            [s["state"] for s in brain.skills.list(OWNER)] == ["enabled", "disabled"],
            [{"version": s["version"], "state": s["state"]} for s in brain.skills.list(OWNER)],
            "P2",
        )
        before = snapshot(brain)
        password = secrets.token_urlsafe(24)
        backup = brain.backups.create(password, OWNER)
        verified = brain.backups.verify(backup["id"], password, OWNER)
        brain.skills.state(skills[1]["id"], False, OWNER)
        brain.tools.set_state(tool["id"], False, OWNER)
        record(brain, "Should disappear on restore", "after_backup")
        brain.backups.restore(backup["id"], password, OWNER)
        after = snapshot(brain)
        # Compare complete values as well as identities, flags and original package bytes.
        before_ids = {
            key: [row["id"] if "id" in row else row for row in rows] for key, rows in before.items()
        }
        after_ids = {key: [row["id"] if "id" in row else row for row in rows] for key, rows in after.items()}
        restored_package = brain.skills.export(skills[1]["id"], OWNER)
        check(
            "encrypted_backup_preserves_complete_state",
            before == after
            and brain.tools.list(OWNER)[0]["enabled"] == 1
            and brain.skills.get(skills[1]["id"], OWNER)["state"] == "enabled"
            and restored_package == packages[1],
            {
                "row_identity_equal": before_ids == after_ids,
                "complete_rows_equal": before == after,
                "integrity": verified["integrity"],
                "skill_package_sha256_equal": hashlib.sha256(restored_package).digest()
                == hashlib.sha256(packages[1]).digest(),
                "tool_enabled": brain.tools.list(OWNER)[0]["enabled"],
            },
        )
        brain.skills.state(skills[0]["id"], True, OWNER)
        check(
            "skill_rollback_preserves_original_package",
            brain.skills.export(skills[0]["id"], OWNER) == packages[0]
            and brain.skills.get(skills[0]["id"], agent)["state"] == "enabled",
            {"version": brain.skills.get(skills[0]["id"], agent)["version"]},
            "P2",
        )
        try:
            brain.skills.get(skills[1]["id"], agent)
            disabled_hidden = False
        except NotFound:
            disabled_hidden = True
        check("disabled_skill_hidden_from_agent", disabled_hidden, {"hidden": disabled_hidden})
        packet = brain.dispatch("brain.prepare_context", {"scope": "audit-project", "budget": 8000}, agent)
        ids = {r["id"] for r in packet["records"]}
        check(
            "project_context_contains_global_policy_and_preference",
            {preference["id"], policy["id"], project["id"]} <= ids,
            {
                "types": [r["memory_type"] for r in packet["records"]],
                "scopes": [r["scope"] for r in packet["records"]],
            },
        )
        query_packet = brain.dispatch("brain.prepare_context", {"query": "SQLite", "budget": 8000}, agent)
        check(
            "task_context_contains_global_policy",
            policy["id"] in {r["id"] for r in query_packet["records"]},
            {"types": [r["memory_type"] for r in query_packet["records"]]},
        )
        budget_failures = []
        source_failures = []
        for budget in range(512, 6001, 37):
            packet = brain.dispatch("brain.prepare_context", {"budget": budget}, agent)
            size = len(dumps(packet).encode())
            if size > budget or packet["estimated_tokens_upper_bound"] < size:
                budget_failures.append(
                    {"budget": budget, "bytes": size, "estimate": packet["estimated_tokens_upper_bound"]}
                )
            if set(packet["sources"]) != {s for r in packet["records"] for s in r["source_event_ids"]}:
                source_failures.append(budget)
        check(
            "context_budget_and_estimate",
            not budget_failures,
            {"cases": len(range(512, 6001, 37)), "failures": budget_failures},
        )
        check("context_sources_match_records", not source_failures, {"failing_budgets": source_failures})
        exports = {fmt: brain.export(OWNER, fmt) for fmt in ["json", "jsonl", "markdown"]}
        check(
            "canonical_export_contains_tool_definitions",
            "tool_configs" in json.loads(exports["json"]) and "audit-python" in exports["jsonl"],
            {
                "json_tables": list(json.loads(exports["json"])),
                "tool_in_jsonl": "audit-python" in exports["jsonl"],
            },
        )
        capabilities = brain.dispatch("brain.list_capabilities", {}, agent)
        context = brain.dispatch("brain.prepare_context", {"budget": 8000}, agent)
        check(
            "enabled_tool_discoverable_to_agent",
            "audit-python" in dumps(capabilities) or "audit-python" in dumps(context),
            {"capability_fields": list(capabilities), "context_has_tool": "audit-python" in dumps(context)},
        )
        forbidden = []
        for operation, args in [
            ("brain.commit_memory", {"id": preference["id"]}),
            ("brain.forget", {"id": preference["id"], "confirmation": preference["id"]}),
        ]:
            try:
                brain.dispatch(operation, args, agent)
                forbidden.append(operation)
            except Denied:
                pass
        check("agent_cannot_approve_or_delete", not forbidden, {"unexpected_allowed_operations": forbidden})
        scope_reader = agent.model_copy(update={"scopes": ["audit-project"]})
        limited = brain.dispatch("brain.prepare_context", {"budget": 8000}, scope_reader)
        check(
            "project_only_reader_does_not_leak_global",
            all(r["scope"] == "audit-project" for r in limited["records"]) and not limited["skills"],
            {"scopes": [r["scope"] for r in limited["records"]], "skills": len(limited["skills"])},
        )

    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        brain = Brain(directory)
        hooks = {
            "codex": "UserPromptSubmit",
            "claude-code": "UserPromptSubmit",
            "gemini-cli": "BeforeAgent",
            "cursor": "beforeSubmitPrompt",
        }
        outcomes = []
        for client, hook in hooks.items():
            payload = {
                "hook_event_name": hook,
                "session_id": "audit-session",
                "event_id": "audit-item",
                "prompt": "Tercihim: Kısa cevap",
            }
            first = brain.events.ingest(normalize_hook(client, payload), OWNER)
            replay = brain.events.ingest(normalize_hook(client, payload), OWNER)
            outcomes.append(
                {"client": client, "same_id": first["id"] == replay["id"], "duplicate": replay["duplicate"]}
            )
        check(
            "stable_hook_replay_deduplicates_four_clients",
            all(o["same_id"] and o["duplicate"] for o in outcomes),
            outcomes,
        )
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "audit-session",
            "prompt": "Aynı metin",
        }
        unidentified = [brain.events.ingest(normalize_hook("codex", payload), OWNER) for _ in range(2)]
        report["idless_capture_limitation"] = {
            "stored_as_distinct_events": unidentified[0]["id"] != unidentified[1]["id"],
            "note": "No stable event ID means replay cannot be distinguished from intentional repeated input.",
        }
        event = brain.events.ingest(
            EventInput(source="feedback-audit", source_id="one", text="Kontrol et"), OWNER
        )
        repeated = [
            brain.learning.feedback("Kontrol et", "global", "correction", OWNER, event["id"])
            for _ in range(8)
        ]
        check(
            "same_feedback_evidence_does_not_inflate_learning",
            all(r["evidence_count"] == 1 and not r["candidate_lesson"] for r in repeated),
            {"counts": [r["evidence_count"] for r in repeated]},
        )
    return report


def soak():
    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        brain = Brain(directory)
        connections = []
        connect = brain.db.connect

        def counted_connect():
            connections.append(time.perf_counter())
            return connect()

        brain.db.connect = counted_connect
        worker = threading.Thread(target=brain.worker, daemon=True)
        samples = [{"elapsed_s": 0, **process_usage()}]
        started = time.perf_counter()
        worker.start()
        try:
            for _ in range(6):
                brain.stop_event.wait(10)
                samples.append({"elapsed_s": time.perf_counter() - started, **process_usage()})
        finally:
            brain.stop_event.set()
            worker.join(timeout=3)
        elapsed = samples[-1]["elapsed_s"]
        return {
            "created_at": now(),
            "seconds": elapsed,
            "samples": samples,
            "cpu_core_percent": (samples[-1]["cpu_seconds"] - samples[0]["cpu_seconds"]) / elapsed * 100,
            "rss_delta_bytes": samples[-1]["rss_bytes"] - samples[0]["rss_bytes"],
            "connections": len(connections),
            "connections_per_second": len(connections) / elapsed,
            "worker_stopped": not worker.is_alive(),
            "limitations": "60 seconds of an empty synthetic worker; not a multi-hour leak or loaded-server test.",
        }


def semantic_scale():
    from second_brain.providers import index_vectors

    os.environ["SB_MODEL_DIR"] = str(ROOT / "data" / "models")
    report = {"created_at": now(), "synthetic_only": True, "scales": []}
    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        brain = Brain(directory)
        for index in range(1000):
            record(
                brain,
                f"Araştırma projesi {index}: depolama motoru SQLite seçildi.",
                f"decision-{index}",
                "DECISION",
            )
        started = time.perf_counter()
        index_result = index_vectors(brain.db, OWNER)
        report["indexing"] = {**index_result, "wall_seconds": time.perf_counter() - started}
        report["usage_after_indexing"] = process_usage()
        for engine in ["vector", "hybrid"]:
            samples = [
                brain.retrieval.search(
                    SearchInput(
                        query=f"Araştırma projesi {i * 97}: veritabanı kararı", engine=engine, limit=5
                    ),
                    OWNER,
                )["elapsed_ms"]
                for i in range(10)
            ]
            report["scales"].append(
                {
                    "engine": engine,
                    "indexed_memories": 1000,
                    "queries": len(samples),
                    "p50_ms": statistics.median(samples),
                    "p95_ms": sorted(samples)[-1],
                    "samples_ms": samples,
                }
            )
        report["limitations"] = (
            "Only 1,000 semantic records, 10 queries/engine, no quality scoring; 50,000-record earlier benchmark had no vectors."
        )
    return report


def quality():
    commands = [
        [sys.executable, "-m", "ruff", "check", "second_brain", "tests", "scripts"],
        [sys.executable, "-m", "ruff", "format", "--check", "second_brain", "tests", "scripts"],
        [sys.executable, "-m", "mypy", "second_brain", "--ignore-missing-imports", "--check-untyped-defs"],
        [shutil.which("node") or "node", "--check", "second_brain/static/app.js"],
        [shutil.which("node") or "node", "--check", "second_brain/static/docs.js"],
        [sys.executable, "scripts/scan_secrets.py"],
    ]
    results = []
    for command in commands:
        started = time.perf_counter()
        result = subprocess.run(  # noqa: S603 -- fixed local validation commands, no shell
            command, cwd=ROOT, capture_output=True, text=True, timeout=90, check=False
        )
        results.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "seconds": time.perf_counter() - started,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    return {"created_at": now(), "checks": results, "all_passed": all(r["exit_code"] == 0 for r in results)}


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["supplemental", "soak", "semantic-scale", "quality"])
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output_dir.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "supplemental": supplemental,
        "soak": soak,
        "semantic-scale": semantic_scale,
        "quality": quality,
    }[args.mode]()
    (OUT / (args.mode + ".json")).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"mode": args.mode, "completed": True, "output": str(OUT)}))


if __name__ == "__main__":
    main()

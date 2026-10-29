"""Before/after engineering probes; isolated synthetic data, no LLM or user DB."""

import argparse
import hashlib
import json
import os
import secrets
import tempfile
import time
from pathlib import Path

from second_brain.core import Brain
from second_brain.db import dumps
from second_brain.models import OWNER, EventInput, MemoryInput, SearchInput, now


def evaluate(phase):
    os.environ["SB_MEMORY_MODE"] = "economy"
    Path(".test-tmp").mkdir(exist_ok=True)
    target = Path("reports/engineering-20261027")
    target.mkdir(exist_ok=True)
    if phase == "before":
        before = target / "baseline"
        before.mkdir(exist_ok=True)
        for name in ["retrieval.py", "directory.py", "core.py", "assistant_contract.py"]:
            (before / (name + ".txt")).write_bytes((Path("second_brain") / name).read_bytes())
    with tempfile.TemporaryDirectory(dir=".test-tmp", prefix="evidence-probe-") as temporary:
        brain = Brain(temporary)

        def save(value, **updates):
            event = brain.events.ingest(
                EventInput(
                    source="synthetic-probe",
                    source_id=secrets.token_hex(12),
                    text=value,
                    scope="global",
                    occurred_at="2024-01-01",
                ),
                OWNER,
            )
            fields = {
                "subject": secrets.token_hex(12),
                "predicate": "decision",
                "value": value,
                "source_event_ids": [event["id"]],
                "valid_from": "2024-01-01",
                **updates,
            }
            return brain.memory.commit(brain.memory.propose(MemoryInput(**fields), OWNER)["id"], OWNER)

        direct = [save(f"Quartz release requirement {i}", topics=["Broad"]) for i in range(4)]
        seed = save("Topaz release", topics=["Broad"])
        related = save("Deniz handles the backup", related_memory_ids=[seed["id"]], importance=1)
        for i in range(24):
            save(f"Garden journal {i}", topics=["Broad"], importance=5)
        original = brain.events.ingest(
            EventInput(
                source="synthetic-probe",
                source_id="old-source",
                text="Orion teslim tarihi 17 Kasım olarak belirlendi.",
                occurred_at="2024-01-01",
            ),
            OWNER,
        )
        for i in range(16):
            brain.events.ingest(
                EventInput(
                    source="synthetic-probe",
                    source_id=f"recent-{i}",
                    text=f"Bahçe teslim notu {i}",
                    occurred_at="2026-01-01",
                ),
                OWNER,
            )
        current = save("SQLite", subject="Synthetic project", predicate="database")
        conflict = save("PostgreSQL", subject="Synthetic project", predicate="database")
        assert conflict["status"] == "disputed"
        probes = []
        for name, query, expected, limit in [
            ("direct_vs_topic_distraction", "Quartz", {x["id"] for x in direct}, 4),
            ("explicit_vs_topic_hub", "Topaz", {seed["id"], related["id"]}, 2),
        ]:
            started = time.perf_counter()
            found = brain.retrieval.search(SearchInput(query=query, limit=limit), OWNER)
            returned = {x["id"] for x in found["items"]}
            probes.append(
                {
                    "scenario": name,
                    "all_required_evidence": expected <= returned,
                    "recall_at_k": len(expected & returned) / len(expected),
                    "precision_at_k": len(expected & returned) / max(1, len(returned)),
                    "k": limit,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "candidate_records": found["candidates_examined"],
                }
            )
        packet = brain.dispatch("brain.prepare_context", {"query": "Orion teslim", "budget": 2000}, OWNER)
        probes.append(
            {
                "scenario": "old_specific_source_vs_recent_weak_matches",
                "correct_source_at_1": bool(packet.get("episodes"))
                and packet["episodes"][0]["id"] == original["id"],
                "context_bytes": len(dumps(packet).encode()),
                "budget": 2000,
            }
        )
        packet = brain.dispatch("brain.prepare_context", {"query": "SQLite", "budget": 3000}, OWNER)
        row = next(x for x in packet["records"] if x["id"] == current["id"])
        probes.append(
            {
                "scenario": "unresolved_dispute_visibility",
                "review_signal": bool(row.get("review_required")),
                "disputed_claim_promoted": any(x["id"] == conflict["id"] for x in packet["records"]),
            }
        )
        budgets = []
        for budget in [512, 800, 1500, 3000]:
            context = brain.dispatch("brain.prepare_context", {"query": "Quartz", "budget": budget}, OWNER)
            budgets.append(
                {
                    "budget": budget,
                    "bytes": len(dumps(context).encode()),
                    "omission_signal": context.get("truncated"),
                    "records": len(context["records"]),
                }
            )
        assert not brain.db.one("SELECT 1 FROM usage")
        result = {
            "measured_at": now(),
            "phase": phase,
            "method": "Four synthetic engineering probes on one pooled local store. Not QA accuracy, Turkish language coverage or a comparison with upstream products.",
            "source_sha256": {
                name: hashlib.sha256((Path("second_brain") / name).read_bytes()).hexdigest()
                for name in ["retrieval.py", "directory.py", "core.py"]
            },
            "probes": probes,
            "budget_checks": budgets,
            "additional_model_calls": 0,
            "limits": "Small diagnostic corpus; timings are a single run, not a latency distribution. Gold IDs are used only by the evaluator, not passed as search inputs.",
        }
    (target / f"evidence-{phase}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["before", "after"], required=True)
    evaluate(parser.parse_args().phase)

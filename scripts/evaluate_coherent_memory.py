"""Synthetic context freshness measurement; never opens personal data."""

import json
import math
import os
import statistics
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from second_brain.core import Brain
from second_brain.db import dumps
from second_brain.memory import project
from second_brain.models import OWNER, EventInput, MemoryInput, now


def measure(operation, runs=30):
    elapsed = []
    for _ in range(runs):
        start = time.perf_counter()
        result = operation()
        elapsed.append((time.perf_counter() - start) * 1000)
    return result, {
        "runs": runs,
        "median_ms": round(statistics.median(elapsed), 3),
        "p95_ms": round(sorted(elapsed)[math.ceil(runs * 0.95) - 1], 3),
    }


def main():
    os.environ["SB_MEMORY_MODE"] = "economy"
    Path(".test-tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coherent-scale-", dir=".test-tmp") as directory:
        brain = Brain(directory)
        with (
            patch(
                "second_brain.providers.LocalEmbedder.embed",
                side_effect=AssertionError("Unexpected embedding"),
            ),
            patch.object(brain.provider, "extract", side_effect=AssertionError("Unexpected LLM")),
        ):
            event = brain.events.ingest(
                EventInput(source="synthetic-scale", source_id="fixture", text="Synthetic scale fixture."),
                OWNER,
            )
            proposed = brain.memory.propose(
                MemoryInput(
                    subject="Synthetic origin",
                    predicate="decision",
                    value="Quartz launch",
                    topics=["Shared"],
                    source_event_ids=[event["id"]],
                ),
                OWNER,
            )
            seed = brain.memory.commit(proposed["id"], OWNER)
            template = brain.db.one("SELECT * FROM memories WHERE id=?", (seed["id"],))
            with brain.db.transaction() as con:
                for index in range(5000):
                    row = {
                        **template,
                        "id": f"generated-{index}",
                        "logical_id": f"generated-{index}",
                        "subject": f"Synthetic item {index}",
                        "value": f"Archive note {index}",
                        "topics": dumps(["Shared"] if index < 240 else ["Archive"]),
                        "related_memory_ids": dumps([seed["id"]] if index < 4 else []),
                    }
                    brain.memory._insert(con, row)
                    project(con, row)
            request = {"query": "Quartz", "budget": 3000}

            def fresh():
                return brain.dispatch("brain.prepare_context", request, OWNER)

            fresh()  # Exclude first setup/cache work from both warm distributions.
            packet, fresh_timing = measure(fresh)
            conditional = {**request, "known_state": packet["state"]}

            def reuse():
                return brain.dispatch("brain.prepare_context", conditional, OWNER)

            with patch.object(brain.retrieval, "search", side_effect=AssertionError("Full search on reuse")):
                unchanged, reused_timing = measure(reuse)
            assert unchanged["unchanged"] and packet["state"] == unchanged["state"]
            assert packet["truncated"] == unchanged["truncated"]
            assert not brain.db.one("SELECT 1 FROM usage")
            report = {
                "measured_at": now(),
                "synthetic_records": 5001,
                "warm_fresh_context": fresh_timing,
                "warm_unchanged_context": reused_timing,
                "fresh_bytes": len(dumps(packet).encode()),
                "unchanged_bytes": len(dumps(unchanged).encode()),
                "budget_upper_bound": 3000,
                "additional_model_calls": 0,
                "unchanged_full_search_calls": 0,
                "limits": "One process, synthetic hub query, warm nearest-rank p95 over 30 runs. Bytes are conservative serialization units, not provider tokens or billing. Metadata checks still query SQLite indexes. A retained prior packet is necessary to reuse context; no end-to-end answer accuracy claim.",
            }
    target = Path("reports/coherent-memory-20261028/performance.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

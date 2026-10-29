"""Bounded local retrieval on synthetic data, with model methods forbidden."""

import json
import os
import statistics
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from second_brain.core import Brain
from second_brain.db import dumps
from second_brain.memory import project
from second_brain.models import OWNER, EventInput, MemoryInput, SearchInput, now


def main():
    os.environ["SB_MEMORY_MODE"] = "economy"
    Path(".test-tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="evidence-scale-", dir=".test-tmp") as directory:
        brain = Brain(directory)
        with (
            patch(
                "second_brain.providers.LocalEmbedder.embed",
                side_effect=AssertionError("Unexpected embedding"),
            ),
            patch.object(brain.provider, "extract", side_effect=AssertionError("Unexpected LLM")),
        ):
            event = brain.events.ingest(
                EventInput(
                    source="synthetic-scale",
                    source_id="fixture",
                    text="Synthetic generated fixture for performance only.",
                ),
                OWNER,
            )
            candidate = brain.memory.propose(
                MemoryInput(
                    subject="Synthetic origin",
                    predicate="decision",
                    value="Quartz launch",
                    topics=["Shared"],
                    source_event_ids=[event["id"]],
                ),
                OWNER,
            )
            seed = brain.memory.commit(candidate["id"], OWNER)
            template = brain.db.one("SELECT * FROM memories WHERE id=?", (seed["id"],))
            with brain.db.transaction() as con:
                for index in range(5000):
                    row = {
                        **template,
                        "id": f"generated-{index}",
                        "logical_id": f"generated-{index}",
                        "subject": f"Synthetic item {index}",
                        "value": f"Backup detail {index}" if index < 240 else f"Archive note {index}",
                        "topics": dumps(["Shared"] if index < 240 else ["Archive"]),
                        "related_memory_ids": dumps([seed["id"]] if index < 4 else []),
                    }
                    brain.memory._insert(con, row)
                    project(con, row)
            elapsed = []
            for _ in range(16):
                start = time.perf_counter()
                found = brain.retrieval.search(SearchInput(query="Quartz", limit=12), OWNER)
                elapsed.append((time.perf_counter() - start) * 1000)
            packet = brain.dispatch("brain.prepare_context", {"query": "Quartz", "budget": 3000}, OWNER)
            assert found["candidates_examined"] <= 96 and found["window_saturated"]
            assert len(dumps(packet).encode()) <= packet["budget"]
            assert packet["truncated"]
            assert {f"generated-{i}" for i in range(4)} <= {x["id"] for x in found["items"]}
            assert not brain.db.one("SELECT 1 FROM usage")
            report = {
                "measured_at": now(),
                "synthetic_records": 5001,
                "cold_first_ms": round(elapsed[0], 3),
                "warm_runs": 15,
                "warm_median_ms": round(statistics.median(elapsed[1:]), 3),
                "warm_p95_ms": round(sorted(elapsed[1:])[14], 3),
                "candidate_records": found["candidates_examined"],
                "candidate_limit": 96,
                "window_saturated": found["window_saturated"],
                "context_truncated": packet["truncated"],
                "context_bytes": len(dumps(packet).encode()),
                "context_budget": 3000,
                "additional_model_calls": 0,
                "limits": "One process and one synthetic hub query. Warm p95 is nearest rank over 15 runs. Candidate cap is loaded content, not total SQL work. Not production latency, QA accuracy, raw archival quality or provider token measurement.",
            }
    target = Path("reports/engineering-20261027/performance.json")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

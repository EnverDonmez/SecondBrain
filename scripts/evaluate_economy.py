"""Synthetic retrieval measurement; never opens the user's data directory."""

import json
import os
import statistics
import tempfile
import time
from pathlib import Path

from second_brain.core import Brain
from second_brain.db import dumps
from second_brain.memory import project
from second_brain.models import OWNER, EventInput, MemoryInput, SearchInput, now


def main():
    os.environ["SB_MEMORY_MODE"] = "economy"
    temporary_root = Path(".test-tmp")
    temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="economy-measure-", dir=temporary_root) as directory:
        brain = Brain(directory)
        source = brain.events.ingest(
            EventInput(source="synthetic-benchmark", source_id="one", text="Synthetic facts only."), OWNER
        )
        seed = brain.memory.propose(
            MemoryInput(
                subject="Synthetic root",
                predicate="decision",
                value="Quartz deployment",
                topics=["deployment"],
                source_event_ids=[source["id"]],
            ),
            OWNER,
        )
        brain.memory.commit(seed["id"], OWNER)
        template = brain.db.one("SELECT * FROM memories WHERE id=?", (seed["id"],))
        with brain.db.transaction() as con:
            for index in range(5000):
                row = {
                    **template,
                    "id": f"synthetic-{index}",
                    "logical_id": f"synthetic-{index}",
                    "subject": f"Synthetic item {index}",
                    "predicate": "detail",
                    "value": f"Backup detail {index}" if index < 40 else f"Unrelated archive {index}",
                    "topics": dumps(["deployment"] if index < 40 else ["archive"]),
                }
                brain.memory._insert(con, row)
                project(con, row)
        timings = []
        for _ in range(15):
            start = time.perf_counter()
            result = brain.retrieval.search(SearchInput(query="Quartz", limit=12), OWNER)
            timings.append((time.perf_counter() - start) * 1000)
        context = brain.dispatch("brain.prepare_context", {"query": "Quartz", "budget": 3000}, OWNER)
        assert result["candidates_examined"] <= 96
        assert len(dumps(context).encode("utf-8")) <= 3000
        assert not brain.db.one("SELECT 1 FROM usage")
        assert not brain.db.one("SELECT 1 FROM jobs WHERE kind='vector_memory'")
        report = {
            "measured_at": now(),
            "synthetic_records": 5001,
            "query": "Quartz",
            "engine": "economy",
            "runs": len(timings),
            "median_ms": round(statistics.median(timings), 3),
            "max_ms": round(max(timings), 3),
            "candidates_examined": result["candidates_examined"],
            "candidate_limit": result["candidate_limit"],
            "graph_hops": result["graph_hops"],
            "returned_items": len(result["items"]),
            "context_records": len(context["records"]),
            "context_bytes": len(dumps(context).encode("utf-8")),
            "context_budget": 3000,
            "additional_model_calls": 0,
            "limits": "Synthetic local measurement, not total SQL rows visited, production latency, model recall quality or the conversation provider's token bill.",
        }
    target = Path("reports/economy-evaluation.json")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

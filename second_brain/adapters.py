from typing import Protocol
import importlib.util
import os
from pathlib import Path

from .models import SearchInput
from .security import require


class MemoryEngine(Protocol):
    name: str
    version: str

    def health(self) -> dict: ...
    def capabilities(self) -> list[str]: ...
    def initialize(self) -> dict: ...
    def ingest(self, records: list[dict]) -> dict: ...
    def retrieve(self, query: SearchInput, principal) -> dict: ...
    def invalidate(self, identity: str) -> dict: ...
    def delete(self, identity: str) -> dict: ...
    def reindex(self, principal) -> dict: ...
    def recover(self, principal) -> dict: ...


class CanonicalAdapter:
    version = "1.0"

    def __init__(self, core, name="fts"):
        self.core, self.name = core, name

    def health(self):
        return {"name": self.name, "status": "working", "version": self.version}

    def capabilities(self):
        return ["retrieval", "temporal_filter", "scope_filter", "provenance", "reindex", "deletion"]

    def initialize(self):
        return self.health()

    def ingest(self, records):
        return {"status": "canonical_transaction_managed", "records": len(records)}

    def retrieve(self, query, principal):
        return self.core.retrieval.search(query.model_copy(update={"engine": self.name}), principal)

    def invalidate(self, identity):
        return {"id": identity, "status": "filtered_at_canonical_read"}

    def delete(self, identity):
        if self.core.db.one("SELECT 1 FROM memories WHERE id=?", (identity,)):
            raise ValueError("Delete canonically before acknowledging projection deletion")
        return {"id": identity, "acknowledged": True}

    def reindex(self, principal):
        require(principal, "admin")
        return self.core.memory.rebuild(principal)

    def recover(self, principal):
        return self.reindex(principal)


def engine_status(core):
    vector_ready = (
        Path(os.environ.get("SB_MODEL_DIR", str(core.db.root / "models"))) / "ready.json"
    ).exists() and importlib.util.find_spec("fastembed") is not None
    return [
        {
            "name": "Economy · indexed knowledge graph",
            "id": "economy",
            "status": "working",
            "role": "Default: FTS inverted index, up to 96 candidates and 0–2 graph hops; no model calls",
        },
        {
            "name": "SQLite FTS5",
            "id": "fts",
            "status": "working",
            "role": "Exact prefix lexical retrieval; no model calls",
        },
        {
            "name": "rank-bm25",
            "id": "bm25",
            "status": "working",
            "role": "Independent open source BM25 comparison",
        },
        {
            "name": "Canonical graph + reciprocal rank fusion",
            "id": "hybrid",
            "status": "working",
            "role": "Lexical and approved relationship retrieval",
        },
        {
            "name": "FastEmbed multilingual MiniLM",
            "id": "vector",
            "status": "working" if vector_ready else "blocked",
            "role": "Local CPU embeddings; overlapping chunks cover the full approved text",
            "reason": None if vector_ready else "Local model is not installed",
        },
        {
            "name": "Graphiti",
            "id": "graphiti",
            "status": "blocked",
            "reason": "Graph backend and verified local model integration are not configured; canonical temporal queries work independently",
        },
        {
            "name": "Mem0",
            "id": "mem0",
            "status": "experimental",
            "reason": "Optional projection integration is tested separately; no hosted API credentials enabled",
        },
        {
            "name": "Hindsight",
            "id": "hindsight",
            "status": "unsupported",
            "reason": "Requires its service/runtime; candidate evaluation is in SOURCE_REGISTRY",
        },
        {
            "name": "Supermemory",
            "id": "supermemory",
            "status": "unsupported",
            "reason": "Separate server license and model requirements; no binary installed",
        },
    ]

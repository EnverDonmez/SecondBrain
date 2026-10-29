"""Optional Mem0 projection: local Qdrant + real local embeddings, no LLM inference.

Mem0 owns only a disposable in-memory projection. Every read is filtered again
against canonical bitemporal, tenant, scope and clearance rules.
"""

import json
import os
from pathlib import Path

from .models import SearchInput
from .providers import LocalEmbedder
from .security import Denied, require


class OfflineEmbeddings:
    def __init__(self, config):
        self.local = LocalEmbedder(Path(config.model_kwargs["brain_root"]))

    def embed(self, text, memory_action=None):
        return self.local.embed([text])[0]


class NoInference:
    def __init__(self, config):
        pass

    def generate_response(self, *args, **kwargs):
        raise Denied("Mem0 LLM inference is disabled. Canonical approval/extraction owns memory decisions.")


class Mem0Adapter:
    name = "mem0"
    version = "2.2.1"

    def __init__(self, core):
        # Set BEFORE importing Mem0: importing upstream otherwise creates ~/.mem0 and enables telemetry.
        os.environ["MEM0_TELEMETRY"] = "false"
        os.environ["MEM0_DIR"] = str(core.db.root / "mem0-runtime")
        from mem0 import Memory
        from mem0.utils.factory import EmbedderFactory, LlmFactory
        from qdrant_client import QdrantClient

        # Upstream's supported provider factory seams; concrete classes never contact external services.
        old_embed = EmbedderFactory.provider_to_class["fastembed"]
        old_llm = LlmFactory.provider_to_class["openai"]
        self.core = core
        self.embedder = LocalEmbedder(core.db.root)
        self.client = QdrantClient(location=":memory:")
        try:
            EmbedderFactory.provider_to_class["fastembed"] = "second_brain.mem0_adapter.OfflineEmbeddings"
            LlmFactory.register_provider("openai", "second_brain.mem0_adapter.NoInference")
            self.engine = Memory.from_config(
                {
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "client": self.client,
                            "collection_name": "second_brain",
                            "embedding_model_dims": 384,
                        },
                    },
                    "embedder": {
                        "provider": "fastembed",
                        "config": {
                            "model": LocalEmbedder.model,
                            "embedding_dims": 384,
                            "model_kwargs": {"brain_root": str(core.db.root)},
                        },
                    },
                    "llm": {"provider": "openai", "config": {"model": "inference-disabled"}},
                    "history_db_path": ":memory:",
                }
            )
        finally:
            EmbedderFactory.provider_to_class["fastembed"] = old_embed
            LlmFactory.provider_to_class["openai"] = old_llm
        # Mem0's optional sparse encoder otherwise lazily downloads another model.
        # This projection deliberately uses dense semantic search only; our separate
        # rank-bm25 adapter supplies lexical comparison without hidden downloads.
        self.engine.vector_store._bm25_encoder = False
        self.mapping = {}

    def health(self):
        return {
            "status": "working",
            "name": self.name,
            "version": self.version,
            "llm_inference": False,
            "telemetry": False,
            "persistence": "disposable in-memory projection",
        }

    def capabilities(self):
        return [
            "semantic_retrieval",
            "local_embeddings",
            "ingest",
            "delete",
            "reindex",
            "canonical_authorization",
        ]

    def initialize(self):
        return self.health()

    def ingest(self, records):
        count = 0
        for record in records:
            if record["id"] in self.mapping or record["status"] != "active" or record["sensitivity"] >= 3:
                continue
            identities: list[str] = []
            for chunk in self.embedder.chunks(record["value"], record["subject"], record["predicate"]):
                result = self.engine.add(
                    chunk["text"],
                    user_id=record["tenant"],
                    metadata={
                        "canonical_id": record["id"],
                        "scope": record["scope"],
                        "start_char": chunk["start"],
                        "end_char": chunk["end"],
                    },
                    infer=False,
                )
                identities.extend(row["id"] for row in result.get("results", []))
            self.mapping[record["id"]] = identities
            count += 1
        return {"ingested": count}

    def retrieve(self, request: SearchInput, principal):
        where, args = self.core.retrieval.where(request, principal)
        eligible = self.core.db.rows("SELECT m.* FROM memories m WHERE " + where, args)  # noqa: S608
        self.ingest(eligible)
        allowed = {row["id"]: row for row in eligible}
        if not allowed or not request.query.strip():
            rows = (
                eligible[request.offset : request.offset + request.limit] if not request.query.strip() else []
            )
            for row in rows:
                row["source_event_ids"] = json.loads(row["source_event_ids"])
                row["risks"] = json.loads(row["risks"])
            return {"items": rows, "engine": "mem0", "abstain": not rows}
        result = self.engine.search(
            request.query,
            top_k=100,
            filters={"user_id": principal.tenant, "canonical_id": {"in": list(allowed)}},
            rerank=False,
        )
        rows = []
        seen = set()
        for match in result.get("results", []):
            identity = match.get("metadata", {}).get("canonical_id")
            if identity in allowed and identity not in seen and float(match.get("score", 0)) >= 0.35:
                seen.add(identity)
                row = allowed[identity].copy()
                row["source_event_ids"] = json.loads(row["source_event_ids"])
                row["risks"] = json.loads(row["risks"])
                row["score"] = match.get("score")
                metadata = match.get("metadata", {})
                if "start_char" in metadata and "end_char" in metadata:
                    start, end = metadata["start_char"], metadata["end_char"]
                    row["match"] = {"start_char": start, "end_char": end, "text": row["value"][start:end]}
                rows.append(row)
        rows = rows[request.offset : request.offset + request.limit]
        return {"items": rows, "engine": "mem0", "abstain": not rows}

    def delete(self, identity):
        for mid in self.mapping.pop(identity, []):
            self.engine.delete(mid)
        return {"id": identity, "acknowledged": True}

    def invalidate(self, identity):
        return self.delete(identity)

    def reindex(self, principal):
        require(principal, "admin")
        for identity in list(self.mapping):
            self.delete(identity)
        return self.ingest(
            self.core.db.rows(
                "SELECT * FROM memories WHERE status='active' AND tenant=?", (principal.tenant,)
            )
        )

    def recover(self, principal):
        return self.reindex(principal)

    def close(self):
        self.client.close()
        self.engine.db.close()

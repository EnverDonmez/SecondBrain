"""Read selected upstream implementation and design evidence at recorded revisions."""

import concurrent.futures
import json

from collect_deep_sources import fetch_file
from collect_sources import ROOT


TARGETS = {
    "NevaMind-AI/memU": ["docs/developer.md", "docs/sqlite.md", "docs/adr/0007-three-independent-memory-lines-wiki-graph.md", "docs/adr/0010-multi-host-adapters.md", "docs/adr/0015-bridging-must-not-mine-its-own-run.md", "src/memu/app/service.py", "src/memu/embedding/defaults.py", "src/memu/database/sqlite/repositories/recall_file_segment_repo.py"],
    "volcengine/OpenViking": ["docs/en/concepts/03-context-layers.md", "docs/en/api/06-retrieval.md", "docs/en/concepts/04-context-extraction.md", "docs/en/concepts/05-retrieval.md"],
    "basicmachines-co/basic-memory": ["src/basic_memory/mcp/tools/build_context.py", "src/basic_memory/services/context_service.py", "src/basic_memory/man/man3/build-context(3).md"],
    "RamaAditya49/titen": ["src/core/retrieval.ts", "src/core/tokens.ts", "docs/architecture/memory-model.md", "docs/architecture/memory-lifecycle.md", "docs/reference/audit.md", "docs/testing/2026-08-07-pooled-store.md"],
    "samrusani/AliceMemory": ["docs/alpha/known-limitations.md", "docs/alpha/mcp-tools.md", "docs/benchmarks/longmemeval/README.md", "apps/api/src/alicebot_api/continuity_recall.py", "apps/api/src/alicebot_api/sqlite_store.py"],
    "rohitg00/agentmemory": [".env.example", "docs/reliability/state-storage.md", "benchmark/LONGMEMEVAL.md", "src/functions/auto-forget.ts", "src/functions/retention.ts", "CHANGELOG.md"],
    "modelcontextprotocol/servers": ["src/memory/README.md", "src/memory/index.ts"],
    "OSU-NLP-Group/HippoRAG": ["src/hipporag/HippoRAG.py", "src/hipporag/rerank.py"],
    "VectifyAI/PageIndex": ["pageindex/client.py", "pageindex/config.yaml"],
    "mem0ai/mem0": ["mem0/memory/main.py", "mem0/memory/graph_memory.py"],
    "doobidoo/mcp-memory-service": ["docs/architecture.md", "docs/consolidation.md", "src/mcp_memory_service/consolidation/decay.py"],
    "MemTensor/MemOS": ["apps/memos-local-plugin/README.md", "apps/memos-local-plugin/ARCHITECTURE.md"],
    "supermemoryai/supermemory": ["packages/server/README.md", "packages/server/LICENSE", "LICENSE.md"],
    "MemPalace/mempalace": ["mempalace/backends/base.py", "docs/ARCHITECTURE.md"],
}


def main():
    ledger = json.loads((ROOT / "source-ledger.json").read_text("utf-8"))
    tasks = []
    for repo, paths in TARGETS.items():
        metadata = next(row for row in ledger["repositories"] if row.get("repo", "").lower() == repo.lower())
        revision = metadata.get("commit", metadata["default_branch"])
        tasks += [(repo, revision, path) for path in paths]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        result = list(pool.map(lambda task: fetch_file(*task), tasks))
    (ROOT / "implementation-ledger.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in result:
        print(json.dumps({key: row.get(key) for key in ["repo", "path", "status", "bytes", "error"]}))


if __name__ == "__main__":
    main()

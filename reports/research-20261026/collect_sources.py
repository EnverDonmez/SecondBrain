"""Public source snapshots for research. Does not install or execute upstream code."""

import concurrent.futures
import hashlib
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPOS = [
    "NevaMind-AI/memU", "volcengine/OpenViking", "basicmachines-co/basic-memory",
    "doobidoo/mcp-memory-service", "samrusani/AliceMemory", "RamaAditya49/titen",
    "rohitg00/agentmemory", "modelcontextprotocol/servers", "mem0ai/mem0",
    "getzep/graphiti", "vectorize-io/hindsight", "MemTensor/MemOS", "topoteretes/cognee",
    "letta-ai/letta", "memvid/memvid", "supermemoryai/supermemory",
    "OSU-NLP-Group/HippoRAG", "VectifyAI/PageIndex", "parthsarthi03/raptor",
    "HKUDS/LightRAG", "langchain-ai/langmem", "MemoriLabs/Memori",
    "MemPalace/MemPalace", "thedotmack/claude-mem", "alexgarcia/sqlite-vec",
    "networkx/networkx", "kuzudb/kuzu", "ladybugdb/ladybug", "unum-cloud/usearch",
    "xiaowu0162/LongMemEval", "snap-research/locomo", "agiresearch/A-mem",
    "Cipher208/a-memory", "openagenthq/localmem-mcp",
]
DEEP = set(REPOS[:8] + ["getzep/graphiti", "OSU-NLP-Group/HippoRAG", "VectifyAI/PageIndex", "alexgarcia/sqlite-vec"])


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "SecondBrain-OpenSource-Research", "Accept": "application/vnd.github+json" if "api.github.com" in url else "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read(1_000_001)
            return {"url": response.url, "status": response.status, "content": data[:1_000_000], "truncated": len(data) > 1_000_000}
    except (urllib.error.URLError, TimeoutError) as error:
        return {"url": url, "status": getattr(error, "code", None), "error": str(error)}


def collect(repo):
    directory = ROOT / "sources" / repo.replace("/", "--")
    directory.mkdir(parents=True, exist_ok=True)
    response = get("https://api.github.com/repos/" + repo)
    if "content" not in response:
        return {"requested_repo": repo, **response}
    metadata = json.loads(response["content"])
    canonical = metadata["full_name"]
    result = {"requested_repo": repo, "repo": canonical, "url": metadata["html_url"], "default_branch": metadata["default_branch"], "archived": metadata["archived"], "pushed_at": metadata["pushed_at"], "created_at": metadata["created_at"], "license_metadata": metadata.get("license"), "files": []}
    (directory / "repository.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    revision = metadata["default_branch"]
    if repo in DEEP:
        commit = get("https://api.github.com/repos/" + canonical + "/commits/" + revision)
        if "content" in commit:
            details = json.loads(commit["content"])
            revision = details["sha"]
            result["commit"] = revision
            result["commit_date"] = details["commit"]["committer"]["date"]
    for name in ["README.md", "LICENSE", "LICENSE.txt", "LICENSE.md", "pyproject.toml", "package.json"]:
        source = get("https://raw.githubusercontent.com/" + canonical + "/" + revision + "/" + name)
        if "content" not in source:
            continue
        data = source.pop("content")
        target = directory / (name.replace("/", "__") + ".txt")
        target.write_bytes(data)
        result["files"].append({**source, "path": name, "local_path": str(target.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return result


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        repositories = list(pool.map(collect, REPOS))
    result = {"checked_at": datetime.now(UTC).isoformat(), "method": "Public GitHub repository metadata and raw source files; code not executed", "repositories": repositories}
    (ROOT / "source-ledger.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in repositories:
        print(json.dumps({key: row.get(key) for key in ["repo", "requested_repo", "archived", "pushed_at", "commit", "license_metadata", "error"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

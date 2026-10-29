"""Fetch public upstream evidence only; never reads or uploads brain data."""

import concurrent.futures
import hashlib
import importlib.metadata
import json
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPOS = {
    "Hindsight": "vectorize-io/hindsight",
    "Mem0": "mem0ai/mem0",
    "Supermemory": "supermemoryai/supermemory",
    "MemOS": "MemTensor/MemOS",
    "memU": "NevaMind-AI/memU",
    "LangMem": "langchain-ai/langmem",
    "Letta": "letta-ai/letta",
    "MIRIX": "Mirix-AI/MIRIX",
    "Honcho": "plastic-labs/honcho",
    "Memori": "MemoriLabs/Memori",
    "OmniMem": "richarvey/OmniMem",
    "MemPalace": "MemPalace/mempalace",
    "Graphiti": "getzep/graphiti",
    "Cognee": "topoteretes/cognee",
    "GraphRAG": "microsoft/graphrag",
    "LightRAG": "HKUDS/LightRAG",
    "HippoRAG": "OSU-NLP-Group/HippoRAG",
    "A-MEM": "agiresearch/A-mem",
    "KAG": "OpenSPG/KAG",
    "EverOS": "EverMind-AI/EverOS",
    "ReMe": "agentscope-ai/ReMe",
    "Basic Memory": "basicmachines-co/basic-memory",
    "OpenViking": "volcengine/OpenViking",
    "Memvid": "memvid/memvid",
    "Claude-Mem": "thedotmack/claude-mem",
    "Agent Skills": "agentskills/agentskills",
    "rank-bm25": "dorianbrown/rank_bm25",
    "FastEmbed": "qdrant/fastembed",
    "MCP Python SDK": "modelcontextprotocol/python-sdk",
    "FastAPI": "fastapi/fastapi",
    "Uvicorn": "Kludex/uvicorn",
    "Codex": "openai/codex",
    "Reflexion": "noahshinn/reflexion",
    "ExpeL": "LeapLabTHU/ExpeL",
    "Voyager": "MineDojo/Voyager",
    "TencentDB Agent Memory": "TencentCloud/TencentDB-Agent-Memory",
    "RapidOCR": "RapidAI/RapidOCR",
    "faster-whisper": "SYSTRAN/faster-whisper",
    "PyAV": "PyAV-Org/PyAV",
    "pypdfium2": "pypdfium2-team/pypdfium2",
}


def fetch(url):
    if not url.startswith(
        ("https://api.github.com/", "https://raw.githubusercontent.com/", "https://github.com/")
    ):
        raise ValueError("Source audit URLs must use an approved HTTPS upstream")
    request = urllib.request.Request(  # noqa: S310 -- HTTPS allowlist checked above
        url, headers={"User-Agent": "SecondBrainOS-source-audit/0.1", "Accept": "application/vnd.github+json"}
    )  # noqa: S310
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
        return response.read(3_000_000)


def inspect(item):
    name, repo = item
    row = {
        "name": name,
        "repository": "https://github.com/" + repo,
        "status": "research_candidate",
        "used": name
        in {
            "Mem0",
            "rank-bm25",
            "FastEmbed",
            "MCP Python SDK",
            "FastAPI",
            "Uvicorn",
            "RapidOCR",
            "faster-whisper",
            "PyAV",
            "pypdfium2",
        },
    }
    folder = Path("third_party/upstream") / repo.replace("/", "--")
    folder.mkdir(parents=True, exist_ok=True)
    try:
        commit = json.loads(fetch(f"https://api.github.com/repos/{repo}/commits/HEAD"))
        sha = commit["sha"]
        row.update(commit=sha, commit_date=commit["commit"]["committer"]["date"])
        for filename in ["LICENSE", "README.md"]:
            try:
                content = fetch(f"https://raw.githubusercontent.com/{repo}/{sha}/{filename}")
                (folder / filename).write_bytes(content)
                row[filename + "_sha256"] = hashlib.sha256(content).hexdigest()
            except (urllib.error.URLError, TimeoutError):
                row[filename + "_status"] = "unavailable_at_expected_path"
        try:
            releases = fetch(f"https://github.com/{repo}/releases.atom").decode()
            (folder / "releases.atom").write_text(releases, encoding="utf-8")
            row["recent_release_refs"] = re.findall(
                r"<id>tag:github.com,2008:Repository/\d+/(.*?)</id>", releases
            )[:5]
        except (urllib.error.URLError, TimeoutError):
            row["release_status"] = "unavailable"
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
        row.update(status="identity_or_network_unverified", error=type(exc).__name__)
    return row


def installed():
    rows = []
    folder = Path("third_party/licenses")
    folder.mkdir(parents=True, exist_ok=True)
    for dist in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].casefold()):
        row = {
            "name": dist.metadata["Name"],
            "version": dist.version,
            "license_expression": dist.metadata.get("License-Expression"),
            "license_metadata": dist.metadata.get("License"),
            "project_urls": dist.metadata.get_all("Project-URL"),
            "requires": dist.requires or [],
            "license_files": [],
        }
        for file in dist.files or []:
            if ".dist-info/" in str(file) and any(
                s in str(file).upper() for s in ["LICENSE", "COPYING", "NOTICE"]
            ):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    path_id = hashlib.sha256(str(file).encode()).hexdigest()[:12]
                    target = folder / (row["name"] + "--" + path_id + "--" + source.name)
                    target.write_bytes(source.read_bytes())
                    row["license_files"].append(
                        {
                            "path": str(target),
                            "installed_path": str(file),
                            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        }
                    )
        rows.append(row)
    return rows


def repair_license(row):
    if "LICENSE_sha256" in row or not row.get("commit"):
        return row
    repo = row["repository"].removeprefix("https://github.com/")
    for filename in ["LICENSE.md", "LICENSE.txt", "COPYING"]:
        try:
            content = fetch(f"https://raw.githubusercontent.com/{repo}/{row['commit']}/{filename}")
            folder = Path("third_party/upstream") / repo.replace("/", "--")
            (folder / "LICENSE").write_bytes(content)
            row.update(LICENSE_sha256=hashlib.sha256(content).hexdigest(), license_source_filename=filename)
            row.pop("LICENSE_status", None)
            break
        except (urllib.error.URLError, TimeoutError):
            continue
    return row


def main():
    existing_path = Path("reports/source-registry.json")
    previous = json.loads(existing_path.read_text("utf-8")) if existing_path.exists() else {"candidates": []}
    retained = {
        row["name"]: row
        for row in previous["candidates"]
        if row.get("commit") and row["repository"] == "https://github.com/" + REPOS.get(row["name"], "")
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        fresh = list(
            pool.map(inspect, [(name, repo) for name, repo in REPOS.items() if name not in retained])
        )
    candidates = [repair_license(row) for row in list(retained.values()) + fresh]
    payload = {
        "checked_at": datetime.now(UTC).isoformat(),
        "note": "HEAD snapshots are research evidence, not the installed package revision. Installed wheels are separately version locked. Missing repository identities are not silently substituted.",
        "candidates": candidates,
        "installed_packages": installed(),
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/source-registry.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "candidates": len(candidates),
                "snapshots": sum("commit" in c for c in candidates),
                "packages": len(payload["installed_packages"]),
            }
        )
    )


if __name__ == "__main__":
    main()

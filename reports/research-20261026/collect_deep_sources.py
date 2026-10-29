"""Extend the read-only evidence inventory with source trees and selected files."""

import concurrent.futures
import hashlib
import json

from collect_sources import ROOT, collect, get


def fetch_file(repo, revision, path):
    response = get("https://raw.githubusercontent.com/" + repo + "/" + revision + "/" + path)
    if "content" not in response:
        return {"repo": repo, "revision": revision, "path": path, **response}
    content = response.pop("content")
    local = ROOT / "sources" / repo.replace("/", "--") / (path.replace("/", "__") + ".txt")
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(content)
    return {"repo": repo, "revision": revision, "path": path, "local_path": str(local.relative_to(ROOT)), "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content), **response}


def main():
    ledger = json.loads((ROOT / "source-ledger.json").read_text("utf-8"))
    known = {row["requested_repo"] for row in ledger["repositories"]}
    for repo in ["asg017/sqlite-vec", "microsoft/graphrag", "xiaowu0162/LongMemEval-V2"]:
        if repo not in known:
            ledger["repositories"].append(collect(repo))
    (ROOT / "source-ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    trees = []
    for repo in ["NevaMind-AI/memU", "RamaAditya49/titen", "basicmachines-co/basic-memory", "samrusani/AliceMemory", "rohitg00/agentmemory"]:
        row = next(row for row in ledger["repositories"] if row.get("repo", "").lower() == repo.lower())
        revision = row.get("commit", row["default_branch"])
        response = get("https://api.github.com/repos/" + repo + "/git/trees/" + revision + "?recursive=1")
        if "content" not in response:
            trees.append({"repo": repo, **response})
            continue
        if response["truncated"]:
            trees.append({"repo": repo, "error": "Response exceeded snapshot limit"})
            continue
        tree = json.loads(response["content"])
        paths = [entry["path"] for entry in tree.get("tree", []) if entry["type"] == "blob"]
        target = ROOT / "sources" / repo.replace("/", "--") / "tree-paths.json"
        target.write_text(json.dumps(paths, indent=2), encoding="utf-8")
        trees.append({"repo": repo, "revision": revision, "files": len(paths), "truncated": tree.get("truncated", False)})
    (ROOT / "tree-ledger.json").write_text(json.dumps(trees, indent=2), encoding="utf-8")
    print(json.dumps(trees, indent=2))


if __name__ == "__main__":
    main()

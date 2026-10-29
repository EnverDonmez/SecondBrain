"""Public release hashes for pinned installed packages; no application data access."""

import concurrent.futures
import importlib.metadata
import json
import urllib.request
from pathlib import Path


def evidence(distribution):
    name, version = distribution.metadata["Name"], distribution.version
    if name == "second-brain-os":
        return None
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310 -- fixed HTTPS PyPI hostname
            release = json.load(response)
        return {
            "name": name,
            "version": version,
            "release_url": f"https://pypi.org/project/{name}/{version}/",
            "artifacts": [
                {
                    "filename": item["filename"],
                    "sha256": item["digests"]["sha256"],
                    "url": item["url"],
                    "yanked": item.get("yanked", False),
                }
                for item in release["urls"]
            ],
        }
    except Exception as exc:
        return {"name": name, "version": version, "verification": "unavailable", "error": type(exc).__name__}


with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    results = [row for row in pool.map(evidence, importlib.metadata.distributions()) if row]
Path("reports/package-release-hashes.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps({"packages": len(results), "verified_releases": sum("artifacts" in row for row in results)}))

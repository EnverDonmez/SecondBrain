"""Pinned public model cards; no model weights or private media are sent."""

import hashlib
import json
import urllib.request
from pathlib import Path

models = [
    ("embedding", "Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q", "data/models/ready.json"),
    ("speech", "Systran/faster-whisper-tiny", "data/models/speech/ready.json"),
]
report = []
for name, repository, marker in models:
    manifest = json.loads(Path(marker).read_text("utf-8"))
    revision = manifest.get("revision") or Path(manifest["snapshot"]).name
    url = f"https://huggingface.co/{repository}/raw/{revision}/README.md"
    folder = Path("third_party/models") / name
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310 -- fixed public HTTPS model repositories
            content = response.read(1_000_000)
        (folder / "README.md").write_bytes(content)
        report.append(
            {
                "model": repository,
                "revision": revision,
                "card_url": url,
                "card_sha256": hashlib.sha256(content).hexdigest(),
                "status": "retrieved",
            }
        )
    except Exception as exc:
        report.append(
            {"model": repository, "revision": revision, "status": "unavailable", "error": type(exc).__name__}
        )
Path("reports/model-source-evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))

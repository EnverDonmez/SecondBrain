"""Package source, tests and public evidence. Never include the user's brain or credentials."""

import hashlib
import json
import zipfile
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parent.parent
version = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]["version"]
target = root / "dist"
target.mkdir(exist_ok=True)
files = [
    p
    for p in root.iterdir()
    if p.is_file()
    and (
        p.suffix in {".md", ".toml", ".lock", ".cmd"}
        or p.name
        in {"LICENSE", "NOTICE", "Dockerfile", "compose.yaml", ".gitignore", ".dockerignore", ".env.example"}
    )
]
for directory in ["second_brain", "tests", "scripts", "docs", "integrations", ".github", "third_party"]:
    folder = root / directory
    if folder.exists():
        files += [
            p
            for p in folder.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        ]
files += [
    p
    for p in (root / "reports").rglob("*")
    if p.is_file()
    and p.suffix in {".json", ".md", ".xml", ".png"}
    and not any(part.startswith("local-") for part in p.relative_to(root).parts)
]
archive_path = target / f"second-brain-os-{version}-source.zip"
manifest = []
with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(set(files)):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Source package cannot follow links outside the workspace")
        name = path.relative_to(root).as_posix()
        if path.name == ".env" or path.suffix.casefold() in {
            ".token",
            ".key",
            ".log",
            ".db",
            ".sqlite",
            ".sqlite3",
            ".enc",
            ".sbbackup",
        }:
            raise ValueError("Private runtime file encountered in source package")
        content = path.read_bytes()
        archive.writestr("second-brain-os/" + name, content)
        manifest.append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
    archive.writestr("second-brain-os/SOURCE_MANIFEST.json", json.dumps(manifest, indent=2))
report = {
    "path": archive_path.name,
    "version": version,
    "channel": "beta",
    "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    "bytes": archive_path.stat().st_size,
    "files": len(manifest),
    "contains_user_data": False,
    "contains_models_or_dependencies": False,
}
wheel_path = target / f"second_brain_os-{version}-py3-none-any.whl"
if wheel_path.exists():
    report["wheel"] = {
        "path": wheel_path.name,
        "sha256": hashlib.sha256(wheel_path.read_bytes()).hexdigest(),
        "bytes": wheel_path.stat().st_size,
    }
(target / "release-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))

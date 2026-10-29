"""Verify the installed wheel target, rather than accidentally importing editable source."""

import json
import hashlib
import sys
import tempfile
import tomllib
import importlib.metadata
from pathlib import Path

root = Path(__file__).resolve().parent.parent
expected_version = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]["version"]
target = (root / f".test-tmp/wheel-install-{expected_version}").resolve()
sys.path.insert(0, str(target))
import second_brain  # noqa: E402 -- deliberately choose the installed wheel first
from second_brain.core import Brain  # noqa: E402

package = Path(second_brain.__file__).resolve().parent
assert package.is_relative_to(target)
assert second_brain.__version__ == expected_version == importlib.metadata.version("second-brain-os")
assert (package / "preferences.py").is_file()
source = root / "second_brain"
checked = 0
for path in source.rglob("*"):
    if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    installed = package / path.relative_to(source)
    assert installed.is_file(), f"Missing wheel member: {path.relative_to(source)}"
    assert hashlib.sha256(installed.read_bytes()).digest() == hashlib.sha256(path.read_bytes()).digest(), (
        f"Stale wheel member: {path.relative_to(source)}"
    )
    checked += 1
for name in ["index.html", "app.js", "style.css", "api-docs.html", "docs.js"]:
    assert (package / "static" / name).is_file()
with tempfile.TemporaryDirectory(dir=root / ".test-tmp") as temporary:
    brain = Brain(Path(temporary) / "brain")
    expected_schema = len(list((source / "migrations").glob("*.sql")))
    assert brain.db.one("PRAGMA user_version")["user_version"] == expected_schema
    assert brain.db.one("PRAGMA quick_check")["quick_check"] == "ok"
result = {
    "installed_wheel_import": True,
    "version": expected_version,
    "static_assets_present": True,
    "fresh_migration_schema": expected_schema,
    "source_files_verified": checked,
    "database_integrity": "ok",
}
(root / "reports/wheel-check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))

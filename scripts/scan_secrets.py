"""Conservative source-only scan. Never opens runtime data or prints matched values."""

import json
import re
from pathlib import Path

patterns = [
    re.compile(r"sk-[A-Za-z0-9_-]{24,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
excluded = {
    ".venv",
    "data",
    ".test-tmp",
    "third_party",
    ".git",
    ".hypothesis",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
}
findings = []
for path in Path.cwd().rglob("*"):
    if (
        not path.is_file()
        or any(part in excluded for part in path.parts)
        or path.suffix.lower() not in {".py", ".js", ".json", ".toml", ".yaml", ".yml", ".md", ".ps1"}
    ):
        continue
    # These explicit synthetic strings exercise the detector/quarantine itself.
    if path.relative_to(Path.cwd()).as_posix() == "tests/test_core.py":
        continue
    for line_number, line in enumerate(path.read_text("utf-8", errors="replace").splitlines(), 1):
        if any(pattern.search(line) for pattern in patterns):
            findings.append({"path": str(path.relative_to(Path.cwd())), "line": line_number})
report = {
    "findings": findings,
    "scope": "source files only; runtime data and upstream snapshots excluded",
    "limitations": "Pattern scan is not a comprehensive credential detector; the synthetic quarantine test file is excluded",
}
Path("reports").mkdir(exist_ok=True)
Path("reports/secret-scan.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"findings": len(findings)}))
raise SystemExit(1 if findings else 0)

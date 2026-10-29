"""Record the verified environment without local paths or editable source references."""

import importlib.metadata
from pathlib import Path

rows = []
for distribution in importlib.metadata.distributions():
    name = distribution.metadata["Name"]
    if name.casefold() in {"pip", "second-brain-os"}:
        continue
    marker = '; sys_platform == "win32"' if name.casefold() == "pywin32" else ""
    rows.append(name + "==" + distribution.version + marker)
Path("requirements.lock").write_text("\n".join(sorted(rows, key=str.casefold)) + "\n", encoding="utf-8")
print(f"Recorded {len(rows)} version pins; local application installed separately")

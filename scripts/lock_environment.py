"""Refresh the approved PyPI wheel hashes for the project's pinned releases."""

import argparse
import importlib.metadata
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]


def approved_wheels(pin):
    name, version = pin.partition(";")[0].strip().split("==", 1)
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    url = f"https://pypi.org/pypi/{quote(normalized, safe='')}/{quote(version, safe='')}/json"
    with urlopen(url, timeout=15) as stream:  # noqa: S310 -- fixed HTTPS PyPI host
        release = json.load(stream)
    hashes = sorted(
        {
            item["digests"]["sha256"]
            for item in release["urls"]
            if item["filename"].endswith(".whl") and not item["yanked"]
        }
    )
    if not hashes:
        raise ValueError(f"{name}=={version} has no approved wheels")
    return normalized, {"version": version, "sha256": hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-installed", action="store_true", help="Replace pins with the active environment"
    )
    args = parser.parse_args()
    pin_path = ROOT / "requirements.lock"
    pins = [line for line in pin_path.read_text("utf-8").splitlines() if line.strip()]
    if args.from_installed:
        pins = []
        for distribution in importlib.metadata.distributions():
            name = distribution.metadata["Name"]
            if name.casefold() == "second-brain-os":
                continue
            marker = '; sys_platform == "win32"' if name.casefold() == "pywin32" else ""
            pins.append(name + "==" + distribution.version + marker)
        pins.sort(key=str.casefold)
    with ThreadPoolExecutor(max_workers=12) as executor:
        lock = dict(executor.map(approved_wheels, pins))
    rows = [
        json.dumps(name) + ": " + json.dumps(data, separators=(",", ":"))
        for name, data in sorted(lock.items())
    ]
    (ROOT / "requirements.hashes.json").write_text(
        "{\n  " + ",\n  ".join(rows) + "\n}\n", encoding="utf-8", newline="\n"
    )
    if args.from_installed:
        pin_path.write_text("\n".join(pins) + "\n", encoding="utf-8", newline="\n")
    print(f"Recorded approved wheels for {len(lock)} releases.")


if __name__ == "__main__":
    main()

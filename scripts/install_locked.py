"""Resolve the chosen extras, verify every wheel, then install the local project."""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


def verified_requirements(report, lock):
    for item in report["install"]:
        name = re.sub(r"[-_.]+", "-", item["metadata"]["name"]).lower()
        version = item["metadata"]["version"]
        archive = item["download_info"]
        digest = archive.get("archive_info", {}).get("hashes", {}).get("sha256")
        approved = lock.get(name, {})
        if (
            approved.get("version") != version
            or not digest
            or digest not in approved.get("sha256", [])
            or not urlsplit(archive["url"]).path.endswith(".whl")
        ):
            raise ValueError(f"No approved wheel for {name}=={version}")
        yield f"{name}=={version} --hash=sha256:{digest}"


def pip(*args):
    subprocess.run(  # noqa: S603 -- fixed interpreter and pip argument vector
        [sys.executable, "-m", "pip", "--disable-pip-version-check", *args], check=True, cwd=ROOT
    )


def main():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))
    extras = project["project"]["optional-dependencies"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extra", choices=sorted(extras), action="append", default=[])
    parser.add_argument("--editable", action="store_true")
    parser.add_argument("--verify-only", action="store_true", help="Resolve and verify without installing")
    args = parser.parse_args()
    required = project["build-system"]["requires"] + project["project"]["dependencies"]
    for extra in args.extra:
        required.extend(extras[extra])
    lock = json.loads((ROOT / "requirements.hashes.json").read_text("utf-8"))
    with tempfile.TemporaryDirectory() as temp:
        report, selection = Path(temp) / "report.json", Path(temp) / "requirements.txt"
        pip(
            "install",
            "--dry-run",
            "--ignore-installed",
            "--only-binary=:all:",
            "--report",
            str(report),
            "-c",
            str(ROOT / "requirements.lock"),
            *required,
        )
        selected = list(verified_requirements(json.loads(report.read_text("utf-8")), lock))
        if not selected:
            raise ValueError("Empty dependency resolution")
        selection.write_text("\n".join(selected) + "\n", encoding="ascii")
        if not args.verify_only:
            pip(
                "install",
                "--require-hashes",
                "--only-binary=:all:",
                "--no-deps",
                "--force-reinstall",
                "-r",
                str(selection),
            )
            pip("install", "--no-deps", "--no-build-isolation", *(["-e"] if args.editable else []), str(ROOT))
    print(f"Verified {len(selected)} locked wheel archives.")


if __name__ == "__main__":
    main()

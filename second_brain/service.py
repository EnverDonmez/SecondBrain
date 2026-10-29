"""Local service lifecycle shared by the launcher and opt-in MCP autostart."""

import hashlib
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

from . import __version__


def instance_id(root):
    canonical = os.path.normcase(str(Path(root).resolve()))
    return hashlib.sha256(canonical.encode()).hexdigest()[:24]


def service_health(port):
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    try:
        with httpx.Client(trust_env=False, timeout=1.5) as client:
            response = client.get(f"http://127.0.0.1:{port}/healthz")
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return None
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Port {port} is occupied but the local service did not respond") from exc
    try:
        health = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Port {port} belongs to another application") from exc
    if response.status_code != 200 or not isinstance(health, dict):
        raise RuntimeError(f"Port {port} did not return a healthy Second Brain service")
    if health.get("application") != "second-brain-os":
        raise RuntimeError(f"Port {port} belongs to another application")
    return health


def validate_service(health, root):
    if health.get("instance_id") != instance_id(root):
        raise RuntimeError(
            "This port serves another data directory or an older service. Check it before restarting."
        )
    if health.get("version") != __version__:
        raise RuntimeError("The running service has another version. Restart it before continuing.")


def ensure_service(root, port=8765, timeout=20):
    """Start only when offline; never replace a process or reuse another brain."""
    root = Path(root).resolve()
    health = service_health(port)
    if health:
        validate_service(health, root)
        return {"started": False, "url": f"http://127.0.0.1:{port}", "health": health}
    # A silent listener must never cause initialization of a second brain.
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(
                f"Port {port} is unavailable. Check the existing process or choose another port."
            ) from exc
    root.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    with (root / "server.stdout.log").open("ab") as stdout, (root / "server.stderr.log").open("ab") as stderr:
        process = subprocess.Popen(  # noqa: S603 -- fixed interpreter/module arguments, no shell
            [sys.executable, "-m", "second_brain", "--data", str(root), "serve", "--port", str(port)],
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            env=environment,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            start_new_session=os.name != "nt",
        )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        health = service_health(port)
        if health:
            validate_service(health, root)
            return {
                "started": True,
                "pid": health.get("pid", process.pid),
                "url": f"http://127.0.0.1:{port}",
                "health": health,
            }
        # A concurrent launcher may have acquired the single-writer lock. Its
        # process can still be migrating/starting when this child exits.
        process.poll()
        time.sleep(0.15)
    raise RuntimeError(
        f"Service is not ready after {timeout}s (child exit: {process.poll()}). Inspect {root / 'server.stderr.log'}"
    )


@contextmanager
def service_lock(root):
    """Hold one writer for the entire process lifetime, including error paths."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / "service.lock").open("a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"1")
            lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
        except OSError as exc:
            raise RuntimeError("Another service owns this data directory") from exc
        yield

"""One serialized, offline embedding worker; release model RAM after idle time."""

import atexit
import json
import os
import queue
import subprocess
import sys
import threading
from io import TextIOWrapper
from pathlib import Path
from typing import cast

from .security import Denied


class SemanticWorker:
    def __init__(self, idle_seconds=None):
        self.idle_seconds = max(
            0,
            min(
                3600,
                float(
                    os.environ.get("SB_SEMANTIC_IDLE_SECONDS", "30") if idle_seconds is None else idle_seconds
                ),
            ),
        )
        self.lock = threading.RLock()
        self.process = None
        self.timer = None
        self.key = None
        self.last_usage = None
        self.generation = 0

    def close(self):
        with self.lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None
            process, self.process = self.process, None
            self.generation += 1
            if process:
                if process.poll() is None:
                    # Let the interpreter exit itself: on Windows a venv launcher
                    # can have a different PID from its Python worker child.
                    try:
                        if process.stdin:
                            process.stdin.write('{"shutdown":true}\n')
                            process.stdin.flush()
                            process.stdin.close()
                    except OSError:
                        pass
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.kill()
                        process.wait(timeout=5)
                for stream in (process.stdin, process.stdout):
                    if stream:
                        stream.close()

    def status(self):
        with self.lock:
            running = self.process is not None and self.process.poll() is None
            return {
                "running": running,
                "pid": self.process.pid if running and self.process is not None else None,
                "idle_seconds": self.idle_seconds,
                "last_usage": self.last_usage,
            }

    def embed(self, directory, model, texts):
        if not texts:
            return []
        return self.request(directory, model, {"texts": texts})["vectors"]

    def request(self, directory, model, payload):
        with self.lock:
            if self.timer:
                self.timer.cancel()
            key = (directory, model)
            if self.key != key or self.process is None or self.process.poll() is not None:
                self.close()
                self.key = key
                self.responses: queue.Queue = queue.Queue(maxsize=1)
                self.process = subprocess.Popen(  # noqa: S603 -- fixed module, no shell
                    [sys.executable, "-m", "second_brain.semantic_runtime", directory, model],
                    cwd=Path(__file__).resolve().parents[1],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                process, responses = self.process, self.responses

                def read():
                    try:
                        assert process.stdout is not None
                        for line in process.stdout:
                            responses.put(json.loads(line))
                    except (ValueError, OSError):
                        pass
                    finally:
                        try:
                            responses.put_nowait(None)
                        except queue.Full:
                            pass

                threading.Thread(target=read, daemon=True, name="semantic-reader").start()
            try:
                assert self.process is not None and self.process.stdin is not None
                self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self.process.stdin.flush()
                response = self.responses.get(timeout=120)
                if not response or not ({"vectors", "chunks"} & response.keys()):
                    raise Denied("Local embedding worker failed; check the pinned model installation")
                self.last_usage = response["usage"]
                return response
            except (OSError, queue.Empty) as exc:
                self.close()
                raise Denied("Local embedding worker is unavailable") from exc
            finally:
                self.generation += 1
                generation = self.generation

                def expire():
                    with self.lock:
                        if self.generation == generation:
                            self.close()

                self.timer = threading.Timer(self.idle_seconds, expire)
                self.timer.daemon = True
                self.timer.start()


semantic_worker = SemanticWorker()
atexit.register(semantic_worker.close)


def main():
    from .providers import local_model
    from .runtime import process_usage

    cast(TextIOWrapper, sys.stdin).reconfigure(encoding="utf-8")
    cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
    engine = local_model(sys.argv[1], sys.argv[2])
    for line in sys.stdin:
        request = json.loads(line)
        if request.get("shutdown"):
            break
        if "chunk" in request:
            # This worker handles one request at a time. Temporarily reuse the
            # inference tokenizer, restoring its settings before any inference.
            tokenizer = engine.model.tokenizer
            truncation, padding = tokenizer.truncation, tokenizer.padding
            tokenizer.no_truncation()
            tokenizer.no_padding()
            value = request["chunk"]
            try:
                encoded = tokenizer.encode(value, add_special_tokens=False)
                prefix = tokenizer.decode(
                    tokenizer.encode(
                        request["subject"] + " " + request["predicate"], add_special_tokens=False
                    ).ids[:20]
                )
            finally:
                if truncation:
                    tokenizer.enable_truncation(**truncation)
                if padding:
                    tokenizer.enable_padding(**padding)
            chunks = []
            for index in range(0, len(encoded.ids), 80):
                offsets = encoded.offsets[index : index + 96]
                start, end = offsets[0][0], offsets[-1][1]
                chunks.append({"start": start, "end": end, "text": prefix + " " + value[start:end]})
            if not chunks:
                chunks = [{"start": 0, "end": len(value), "text": prefix + " " + value}]
            result = {"chunks": chunks}
        else:
            result = {"vectors": [v.tolist() for v in engine.embed(request["texts"], batch_size=16)]}
        print(json.dumps({**result, "usage": process_usage()}), flush=True)


if __name__ == "__main__":
    main()

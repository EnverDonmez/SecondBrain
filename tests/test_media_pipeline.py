"""Real CPU processors with generated media, never personal recordings or remote inference."""

import importlib.util
import io
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from second_brain.models import OWNER
from second_brain.queue import JobCancelled

pytestmark = pytest.mark.skipif(
    not importlib.util.find_spec("rapidocr_onnxruntime") or not importlib.util.find_spec("av"),
    reason="Optional local media extra is not installed",
)


def image_sample():
    image = Image.new("RGB", (1000, 240), "white")
    ImageDraw.Draw(image).text(
        (35, 65), "SECOND BRAIN MEMORY TEST", fill="black", font=ImageFont.load_default(size=42)
    )
    return image


@pytest.mark.parametrize("operation,extension", [("ocr", "PNG"), ("pdf_ocr", "PDF")])
def test_real_ocr_provenance_replay_and_original(brain, operation, extension):
    content = io.BytesIO()
    image_sample().save(content, format=extension)
    brain.importer.submit(content.getvalue(), "sample." + extension.lower(), OWNER)
    brain.process_one()
    asset = brain.db.one("SELECT * FROM assets")
    job = brain.multimodal.enqueue(asset["id"], operation, OWNER)
    brain.process_one()
    assert brain.db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "done"
    memory = brain.db.one("SELECT * FROM memories")
    assert "MEMORYTEST" in memory["value"].replace(" ", "")
    assert memory["trust"] == "untrusted" and memory["status"] == "candidate"
    event = brain.events.get(json.loads(memory["source_event_ids"])[0], OWNER)
    assert event["metadata"]["location"] == ("page:1" if extension == "PDF" else "image")
    assert asset["id"] in event["attachments"]
    assert brain.vault.get(asset["id"]) == content.getvalue()
    brain.queue.retry(job["id"], OWNER)
    brain.process_one()
    assert brain.db.one("SELECT COUNT(*) AS n FROM memories")["n"] == 1
    assert brain.memory.commit(memory["id"], OWNER)["memory_type"] == "EXTERNAL_KNOWLEDGE"
    brain.privacy.forget(memory["id"], OWNER)
    assert not brain.vault.path(asset["id"]).exists()
    assert not brain.db.one("SELECT 1 FROM memories")


def test_real_video_timestamp_and_no_network(brain, tmp_path, monkeypatch):
    import av
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError("Processor tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    video = tmp_path / "sample.mp4"
    with av.open(str(video), "w") as container:
        stream = container.add_stream("mpeg4", rate=1)
        stream.width, stream.height, stream.pix_fmt = 1000, 240, "yuv420p"
        for _ in range(3):
            for packet in stream.encode(av.VideoFrame.from_image(image_sample())):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    brain.importer.submit(video.read_bytes(), "sample.mp4", OWNER)
    brain.process_one()
    asset = brain.db.one("SELECT * FROM assets")
    job = brain.multimodal.enqueue(asset["id"], "video", OWNER)
    brain.process_one()
    assert brain.db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "done"
    event = brain.db.one("SELECT metadata FROM events WHERE source='local-derivative'")
    extraction = json.loads(event["metadata"])["extraction"]
    assert extraction["timestamp"] == 0 and extraction["timestamp_basis"] == "container"
    assert "MEMORYTEST" in "".join(line["text"].replace(" ", "") for line in extraction["ocr"])


@pytest.mark.skipif(not Path("data/models/speech/ready.json").exists(), reason="Local speech weights missing")
def test_real_local_speech_timestamps(brain, monkeypatch):
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError("Local speech runtime attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setenv("SB_MODEL_DIR", str(Path("data/models").resolve()))
    content = Path("tests/fixtures/synthetic_speech.wav").read_bytes()
    brain.importer.submit(content, "synthetic.wav", OWNER)
    brain.process_one()
    asset = brain.db.one("SELECT * FROM assets")
    job = brain.multimodal.enqueue(asset["id"], "transcribe", OWNER, "en")
    brain.process_one()
    assert brain.db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "done"
    rows = brain.db.rows("SELECT * FROM memories ORDER BY predicate")
    assert "second brain" in " ".join(row["value"].lower() for row in rows)
    assert "short clear sentences" in " ".join(row["value"].lower() for row in rows)
    for row in rows:
        assert row["status"] == "candidate" and row["trust"] == "untrusted"
        event = brain.events.get(json.loads(row["source_event_ids"])[0], OWNER)
        segment = event["metadata"]["extraction"]
        assert 0 <= segment["start"] < segment["end"] <= 6.2
        assert segment["timestamp_discontinuities"] == 0
    assert brain.vault.get(asset["id"]) == content


def test_cancel_during_ocr_retains_original_without_new_candidate(brain, monkeypatch):
    import second_brain.multimodal as module

    content = io.BytesIO()
    image_sample().save(content, format="PNG")
    brain.importer.submit(content.getvalue(), "cancel.png", OWNER)
    brain.process_one()
    asset = brain.db.one("SELECT * FROM assets")
    queued = brain.multimodal.enqueue(asset["id"], "ocr", OWNER)

    def cancel_after_inference(image):
        brain.queue.cancel(queued["id"], OWNER)
        return [{"text": "This cancelled text must not be saved", "confidence": 1.0}]

    monkeypatch.setattr(module, "recognize_image", cancel_after_inference)
    brain.process_one()
    assert brain.db.one("SELECT state FROM jobs WHERE id=?", (queued["id"],))["state"] == "cancelled"
    assert not brain.db.one("SELECT 1 FROM memories")
    assert brain.vault.get(asset["id"]) == content.getvalue()
    with pytest.raises(JobCancelled):
        brain.queue.ensure_active(queued["id"])

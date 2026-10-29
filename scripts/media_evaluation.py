"""Real local processors evaluated only with generated text images and synthetic TTS."""

import io
import json
import os
import tempfile
import time
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont

from second_brain.core import Brain
from second_brain.models import OWNER
from second_brain.runtime import process_usage

workspace = Path.cwd()
os.environ["SB_MODEL_DIR"] = str(workspace / "data" / "models")
(workspace / ".test-tmp").mkdir(exist_ok=True)
report = {"data": "generated image/PDF/video and synthetic Windows TTS; no personal media", "processors": {}}
with tempfile.TemporaryDirectory(dir=workspace / ".test-tmp") as temporary:
    root = Path(temporary)
    brain = Brain(root / "brain")
    image = Image.new("RGB", (1000, 240), "white")
    ImageDraw.Draw(image).text(
        (35, 65), "SECOND BRAIN MEMORY TEST", fill="black", font=ImageFont.load_default(size=42)
    )
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    pdf_bytes = io.BytesIO()
    image.save(pdf_bytes, format="PDF")
    video_path = root / "synthetic.mp4"
    with av.open(str(video_path), "w") as container:
        stream = container.add_stream("mpeg4", rate=1)
        stream.width, stream.height, stream.pix_fmt = 1000, 240, "yuv420p"
        for _ in range(3):
            for packet in stream.encode(av.VideoFrame.from_image(image)):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    samples = [
        ("image.png", image_bytes.getvalue(), "ocr"),
        ("scan.pdf", pdf_bytes.getvalue(), "pdf_ocr"),
        ("video.mp4", video_path.read_bytes(), "video"),
    ]
    speech = workspace / "tests" / "fixtures" / "synthetic_speech.wav"
    if speech.exists():
        samples.append(("speech.wav", speech.read_bytes(), "transcribe"))
    for filename, content, operation in samples:
        started = time.perf_counter()
        imported = brain.importer.submit(content, filename, OWNER)
        brain.process_one()
        asset = brain.db.one("SELECT id FROM assets WHERE name=?", (filename,))
        job = brain.multimodal.enqueue(
            asset["id"], operation, OWNER, "en" if operation == "transcribe" else None
        )
        brain.process_one()
        state = brain.db.one("SELECT state,error,result FROM jobs WHERE id=?", (job["id"],))
        rows = brain.db.rows(
            "SELECT m.value,m.trust,m.status,e.metadata FROM memories m JOIN json_each(m.source_event_ids) s JOIN events e ON e.id=s.value JOIN event_assets ea ON ea.event_id=e.id WHERE ea.asset_id=?",
            (asset["id"],),
        )
        report["processors"][operation] = {
            "state": state["state"],
            "error": state["error"],
            "seconds": round(time.perf_counter() - started, 3),
            "extracted_text": [row["value"] for row in rows],
            "all_candidates_untrusted": all(
                row["status"] == "candidate" and row["trust"] == "untrusted" for row in rows
            ),
            "original_bytes_equal": brain.vault.get(asset["id"]) == content,
            "result": json.loads(state["result"] or "{}"),
        }
    report["runtime"] = process_usage()
Path("reports/media-evaluation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))

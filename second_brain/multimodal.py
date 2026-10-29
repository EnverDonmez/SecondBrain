"""Local processor seams: originals and derivative locations remain distinct."""

import io
import hashlib
import json
import shutil
import subprocess
import tempfile
import importlib.util
from pathlib import Path

from .db import dumps
from .models import EventInput, MemoryInput, MemoryType, Principal
from .local_media import has_ocr, recognize_image, speech_directory, transcribe, sample_video
from .security import Denied, NotFound, require


class Multimodal:
    def __init__(self, core):
        self.core = core

    def capabilities(self):
        try:
            if not importlib.util.find_spec("faster_whisper") or not importlib.util.find_spec("av"):
                raise Denied("Local speech package is missing")
            speech_directory(self.core.db.root)
            speech = "available"
        except Denied:
            speech = "blocked: local speech package or model not installed"
        video_ready = has_ocr() and importlib.util.find_spec("av") is not None
        return {
            "pdf_text": "working",
            "docx_text": "working",
            "scanned_pdf_ocr": "available"
            if has_ocr() and importlib.util.find_spec("pypdfium2")
            else "blocked: local PDF OCR packages not installed",
            "images": {
                "original": "working",
                "metadata": "working",
                "ocr": "available: RapidOCR CPU"
                if has_ocr()
                else "available: Tesseract"
                if shutil.which("tesseract")
                else "blocked: local OCR package not installed",
            },
            "audio": {
                "original": "working",
                "transcript_sidecar": "working",
                "automatic_transcription": speech,
            },
            "video": {
                "original": "working",
                "timestamped_sidecar": "working",
                "automatic_extraction": (
                    "available: sampled frame OCR + local audio"
                    if speech == "available"
                    else "available: sampled frame OCR; speech model missing"
                )
                if video_ready
                else "blocked: local video/OCR packages not installed",
            },
        }

    def derivative(
        self,
        asset_id,
        text,
        principal,
        kind="transcript",
        location="",
        language=None,
        processor="manual-sidecar",
        metadata=None,
        confidence=1.0,
    ):
        require(principal, "capture")
        asset = self.core.db.one("SELECT * FROM assets WHERE id=? AND tenant=?", (asset_id, principal.tenant))
        if not asset:
            raise NotFound("Asset not found")
        require(principal, "capture", asset["scope"], asset["sensitivity"])
        if kind not in {"transcript", "ocr", "caption", "video_notes"} or not 1 <= len(text) <= 50_000:
            raise ValueError("Invalid derivative kind or length (1–50000 characters required)")
        event = self.core.events.ingest(
            EventInput(
                source="local-derivative",
                source_id=hashlib.sha256(
                    dumps([asset_id, kind, location, text, language, processor]).encode()
                ).hexdigest(),
                actor="document",
                event_type="file." + kind,
                text=text,
                scope=asset["scope"],
                sensitivity=asset["sensitivity"],
                metadata={
                    "location": location,
                    "language": language,
                    "derivative_kind": kind,
                    "original_asset": asset_id,
                    "authority": "untrusted_source",
                    "processor": processor,
                    "extraction": metadata or {},
                },
                attachments=[asset_id],
            ),
            principal,
        )
        candidate = self.core.memory.propose(
            MemoryInput(
                memory_type=MemoryType.EXTERNAL_KNOWLEDGE,
                subject=asset["name"],
                predicate=kind + (":" + location if location else ""),
                value=text,
                source_event_ids=[event["id"]],
                scope=asset["scope"],
                sensitivity=asset["sensitivity"],
                confidence=max(0, min(1, confidence)),
            ),
            principal,
        )
        return {"event": event, "candidate": candidate, "original_preserved": True}

    def ocr(self, asset_id, principal, ensure_active=None):
        require(principal, "admin")
        if has_ocr():
            asset = self._asset(asset_id, principal)
            if not asset["mime"].startswith("image/"):
                raise ValueError("Choose an imported image")
            lines = recognize_image(self.core.vault.get(asset_id))
            if ensure_active:
                ensure_active()
            text = "\n".join(line["text"] for line in lines)
            if not text.strip():
                return {"extracted": False, "reason": "Local OCR returned no text; original retained"}
            return self.derivative(
                asset_id,
                text[:50000],
                principal,
                "ocr",
                "image",
                processor="rapidocr-onnxruntime-1.4.4",
                metadata={"lines": lines},
                confidence=sum(line["confidence"] for line in lines) / len(lines),
            )
        return self.ocr_tesseract(asset_id, principal)

    def _asset(self, asset_id, principal):
        asset = self.core.db.one("SELECT * FROM assets WHERE id=? AND tenant=?", (asset_id, principal.tenant))
        if not asset:
            raise NotFound("Asset not found")
        require(principal, "capture", asset["scope"], asset["sensitivity"])
        return asset

    def enqueue(self, asset_id, operation, principal, language=None):
        require(principal, "admin")
        asset = self._asset(asset_id, principal)
        if operation not in {"ocr", "transcribe", "video", "pdf_ocr"}:
            raise ValueError("Unknown media processing operation")
        capability = self.capabilities()
        expected = {
            "ocr": "image/",
            "transcribe": ("audio/", "video/"),
            "video": "video/",
            "pdf_ocr": "application/pdf",
        }
        if not asset["mime"].startswith(expected[operation]):
            raise ValueError("The selected processor does not support this asset type")
        status = {
            "ocr": capability["images"]["ocr"],
            "transcribe": capability["audio"]["automatic_transcription"],
            "video": capability["video"]["automatic_extraction"],
            "pdf_ocr": capability["scanned_pdf_ocr"],
        }[operation]
        if not status.startswith("available"):
            raise Denied(status)
        return self.core.queue.enqueue(
            "media",
            asset_id + ":" + operation + ":" + str(language),
            {"asset_id": asset_id, "operation": operation, "language": language},
            principal,
        )

    def process(self, job):
        principal = Principal(**job["payload"]["principal"])
        require(principal, "admin")
        asset_id, operation = job["payload"]["asset_id"], job["payload"]["operation"]
        asset = self._asset(asset_id, principal)
        self.core.queue.ensure_active(job["id"])
        if operation == "ocr":
            result = self.ocr(asset_id, principal, lambda: self.core.queue.ensure_active(job["id"]))
            return {
                "operation": operation,
                "extracted": bool(result.get("candidate")),
                "candidate_id": result.get("candidate", {}).get("id"),
            }
        content = self.core.vault.get(asset_id)
        ids = []
        if operation in {"transcribe", "video"}:
            speech_ready = self.capabilities()["audio"]["automatic_transcription"] == "available"
            if operation == "transcribe" or speech_ready:
                transcript = transcribe(
                    content,
                    asset["name"],
                    self.core.db.root,
                    job["payload"].get("language"),
                    lambda progress: self.core.queue.heartbeat(job["id"], progress),
                )
                for segment in transcript["segments"]:
                    self.core.queue.ensure_active(job["id"])
                    derived = self.derivative(
                        asset_id,
                        segment["text"],
                        principal,
                        "transcript",
                        f"seconds:{segment['start']:.3f}-{segment['end']:.3f}",
                        transcript.get("language"),
                        "faster-whisper-tiny-int8-cpu",
                        segment,
                        confidence=max(0, min(1, 1 - segment["no_speech_probability"])),
                    )
                    ids.append(derived["candidate"]["id"])
                    self.core.queue.heartbeat(
                        job["id"],
                        {"stage": "transcript", "segments": len(ids), "processed_until": segment["end"]},
                    )
            elif operation == "video":
                self.core.queue.heartbeat(
                    job["id"], {"warning": "Speech model unavailable; sampled OCR only"}
                )
        if operation == "video":
            for frame in sample_video(content, asset["name"]):
                self.core.queue.ensure_active(job["id"])
                text = "\n".join(line["text"] for line in frame["ocr"])
                if text.strip():
                    derived = self.derivative(
                        asset_id,
                        text[:50000],
                        principal,
                        "video_notes",
                        f"seconds:{frame['timestamp']:.3f}",
                        processor="pyav19-rapidocr1.4.4",
                        metadata=frame,
                        confidence=sum(line["confidence"] for line in frame["ocr"]) / len(frame["ocr"]),
                    )
                    ids.append(derived["candidate"]["id"])
                self.core.queue.heartbeat(
                    job["id"],
                    {"stage": "video", "processed_until": frame["timestamp"], "candidates": len(ids)},
                )
        if operation == "pdf_ocr":
            import pypdfium2 as pdfium
            import numpy as np

            previous = json.loads(job.get("result") or "{}")
            start = int(previous.get("next_page", 0))
            ids = previous.get("candidate_ids", [])
            document = pdfium.PdfDocument(content)
            try:
                if len(document) > 200:
                    raise Denied("Scanned PDF OCR is limited to 200 pages per file")
                for index in range(start, len(document)):
                    self.core.queue.ensure_active(job["id"])
                    page = document[index]
                    try:
                        width, height = page.get_size()
                        bitmap = page.render(scale=min(2, 2200 / max(width, height, 1)))
                        try:
                            lines = recognize_image(np.array(bitmap.to_pil()))
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
                    text = "\n".join(line["text"] for line in lines)
                    self.core.queue.ensure_active(job["id"])
                    if text.strip():
                        derived = self.derivative(
                            asset_id,
                            text[:50000],
                            principal,
                            "ocr",
                            "page:" + str(index + 1),
                            processor="pdfium5-rapidocr1.4.4",
                            metadata={"page": index + 1, "lines": lines},
                            confidence=sum(line["confidence"] for line in lines) / len(lines),
                        )
                        ids.append(derived["candidate"]["id"])
                    self.core.queue.heartbeat(
                        job["id"], {"stage": "pdf_ocr", "next_page": index + 1, "candidate_ids": ids}
                    )
            finally:
                document.close()
        return {
            "operation": operation,
            "candidate_ids": ids,
            "candidates": len(ids),
            "original_preserved": True,
        }

    def ocr_tesseract(self, asset_id, principal):
        require(principal, "admin")
        executable = shutil.which("tesseract")
        if not executable:
            raise Denied("Local Tesseract OCR is not installed")
        asset = self.core.db.one("SELECT * FROM assets WHERE id=? AND tenant=?", (asset_id, principal.tenant))
        if not asset or not asset["mime"].startswith("image/"):
            raise ValueError("Choose an imported image")
        from PIL import Image

        with tempfile.TemporaryDirectory(dir=self.core.db.root) as temp:
            image_path = Path(temp) / "source.png"
            with Image.open(io.BytesIO(self.core.vault.get(asset_id))) as image:
                image.save(image_path, format="PNG")
            result = subprocess.run(  # noqa: S603 -- fixed Tesseract executable and generated local image path
                [executable, str(image_path), "stdout", "-l", "eng"],
                shell=False,
                capture_output=True,
                timeout=60,
                check=True,
            )  # noqa: S603
            text = result.stdout.decode("utf-8").strip()
        if not text:
            return {"extracted": False, "reason": "OCR returned no text; original retained"}
        return self.derivative(asset_id, text, principal, "ocr", "image", "eng")

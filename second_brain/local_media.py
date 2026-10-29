"""CPU-only OCR, speech and bounded media decoding; no remote inference."""

import hashlib
import importlib.util
import io
import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from .db import dumps
from .models import now
from .security import Denied

DEMUXERS = {".wav": "wav", ".mp3": "mp3", ".m4a": "mov", ".mp4": "mov", ".webm": "matroska", ".ogg": "ogg"}
SAFE_DECODE_OPTIONS = {
    "protocol_whitelist": "pipe,crypto,data",
    "enable_drefs": "0",
    "use_absolute_path": "0",
}
MAX_DURATION = 1800


def has_ocr():
    return importlib.util.find_spec("rapidocr_onnxruntime") is not None


@lru_cache(maxsize=1)
def ocr_engine():
    if not has_ocr():
        raise Denied("Install the local media extra for OCR")
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)


def recognize_image(image):
    from PIL import Image

    if isinstance(image, bytes):
        with Image.open(io.BytesIO(image)) as decoded:
            if decoded.width * decoded.height > 25_000_000:
                raise Denied("Image exceeds the 25 megapixel processing limit")
            rgb_image = decoded.convert("RGB")
            rgb_image.thumbnail((2400, 2400))
            image = np.array(rgb_image)
    result, _ = ocr_engine()(image)
    return [
        {"box": [[float(p[0]), float(p[1])] for p in item[0]], "text": item[1], "confidence": float(item[2])}
        for item in result or []
    ]


def install_speech_model(root):
    from faster_whisper import WhisperModel
    from faster_whisper.utils import download_model
    from huggingface_hub import HfApi

    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    directory = (Path(root) / "models" / "speech").resolve()
    directory.mkdir(parents=True, exist_ok=True)
    revision = HfApi().model_info("Systran/faster-whisper-tiny").sha
    if not revision:
        raise ValueError("Speech model revision could not be resolved")
    target = directory / revision
    download_model("tiny", output_dir=str(target), revision=revision)
    WhisperModel(str(target), device="cpu", compute_type="int8", cpu_threads=2, local_files_only=True)
    files = {
        str(p.relative_to(target)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in target.rglob("*")
        if p.is_file() and ".cache" not in p.parts
    }
    manifest = {
        "repository": "Systran/faster-whisper-tiny",
        "revision": revision,
        "path": revision,
        "installed_at": now(),
        "sha256": files,
        "device": "cpu",
        "compute_type": "int8",
    }
    (directory / "ready.json").write_text(dumps(manifest), encoding="utf-8")
    return manifest


def speech_directory(root):
    directory = Path(os.environ.get("SB_MODEL_DIR", str(Path(root) / "models"))) / "speech"
    if not (directory / "ready.json").exists():
        raise Denied("Local speech model is missing; run: second-brain speech-model-install")
    return directory


@lru_cache(maxsize=1)
def speech_engine(directory):
    from faster_whisper import WhisperModel

    manifest = json.loads((Path(directory) / "ready.json").read_text("utf-8"))
    return WhisperModel(
        str(Path(directory) / manifest["path"]),
        device="cpu",
        compute_type="int8",
        cpu_threads=2,
        local_files_only=True,
    )


def open_media(content, filename):
    import av

    extension = Path(filename).suffix.lower()
    if extension not in DEMUXERS:
        raise ValueError("Unsupported media container")
    return av.open(io.BytesIO(content), mode="r", format=DEMUXERS[extension], options=SAFE_DECODE_OPTIONS)


def decode_audio(content, filename, progress=None):
    import av

    chunks, samples = [], 0
    origin, expected, discontinuities, next_progress = None, None, 0, 0
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    with open_media(content, filename) as container:
        if not container.streams.audio:
            return None
        if container.duration and container.duration / 1_000_000 > MAX_DURATION:
            raise Denied("Media exceeds the 30 minute processing limit")
        for frame in container.decode(audio=0):
            stamp = float(frame.time) if frame.time is not None else None
            if origin is None:
                origin = stamp or 0.0
            if stamp is not None and expected is not None and abs(stamp - expected) > 0.1:
                discontinuities += 1
            if stamp is not None and frame.sample_rate:
                expected = stamp + frame.samples / frame.sample_rate
            for normalized in resampler.resample(frame):
                data = normalized.to_ndarray().reshape(-1)
                samples += len(data)
                if samples > 16000 * MAX_DURATION:
                    raise Denied("Decoded audio exceeds processing budget")
                chunks.append(data)
                if progress and samples >= next_progress:
                    progress({"stage": "decode_audio", "decoded_seconds": samples / 16000})
                    next_progress = samples + 160000
        for normalized in resampler.resample(None):
            chunks.append(normalized.to_ndarray().reshape(-1))
    if not chunks:
        return None
    return {
        "audio": np.concatenate(chunks).astype(np.float32) / 32768,
        "source_start_seconds": origin or 0.0,
        "timestamp_basis": "decoded_audio_with_container_start_offset",
        "timestamp_discontinuities": discontinuities,
    }


def transcribe(content, filename, root, language=None, progress=None):
    if language is not None and (
        not isinstance(language, str)
        or not 2 <= len(language) <= 5
        or not language.replace("-", "").isalpha()
    ):
        raise ValueError("Invalid speech language code")
    directory = speech_directory(root)
    decoded = decode_audio(content, filename, progress)
    if decoded is None:
        return {"segments": [], "language": language, "reason": "No audio stream"}
    segments, info = speech_engine(str(directory)).transcribe(
        decoded["audio"], language=language, beam_size=3, vad_filter=True, condition_on_previous_text=False
    )
    rows = []
    for s in segments:
        if progress:
            progress({"stage": "speech_inference", "processed_until": float(s.end)})
        if not s.text.strip() or s.no_speech_prob >= 0.9:
            continue
        rows.append(
            {
                "start": float(s.start) + decoded["source_start_seconds"],
                "end": float(s.end) + decoded["source_start_seconds"],
                "text": s.text.strip(),
                "average_log_probability": float(s.avg_logprob),
                "no_speech_probability": float(s.no_speech_prob),
                "timestamp_basis": decoded["timestamp_basis"],
                "timestamp_discontinuities": decoded["timestamp_discontinuities"],
                "confidence_basis": "one_minus_no_speech_probability; not calibrated transcript accuracy",
            }
        )
    return {
        "segments": rows,
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "processor": "faster-whisper-tiny-int8-cpu",
    }


def sample_video(content, filename, interval=15, max_frames=120):
    if not 1 <= interval <= 300 or not 1 <= max_frames <= 120:
        raise ValueError("Video sampling budget is invalid")
    count, next_at = 0, 0.0
    with open_media(content, filename) as container:
        if not container.streams.video:
            return
        stream = container.streams.video[0]
        if stream.width * stream.height > 25_000_000:
            raise Denied("Video exceeds the 25 megapixel frame limit")
        if container.duration and container.duration / 1_000_000 > MAX_DURATION:
            raise Denied("Video exceeds the 30 minute processing limit")
        for index, frame in enumerate(container.decode(video=0)):
            rate = float(stream.average_rate or 1)
            stamp = float(frame.time) if frame.time is not None else index / rate
            if stamp < next_at:
                continue
            image = frame.to_image()
            image.thumbnail((1600, 1600))
            yield {
                "timestamp": stamp,
                "timestamp_basis": "container" if frame.time is not None else "estimated_from_frame_rate",
                "frame_index": index,
                "ocr": recognize_image(np.array(image)),
            }
            count += 1
            next_at = stamp + interval
            if count >= max_frames:
                break

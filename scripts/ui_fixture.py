"""Disposable UI QA server. Never writes the user's data/ brain."""

from pathlib import Path
import io

import uvicorn

from second_brain.api import create_app
from second_brain.models import OWNER, EventInput, MemoryInput

root = Path(".test-tmp/ui-qa").resolve()
root.mkdir(parents=True, exist_ok=True)
(root / "owner.token").write_text("synthetic-ui-test-owner-key", encoding="utf-8")
app = create_app(root, run_worker=True)
brain = app.state.brain
for index, (kind, subject, predicate, value, scope) in enumerate(
    [
        (
            "USER_PREFERENCE",
            "user",
            "cevap_dili",
            "Kısa ve kaynaklı Türkçe yanıtları tercih ederim.",
            "global",
        ),
        (
            "DECISION",
            "Second Brain",
            "veritabanı",
            "Kanonik kayıtlar SQLite üzerinde, motorlar değiştirilebilir projection olarak tutulur.",
            "Second Brain",
        ),
        ("PROJECT_STATE", "Araştırma", "durum", "Sentetik UI doğrulama çalışması devam ediyor.", "Araştırma"),
    ]
):
    event = brain.events.ingest(
        EventInput(source="synthetic-ui-qa", source_id=str(index), actor="user", text=value, scope=scope),
        OWNER,
    )
    record = brain.memory.propose(
        MemoryInput(
            memory_type=kind,
            subject=subject,
            predicate=predicate,
            value=value,
            scope=scope,
            source_event_ids=[event["id"]],
        ),
        OWNER,
    )
    brain.memory.commit(record["id"], OWNER)
brain.learning.feedback("API değiştirmeden önce mevcut testleri oku.", "global", "correction", OWNER)
if not brain.db.one("SELECT 1 FROM assets WHERE name='synthetic-ocr.png'"):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1000, 240), "white")
    ImageDraw.Draw(image).text(
        (35, 65), "SECOND BRAIN MEMORY TEST", fill="black", font=ImageFont.load_default(size=42)
    )
    content = io.BytesIO()
    image.save(content, format="PNG")
    brain.importer.submit(content.getvalue(), "synthetic-ocr.png", OWNER)
uvicorn.run(app, host="127.0.0.1", port=8766, log_level="warning", access_log=False)

"""Additional frozen synthetic cases and bounded real semantic/concurrency measurement."""

import argparse
import hashlib
import json
import os
import statistics
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.goal_audit import record
from second_brain.core import Brain
from second_brain.db import dumps
from second_brain.memory import project
from second_brain.models import OWNER, SearchInput
from second_brain.providers import index_vectors
from second_brain.runtime import process_usage
from second_brain.semantic_runtime import semantic_worker


ROOT = Path(__file__).resolve().parents[1]

# New examples beyond the original 24-question diagnostic. Frozen with the report;
# authored in this implementation round, so not an independent external benchmark.
RECORDS = [
    "Toplantıları öğleden sonra yapmayı tercih ederim.",
    "Dosya yedekleri her cuma harici diske kopyalanır.",
    "Mobil uygulama projesinde veritabanı olarak PostgreSQL seçildi.",
    "E-posta bildirimleri kapalı, yalnızca uygulama içi bildirimler açık.",
    "İnceleme sırasında hata bulunursa değişikliği düzeltip testi tekrar çalıştır.",
    "Kitap okurken sessiz bir ortam isterim.",
    "Proje raporlarını Markdown biçiminde hazırlamayı seviyorum.",
    "Arayüz tasarımında büyük yazı boyutu kullanılmalı.",
    "Tıklamadan önce ikinci ajan düğmenin hedefini doğrulasın.",
    "Kişisel veriler yerel cihazda saklanır ve buluta gönderilmez.",
    "Kod örneklerini TypeScript dilinde görmek istiyorum.",
    "Uzun listeler yerine bağlantılı paragraflarla cevap ver.",
    "İşlem başarıyla bittikten sonra kısa bir sonuç bildir.",
    "Fotoğraf albümünü yıllara göre klasörlere ayırdık.",
]
CASES = [
    ("Görüşmeler için günün hangi bölümünü seviyorum?", 0),
    ("Yedekler hangi gün nereye taşınıyor?", 1),
    ("Mobil projede hangi veri tabanını kullanıyoruz?", 2),
    ("Mail uyarıları açık mı?", 3),
    ("İncelemede bug çıkarsa nasıl ilerlemelisin?", 4),
    ("Kitapları gürültülü ortamda mı okumayı seviyorum?", 5),
    ("Raporları hangi formatta hazırlıyoruz?", 6),
    ("Ekrandaki metin boyutu nasıl olmalı?", 7),
    ("Düğmeye basmadan önce kim kontrol etmeli?", 8),
    ("Veriler uzaktaki sunuculara yollanabilir mi?", 9),
    ("Örnek kodları hangi dilde istemiştim?", 10),
    ("Yanıtlarını madde madde mi paragraf mı yazmalısın?", 11),
    ("İşi bitirince bana ne bildirmelisin?", 12),
    ("Fotoğrafları nasıl gruplamıştık?", 13),
    ("Toplantı öğleden sonra", 0),
    ("cuma harici disk", 1),
    ("PostgreSQL", 2),
    ("Markdown", 6),
    ("TypeScript", 10),
    ("fotoğraf albümü", 13),
]
UNKNOWN = [
    "Köpeğimin adı nedir?",
    "Pasaport numaramı hatırlıyor musun?",
    "Kiralık evimin adresi ne?",
    "Venüs projesinin bütçesi ne kadar?",
    "Ayakkabı numaram kaç?",
]


def quality(output):
    with tempfile.TemporaryDirectory(dir=output) as directory:
        brain = Brain(directory)
        memories = [record(brain, text, f"new-{i}", "USER_ASSERTED_FACT") for i, text in enumerate(RECORDS)]
        index_vectors(brain.db, OWNER)
        cases = []
        for query, expected in CASES:
            result = brain.retrieval.search(SearchInput(query=query, engine="hybrid", limit=5), OWNER)
            ids = [r["id"] for r in result["items"]]
            cases.append(
                {
                    "query": query,
                    "expected": RECORDS[expected],
                    "top1": bool(ids and ids[0] == memories[expected]["id"]),
                    "recall5": memories[expected]["id"] in ids,
                    "returned_values": [r["value"] for r in result["items"]],
                }
            )
        unknown = [
            {
                "query": q,
                "returned": len(
                    brain.retrieval.search(SearchInput(query=q, engine="hybrid"), OWNER)["items"]
                ),
            }
            for q in UNKNOWN
        ]
        learning = []
        for text in [
            "Dağıtım öncesi bağlantı testini çalıştır",
            "Dağıtım öncesi bağlantı testlerini çalıştır",
            "Dağıtımdan önce bağlantı testini çalıştır",
            "Dağıtım öncesi bağlantı testini çalıştırma",
            "Dağıtım öncesi bağlantı testini 2 kez çalıştır",
        ]:
            result = brain.learning.feedback(text, "global", "correction", OWNER)
            learning.append(
                {
                    "text": text,
                    "evidence_count": result["evidence_count"],
                    "match_method": result["match_method"],
                    "candidate": bool(result["candidate_lesson"]),
                }
            )
        return {
            "fixture_sha256": hashlib.sha256(
                json.dumps([RECORDS, CASES, UNKNOWN], ensure_ascii=False).encode()
            ).hexdigest(),
            "corpus": RECORDS,
            "cases": cases,
            "top1": sum(c["top1"] for c in cases),
            "recall5": sum(c["recall5"] for c in cases),
            "total": len(cases),
            "unknown": unknown,
            "real_model_learning": learning,
            "limitations": "Small synthetic set authored in the same development round; no external quality or LLM-answer guarantee.",
        }


def scale(output, size):
    with tempfile.TemporaryDirectory(dir=output) as directory:
        brain = Brain(directory)
        first = record(
            brain, "Araştırma projesi 0: depolama motoru SQLite seçildi.", "decision-0", "DECISION"
        )
        memory_template = brain.db.one("SELECT * FROM memories WHERE id=?", (first["id"],))
        event_template = brain.db.one("SELECT * FROM events WHERE id=?", (first["source_event_ids"][0],))
        # Fixture setup is not part of measured indexing/search throughput.
        with brain.db.transaction() as con:
            for i in range(1, size):
                identity = f"{i:032x}"
                value = f"Araştırma projesi {i}: depolama motoru SQLite seçildi."
                event = {
                    **event_template,
                    "id": identity,
                    "source_id": f"decision-{i}",
                    "text": value,
                    "content_hash": hashlib.sha256(value.encode()).hexdigest(),
                }
                con.execute(
                    "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tuple(event.values()),
                )
                row = {
                    **memory_template,
                    "id": identity,
                    "logical_id": identity,
                    "predicate": f"decision-{i}",
                    "value": value,
                    "source_event_ids": dumps([identity]),
                }
                brain.memory._insert(con, row)
                project(con, row)
        started = time.perf_counter()
        indexed = index_vectors(brain.db, OWNER)
        result = {
            "records": size,
            "index": indexed,
            "index_seconds": time.perf_counter() - started,
            "parent_after_index": process_usage(),
            "worker_after_index": semantic_worker.status(),
        }

        def search(i):
            return brain.retrieval.search(
                SearchInput(query=f"Araştırma projesi {i * 97}: veritabanı kararı", engine="hybrid", limit=5),
                OWNER,
            )["elapsed_ms"]

        result["warmup_ms"] = search(0)
        samples = [search(i) for i in range(1, 11)]
        result["sequential"] = {
            "samples_ms": samples,
            "p50_ms": statistics.median(samples),
            "p95_ms": max(samples),
        }
        with ThreadPoolExecutor(max_workers=4) as pool:
            samples = list(pool.map(search, range(12)))
        result["concurrent_4"] = {
            "samples_ms": samples,
            "p50_ms": statistics.median(samples),
            "p95_ms": max(samples),
        }
        result["parent_after_search"] = process_usage()
        deadline = time.monotonic() + semantic_worker.idle_seconds + 5
        while semantic_worker.status()["running"] and time.monotonic() < deadline:
            time.sleep(0.1)
        result["after_idle"] = {"parent": process_usage(), "worker": semantic_worker.status()}
        result["limitations"] = (
            "One local run; synthetic short records; p95 is maximum of 10/12 samples, no statistical confidence interval. Worker last_usage is a recent sample, not peak RSS."
        )
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["quality", "scale"])
    parser.add_argument("--size", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/completion-20261026")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ["SB_MODEL_DIR"] = str(ROOT / "data/models")
    result = quality(args.output) if args.mode == "quality" else scale(args.output, args.size)
    target = args.output / ("new-quality.json" if args.mode == "quality" else f"scale-{args.size}.json")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(target), "top1": result.get("top1"), "total": result.get("total")}))


if __name__ == "__main__":
    main()

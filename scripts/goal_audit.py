"""Reproducible product-goal audit; synthetic databases only, live DB read-only."""

import argparse
import io
import json
import os
import socket
import sqlite3
import tempfile
import threading
import time
import zipfile
from pathlib import Path

import httpx

from second_brain.core import Brain
from second_brain.db import dumps
from second_brain.models import OWNER, EventInput, MemoryInput, Principal, SearchInput, now
from second_brain.runtime import process_usage


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "goal-audit-20261026"


def record(brain, value, predicate, kind="USER_PREFERENCE", scope="global", importance=3):
    event = brain.events.ingest(
        EventInput(source="goal-audit", source_id=predicate, text=value, scope=scope), OWNER
    )
    candidate = brain.memory.propose(
        MemoryInput(
            value=value,
            predicate=predicate,
            memory_type=kind,
            scope=scope,
            importance=importance,
            source_event_ids=[event["id"]],
        ),
        OWNER,
    )
    return brain.memory.commit(candidate["id"], OWNER)


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def functional():
    report = {"created_at": now(), "synthetic_only": True}
    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        brain = Brain(directory)
        natural = [
            "Bana hep Türkçe ve kısa cevap ver.",
            "Uzun listeler yerine paragraf okumayı seviyorum.",
            "Hocam bir daha tıklamadan önce başka bir ajana kontrol ettir.",
            "Kaynak göstermeden kesin konuşmanı istemiyorum.",
            "Kod örneklerinde Python kullanmanı tercih ederim.",
            "Arayüzlerde koyu tema seviyorum.",
            "Benimle konuşurken gereksiz onay soruları sorma.",
            "Projelerimi kendi bilgisayarımda çalıştırmak istiyorum.",
            "Tercihim: Türkçe kısa yanıt",
            "Kuralım: Kaynak göster",
        ]
        report["extraction"] = []
        for i, text in enumerate(natural):
            event = brain.events.ingest(EventInput(source="conversation", source_id=str(i), text=text), OWNER)
            result = brain.importer.extract_explicit(event["id"], OWNER)
            report["extraction"].append(
                {"text": text, "control_syntax": i >= 8, "candidates": len(result["candidates"])}
            )
        report["capture_only"] = {
            "events_stored": brain.db.one("SELECT COUNT(*) n FROM events")["n"],
            "recall_found": len(brain.dispatch("brain.recall", {"query": "koyu tema"}, OWNER)["items"]),
            "timeline_found": any("koyu tema" in e["text"] for e in brain.events.list(OWNER)),
        }
        # Different compatible preferences use the same extractor predicate.
        states = []
        for i, text in enumerate(["Tercihim: Kısa cevap", "Tercihim: Koyu tema"]):
            event = brain.events.ingest(
                EventInput(source="multi-preference", source_id=str(i), text=text), OWNER
            )
            candidate = brain.importer.extract_explicit(event["id"], OWNER)["candidates"][0]
            states.append(brain.memory.commit(candidate["id"], OWNER)["status"])
        report["independent_explicit_preferences"] = states

    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        brain = Brain(directory)
        texts = [
            "Tıklamadan önce bağımsız alt ajana hedefi doğrulat.",
            "Her tıklama öncesinde başka bir ajan hedefi kontrol etsin.",
            "Bilgisayarda düğmeye basmadan evvel ikinci ajanın onayını al.",
        ]
        report["paraphrased_feedback"] = [
            {
                "text": text,
                "evidence_count": (r := brain.learning.feedback(text, "global", "correction", OWNER))[
                    "evidence_count"
                ],
                "candidate": bool(r["candidate_lesson"]),
            }
            for text in texts
        ]
        repeat = "Hata düzeltmesinden sonra ilgili testi çalıştır."
        results = [brain.learning.feedback(repeat, "global", "correction", OWNER) for _ in range(8)]
        report["repeated_feedback"] = {
            "evidence_counts": [r["evidence_count"] for r in results],
            "lesson_candidates": brain.db.one("SELECT COUNT(*) n FROM memories WHERE memory_type='LESSON'")[
                "n"
            ],
            "active_before_approval": brain.db.one("SELECT COUNT(*) n FROM memories WHERE status='active'")[
                "n"
            ],
        }

    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        brain = Brain(directory)
        rows = [
            ("Yanıtları kısa ve Türkçe tercih ederim.", "reply_style", "USER_PREFERENCE", "global"),
            ("Her tıklamadan önce bağımsız alt ajan hedefi doğrulamalı.", "click_rule", "POLICY", "global"),
            (
                "Kaynakları göster ve belirsiz bilgiyi kesinmiş gibi sunma.",
                "sources",
                "USER_PREFERENCE",
                "global",
            ),
            (
                "Kod örneklerinde Python kullanmayı tercih ederim.",
                "coding_language",
                "USER_PREFERENCE",
                "global",
            ),
            ("Gereksiz onay soruları sormadan yetkili işleri tamamla.", "autonomy", "POLICY", "global"),
            (
                "SecondBrain projesinin veritabanı SQLite olarak seçildi.",
                "database",
                "DECISION",
                "secondbrain",
            ),
            (
                "SecondBrain uygulaması yerel bilgisayarda çalışır, buluta veri göndermez.",
                "deployment",
                "PROJECT_STATE",
                "secondbrain",
            ),
            (
                "Hata düzeltmesinden sonra ilgili regresyon testini çalıştır.",
                "regression",
                "LESSON",
                "global",
            ),
            (
                "Dün bahçe sulama sisteminde damlama yöntemi üzerine konuştuk.",
                "garden_topic",
                "OBSERVED_EVENT",
                "global",
            ),
            (
                "OCR işinde önce ekran görüntüsünün çözünürlüğünü artırmak işe yaradı.",
                "ocr_lesson",
                "LESSON",
                "global",
            ),
            ("Araştırma projesinde Mavi Mercan raporu tamamlandı.", "report", "PROJECT_STATE", "research"),
            ("Kullanıcı arayüzünde koyu tema kullanılmasını isterim.", "theme", "USER_PREFERENCE", "global"),
        ]
        memories = [record(brain, *row) for row in rows]
        cases = [
            ("Türkçe", 0, "keyword"),
            ("Hangi dilde ve ne uzunlukta cevap vermelisin?", 0, "natural"),
            ("Cevaplarını nasıl yazmanı seviyorum?", 0, "paraphrase"),
            ("tıklamadan önce", 1, "keyword"),
            ("Ekrandaki düğmeye basmadan önce kime kontrol ettirmelisin?", 1, "paraphrase"),
            ("kaynakları göster", 2, "keyword"),
            ("Emin olmadığın bir şeyi bana nasıl anlatmalısın?", 2, "paraphrase"),
            ("Python", 3, "keyword"),
            ("Kodları hangi programlama dilinde yazmanı istiyorum?", 3, "natural"),
            ("gereksiz onay", 4, "keyword"),
            ("İşe devam etmek için sürekli benden izin istemeli misin?", 4, "paraphrase"),
            ("SecondBrain SQLite", 5, "keyword"),
            ("Hafıza uygulamamızda hangi veritabanına karar verdik?", 5, "natural"),
            ("buluta veri", 6, "keyword"),
            ("Verilerimi uzak sunuculara yolluyor muyuz?", 6, "paraphrase"),
            ("regresyon testini", 7, "keyword"),
            ("Bir bugı giderdikten sonra ne yapmayı öğrenmiştik?", 7, "paraphrase"),
            ("bahçe sulama", 8, "keyword"),
            ("Dün bitkileri sulamak hakkında ne konuşmuştuk?", 8, "natural"),
            ("OCR çözünürlüğünü", 9, "keyword"),
            ("Görüntüden metin okumada hangi yöntem faydalı olmuştu?", 9, "paraphrase"),
            ("Mavi Mercan", 10, "keyword"),
            ("koyu tema", 11, "keyword"),
            ("Arayüzün aydınlık mı karanlık mı olmasını seviyorum?", 11, "paraphrase"),
        ]
        report["retrieval"] = []
        baseline = process_usage()
        model_dir = ROOT / "data" / "models"
        report["model_available"] = (model_dir / "ready.json").exists()
        engines = ["fts", "bm25", "hybrid"]

        def evaluate(engine, phase):
            outcomes = []
            for query, expected, kind in cases:
                result = brain.retrieval.search(SearchInput(query=query, engine=engine, limit=5), OWNER)
                ids = [r["id"] for r in result["items"]]
                outcomes.append(
                    {
                        "query": query,
                        "kind": kind,
                        "top1": bool(ids and ids[0] == memories[expected]["id"]),
                        "recall5": memories[expected]["id"] in ids,
                        "returned": len(ids),
                        "elapsed_ms": result["elapsed_ms"],
                    }
                )
            report["retrieval"].append(
                {
                    "engine": engine,
                    "phase": phase,
                    "cases": outcomes,
                    "top1": sum(o["top1"] for o in outcomes),
                    "recall5": sum(o["recall5"] for o in outcomes),
                }
            )
            unknown = []
            for query in [
                "Kan grubum ne?",
                "Doğum tarihim hangi gün?",
                "Evimin açık adresi nedir?",
                "Kedimin adı ne?",
                "Atlas projesinin bütçesi kaç lira?",
                "En sevdiğim yemek hangisi?",
            ]:
                result = brain.retrieval.search(SearchInput(query=query, engine=engine, limit=5), OWNER)
                unknown.append(
                    {"query": query, "returned": len(result["items"]), "abstain": result["abstain"]}
                )
            report.setdefault("unknown_queries", []).append(
                {"engine": engine, "phase": phase, "cases": unknown}
            )

        for engine in engines:
            evaluate(engine, "no_vectors")
        if report["model_available"]:
            from second_brain.providers import index_vectors

            original = os.environ.get("SB_MODEL_DIR")
            os.environ["SB_MODEL_DIR"] = str(model_dir)
            network_attempts = []
            connect = socket.socket.connect

            def deny_network(sock, address):
                network_attempts.append(str(address))
                raise RuntimeError("Network disabled during local audit")

            socket.socket.connect = deny_network
            try:
                started = time.perf_counter()
                report["indexing"] = index_vectors(brain.db, OWNER)
                report["indexing"]["wall_seconds"] = round(time.perf_counter() - started, 3)
                for engine in ["vector", "hybrid"]:
                    evaluate(engine, "indexed")
                report["embedding_usage"] = {
                    "before": baseline,
                    "after": process_usage(),
                    "network_attempts": network_attempts,
                }
                write("functional-progress.json", report)
            finally:
                socket.socket.connect = connect
                if original is None:
                    os.environ.pop("SB_MODEL_DIR", None)
                else:
                    os.environ["SB_MODEL_DIR"] = original

        scoped = brain.dispatch(
            "brain.prepare_context", {"query": "Beynimi tara", "scope": "secondbrain", "budget": 8000}, OWNER
        )
        report["scoped_bootstrap"] = {
            "record_types": [r["memory_type"] for r in scoped["records"]],
            "global_policy_included": any(r["memory_type"] == "POLICY" for r in scoped["records"]),
            "global_preference_included": any(
                r["memory_type"] == "USER_PREFERENCE" for r in scoped["records"]
            ),
        }
        report["budget_bootstrap"] = []
        for budget in [512, 1000, 3000, 6000, 12000]:
            packet = brain.dispatch("brain.prepare_context", {"budget": budget}, OWNER)
            report["budget_bootstrap"].append(
                {
                    "budget": budget,
                    "actual_bytes": len(dumps(packet).encode()),
                    "record_count": len(packet["records"]),
                    "policies": sum(r["memory_type"] == "POLICY" for r in packet["records"]),
                    "types": [r["memory_type"] for r in packet["records"]],
                }
            )
        package = io.BytesIO()
        skill_text = "---\nname: audit-skill\ndescription: Rapor üretme prosedürü\n---\nÖnce girdiyi doğrula, ardından raporu oluştur."
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("SKILL.md", skill_text)
            archive.writestr("scripts/report.py", "print('synthetic report')\n")
        skill = brain.skills.register(package.getvalue(), OWNER)
        brain.skills.state(skill["id"], True, OWNER)
        agent = Principal(
            id="audit-agent", role="agent", scopes=["global"], permissions=["read"], clearance=1
        )
        read = brain.dispatch("brain.get_skill", {"id": skill["id"]}, agent)
        file_read = brain.dispatch(
            "brain.get_skill_file", {"id": skill["id"], "path": "scripts/report.py"}, agent
        )
        report["skill_portability"] = {
            "skill_text_available": read["content"] == skill_text,
            "script_content_available_to_model": "print('synthetic report')" in dumps(read),
            "script_content_available_on_request": file_read["content"] == "print('synthetic report')\n",
            "package_roundtrip": brain.skills.export(skill["id"], OWNER) == package.getvalue(),
        }
        tool = brain.tools.register("audit-mcp", "mcp", {"description": "Synthetic test tool"}, OWNER)[0]
        disabled_capabilities = brain.dispatch("brain.list_capabilities", {}, agent)
        brain.tools.set_state(tool["id"], True, OWNER)
        capabilities = brain.dispatch("brain.list_capabilities", {}, agent)
        report["tool_inventory"] = {
            "registered": len(brain.tools.list(OWNER)),
            "disabled_tool_hidden": "audit-mcp" not in dumps(disabled_capabilities),
            "registered_tool_discoverable_in_model_capabilities": "audit-mcp" in dumps(capabilities),
            "canonical_json_export_contains_tool_configs": "tool_configs" in json.loads(brain.export(OWNER)),
        }
        reopened = Brain(directory)
        report["persistence"] = {
            "memory_count": reopened.db.one("SELECT COUNT(*) n FROM memories WHERE status='active'")["n"],
            "enabled_skills": sum(s["state"] == "enabled" for s in reopened.skills.list(OWNER)),
            "tools": len(reopened.tools.list(OWNER)),
        }
    write("functional.json", report)
    return report


def live_metadata():
    path = ROOT / "data" / "brain.sqlite3"
    result = {"created_at": now(), "read_only": True, "content_read": False}
    if path.exists():
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as con:
            result["integrity"] = con.execute("PRAGMA quick_check").fetchone()[0]
            tables = [
                "events",
                "memories",
                "skills",
                "tool_configs",
                "tokens",
                "feedback",
                "vector_chunks",
                "usage",
            ]
            result["counts"] = {
                table: con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]  # noqa: S608 -- fixed local table allowlist
                for table in tables
            }
            result["memory_states"] = con.execute(
                "SELECT status,COUNT(*) FROM memories GROUP BY status"
            ).fetchall()
            result["memory_types"] = con.execute(
                "SELECT memory_type,COUNT(*) FROM memories GROUP BY memory_type"
            ).fetchall()
            result["event_sources"] = con.execute(
                "SELECT source,COUNT(*) FROM events GROUP BY source"
            ).fetchall()
            result["jobs"] = con.execute(
                "SELECT kind,state,COUNT(*) FROM jobs GROUP BY kind,state"
            ).fetchall()
            result["enabled_skills"] = con.execute(
                "SELECT COUNT(*) FROM skills WHERE state='enabled'"
            ).fetchone()[0]
            result["active_model_credentials"] = con.execute(
                "SELECT COUNT(*) FROM tokens WHERE revoked=0"
            ).fetchone()[0]
    sizes = {}
    for name in [".venv", "third_party", "data", "reports", "dist", "build"]:
        sizes[name] = sum(p.stat().st_size for p in (ROOT / name).rglob("*") if p.is_file())
    result["disk_bytes"] = sizes
    write("live-metadata.json", result)
    return result


def performance():
    from second_brain.benchmark import run_performance

    report = {"created_at": now(), "scale": []}
    for count in [1000, 10000, 50000]:
        print("performance", count, flush=True)
        sample_root = OUT / ("performance-" + str(count))
        started = time.perf_counter()
        result = run_performance(sample_root, count=count)
        result["wall_seconds"] = round(time.perf_counter() - started, 3)
        result["process_usage"] = process_usage()
        report["scale"].append(result)
        write("performance.json", report)
    return report


def idle():
    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        brain = Brain(directory)
        queries = []
        connect = brain.db.connect

        def counted_connect():
            queries.append(time.perf_counter())
            return connect()

        brain.db.connect = counted_connect
        worker = threading.Thread(target=brain.worker, daemon=True)
        before = process_usage()
        started = time.perf_counter()
        worker.start()
        brain.stop_event.wait(8)
        brain.stop_event.set()
        worker.join(timeout=2)
        after = process_usage()
        elapsed = time.perf_counter() - started
        result = {
            "seconds": elapsed,
            "before": before,
            "after": after,
            "cpu_core_percent": (after["cpu_seconds"] - before["cpu_seconds"]) / elapsed * 100,
            "database_connections": len(queries),
            "connections_per_second": len(queries) / elapsed,
            "worker_stopped": not worker.is_alive(),
        }
        write("idle.json", result)
        return result


def live_http():
    result = {"created_at": now(), "read_only_requests": True}
    try:
        token = (ROOT / "data" / "owner.token").read_text().strip()
        with httpx.Client(base_url="http://127.0.0.1:8765", trust_env=False, timeout=3) as client:
            health = client.get("/healthz")
            result["health"] = {"status_code": health.status_code, "body": health.json()}
            client.headers["Authorization"] = "Bearer " + token
            samples = []
            for _ in range(3):
                started = time.perf_counter()
                status = client.get("/api/status")
                status.raise_for_status()
                body = status.json()
                samples.append(
                    {
                        "elapsed_ms": (time.perf_counter() - started) * 1000,
                        "runtime": body["runtime"],
                        "counts": body["counts"],
                    }
                )
                time.sleep(3)
            result["samples"] = samples
            delta_cpu = samples[-1]["runtime"]["cpu_seconds"] - samples[0]["runtime"]["cpu_seconds"]
            result["cpu_seconds_between_samples"] = delta_cpu
            result["note"] = "Includes three status requests; short sample, not a long leak soak."
    except (OSError, httpx.HTTPError, ValueError) as exc:
        result["unavailable"] = type(exc).__name__
    write("live-http.json", result)
    return result


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["functional", "metadata", "performance", "idle", "live-http"])
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output_dir.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "functional": functional,
        "metadata": live_metadata,
        "performance": performance,
        "idle": idle,
        "live-http": live_http,
    }[args.mode]()
    print(json.dumps({"mode": args.mode, "output": str(OUT), "completed": bool(result)}))


if __name__ == "__main__":
    main()

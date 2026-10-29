"""Build the research inventory/HTML and verify saved evidence; no network or app writes."""

import hashlib
import html
import json
import re
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "SECOND_BRAIN_ARASTIRMA_RAPORU.md"

ROLES = {
    "nevamind-ai/memu": "Mevcut ajanla hafıza yazma",
    "volcengine/openviking": "Katmanlı bağlam altyapısı",
    "basicmachines-co/basic-memory": "Taşınabilir kişisel bilgi tabanı",
    "doobidoo/mcp-memory-service": "Yerel semantik hafıza",
    "samrusani/alicememory": "Kaynaklı oturum devamlılığı",
    "ramaaditya49/titen": "Modelsiz kaynak/iddia çekirdeği",
    "rohitg00/agentmemory": "Host yakalama ve devamlılık",
    "modelcontextprotocol/servers": "MCP referans sunucuları",
    "mem0ai/mem0": "Hafıza API'si",
    "getzep/graphiti": "Zamansal bilgi grafiği",
    "vectorize-io/hindsight": "Retain/recall/reflect hafızası",
    "memtensor/memos": "Hafıza ve skill yaşam döngüsü",
    "topoteretes/cognee": "Graf/semantik veri hattı",
    "letta-ai/letta": "Stateful ajan runtime'ı",
    "memvid/memvid": "Taşınabilir hafıza dosyası",
    "supermemoryai/supermemory": "Açık SDK; sunucu çekirdeği kapalı",
    "osu-nlp-group/hipporag": "İlişkisel erişim araştırması",
    "vectifyai/pageindex": "Belge ağacı ve reasoning erişimi",
    "parthsarthi03/raptor": "Özet ağacı araştırması",
    "hkuds/lightrag": "Graf + vektör RAG",
    "langchain-ai/langmem": "Ajan hafıza araçları",
    "memorilabs/memori": "SQL hafıza entegrasyonu",
    "mempalace/mempalace": "Özgün konuşma arşivi/erişim",
    "thedotmack/claude-mem": "Host capture ve AI sıkıştırması",
    "networkx/networkx": "Graf algoritmaları kütüphanesi",
    "kuzudb/kuzu": "Arşivlenmiş embedded graf DB",
    "ladybugdb/ladybug": "Embedded graf DB",
    "unum-cloud/usearch": "Vektör ANN kütüphanesi",
    "xiaowu0162/longmemeval": "Uzun sohbet değerlendirmesi",
    "snap-research/locomo": "Diyalog veri/değerlendirme deposu",
    "agiresearch/a-mem": "Bağlantılı ajan notları araştırması",
    "cipher208/a-memory": "SQLite katmanlı hafıza",
    "openagenthq/localmem-mcp": "Küçük yerel semantik store",
    "asg017/sqlite-vec": "SQLite vektör uzantısı",
    "microsoft/graphrag": "Graf tabanlı RAG hattı",
    "xiaowu0162/longmemeval-v2": "İş akışı hafızası değerlendirmesi",
}
LICENSE_OVERRIDES = {
    "nevamind-ai/memu": "Apache-2.0 (metin)",
    "memorilabs/memori": "Apache-2.0 (metin)",
    "networkx/networkx": "BSD-3-Clause (metin)",
    "snap-research/locomo": "CC BY-NC 4.0; OSS lisansı değil",
    "modelcontextprotocol/servers": "MIT → Apache-2.0 geçişi; docs CC BY 4.0",
    "supermemoryai/supermemory": "MIT açık repo; sunucu kapalı",
}


def main():
    ledger = json.loads((ROOT / "source-ledger.json").read_text("utf-8"))
    selected_path = ROOT / "implementation-ledger.json"
    selected = json.loads(selected_path.read_text("utf-8"))
    extras = [
        ("basicmachines-co/basic-memory", "9643ec25918e8958629a668e3ce928981ab3ea36", "src/basic_memory/man/man3/bm-context(3).md"),
        ("basicmachines-co/basic-memory", "9643ec25918e8958629a668e3ce928981ab3ea36", "src/basic_memory/mcp/tools/context.py"),
        ("asg017/sqlite-vec", "main", "LICENSE-APACHE"),
    ]
    for repo, revision, path in extras:
        if any(x.get("repo") == repo and x.get("path") == path and x.get("status") == 200 for x in selected):
            continue
        local = Path("sources") / repo.replace("/", "--") / (path.replace("/", "__") + ".txt")
        content = (ROOT / local).read_bytes()
        selected.append({"repo": repo, "revision": revision, "path": path, "local_path": str(local), "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content), "url": f"https://raw.githubusercontent.com/{repo}/{revision}/{path}", "status": 200, "truncated": False})
    selected_path.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [x for x in ledger["repositories"] if x.get("repo")]
    assert len(rows) == 36
    table = ["| Depo | İncelenen rol | Üst düzey lisans / kapsam | Son push (UTC) / arşiv durumu | Sabitleme |", "|---|---|---|---|---|"]
    for row in rows:
        repo = row["repo"]
        key = repo.lower()
        license_name = LICENSE_OVERRIDES.get(key, (row.get("license_metadata") or {}).get("spdx_id", "Belirsiz"))
        revision = row.get("commit")
        snapshot = f"`{revision[:12]}`" if revision else f"`{row['default_branch']}` + dosya SHA-256"
        status = "arşivli" if row["archived"] else "arşivli değil"
        table.append(f"| [{repo}]({row['url']}) | {ROLES[key]} | {license_name} | {row['pushed_at'][:10]} / {status} | {snapshot} |")
    text = REPORT.read_text("utf-8")
    generated = "<!-- INVENTORY_START -->\n" + "\n".join(table) + "\n<!-- INVENTORY_END -->"
    if "<!-- INVENTORY_TABLE -->" in text:
        text = text.replace("<!-- INVENTORY_TABLE -->", generated)
    else:
        text = re.sub(r"<!-- INVENTORY_START -->.*?<!-- INVENTORY_END -->", lambda _: generated, text, flags=re.S)
    REPORT.write_text(text, encoding="utf-8")

    evidence = [f for r in rows for f in r["files"] if f.get("status") == 200] + [x for x in selected if x.get("status") == 200]
    for item in evidence:
        target = ROOT / item["local_path"]
        assert target.is_file(), target
        assert hashlib.sha256(target.read_bytes()).hexdigest() == item["sha256"], target
        assert not item.get("truncated"), target
    assert "INVENTORY_TABLE" not in text
    assert not re.search(r"\b(TODO|FIXME)\b", text)
    for href in re.findall(r"\]\(([^)]+)\)", text):
        if not href.startswith(("https://", "#")):
            assert (ROOT / href).exists(), href

    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    body = md.render(text)
    headings = []

    def heading(match):
        level, label = match.group(1), match.group(2)
        anchor = f"section-{len(headings)+1}"
        if level == "2":
            headings.append((anchor, re.sub("<[^>]+>", "", label)))
        return f'<h{level} id="{anchor}">{label}</h{level}>'

    # Only h2 receives navigation IDs, so IDs remain unique and stable per section.
    body = re.sub(r"<h(2)>(.*?)</h\1>", heading, body)
    body = re.sub(r"<p>&lt;!-- INVENTORY_(?:START|END) --&gt;</p>\n?", "", body)
    toc = "\n".join(f'<a href="#{anchor}">{label}</a>' for anchor, label in headings)
    document = '''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Second Brain — Açık Kaynak Araştırması</title><style>
    :root{color-scheme:light;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#172635;background:#eef2f5}*{box-sizing:border-box}body{margin:0}nav{position:fixed;top:0;bottom:0;left:0;width:250px;padding:28px 20px;overflow:auto;background:#142c3b;color:white}nav strong{display:block;margin-bottom:24px}nav a{display:block;color:#dce9f0;text-decoration:none;font-size:13px;line-height:1.5;margin:12px 0}main{max-width:1220px;margin-left:250px;padding:48px 48px 90px;background:white}h1{font-size:34px;line-height:1.2;letter-spacing:-.6px}h2{font-size:25px;border-top:1px solid #d8e1e6;padding-top:26px;margin-top:44px;scroll-margin-top:24px}h3{font-size:20px;margin-top:32px}p,li{font-size:16px;line-height:1.75}a{color:#075f88;overflow-wrap:anywhere}code{font:13px ui-monospace,Consolas,monospace;background:#f0f4f6;border-radius:3px;padding:2px 4px;overflow-wrap:anywhere}table{display:block;overflow-x:auto;border-collapse:collapse;width:100%;font-size:14px;margin:22px 0}th{background:#e9f1f5;text-align:left}td,th{border:1px solid #d8e1e6;padding:11px;vertical-align:top;line-height:1.55;min-width:145px}tr:nth-child(even){background:#f8fafb}strong{font-weight:650}li{margin-bottom:8px}@media(max-width:900px){nav{position:static;width:auto;padding:20px}nav a{display:inline-block;margin:7px 10px 7px 0}main{margin:0;padding:24px}h1{font-size:28px}}@media print{nav{display:none}main{margin:0;padding:0;max-width:none}body{background:white}table{display:table;font-size:10px}td,th{min-width:0;padding:5px}h2,h3{break-after:avoid}a{color:inherit}p,li{font-size:11px}}
    </style></head><body><nav><strong>SECOND BRAIN<br>26 Ekim 2026</strong>TOC</nav><main>BODY</main></body></html>'''
    document = document.replace("TOC", toc).replace("BODY", body)
    (ROOT / "SECOND_BRAIN_ARASTIRMA_RAPORU.html").write_text(document, encoding="utf-8")
    summary = {
        "repository_attempts": len(ledger["repositories"]),
        "public_repositories": len(rows),
        "standard_snapshots": sum(len(r["files"]) for r in rows),
        "selected_successful_snapshots": sum(x.get("status") == 200 for x in selected),
        "selected_successful_repositories": len({x["repo"] for x in selected if x.get("status") == 200}),
        "validated_evidence_records": len(evidence),
        "markdown_words": len(text.split()),
        "html_tables": body.count("<table>"),
        "html_sections": len(headings),
        "report_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
        "validation": "Local evidence digests, completeness and relative links verified; no cross-project execution benchmark performed",
    }
    (ROOT / "research-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

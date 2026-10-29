"""Render local evidence into reviewable source/license documentation."""

import json
from pathlib import Path

report = json.loads(Path("reports/source-registry.json").read_text("utf-8"))
reasons = {
    "Hindsight": "Reflection adayı; ek servis/LLM ve aynı corpus benchmark'ı yok, runtime'a eklenmedi.",
    "Mem0": "Gerçek yerel projection kullanıldı; infer=False, telemetri kapalı, canonical authority korunuyor.",
    "Supermemory": "Açık repo ile ayrı sunucu binary lisansı ayrıldı; binary kurulmadı.",
    "MemOS": "Geniş taxonomy/procedural referans; auth düzeltmesi bağımsız doğrulanmadan çalıştırılmadı.",
    "memU": "Skill distillation/file memory referansı; otomatik güvenilir kural üretimi benimsenmedi.",
    "LangMem": "Procedure optimization referansı; mevcut yerel reflection yerine zorunlu LangGraph kurulmadı.",
    "Letta": "Agent runtime'a kilitlenmemek için referans olarak kaldı.",
    "MIRIX": "Multimodal fikirler incelendi; sürekli ekran capture açık izinsiz etkinleştirilmedi.",
    "Honcho": "İlişkisel user-model yaklaşımı; ayrı runtime/lisans ve canonical ownership nedeniyle seçilmedi.",
    "Memori": "SQL açıklanabilirliği referansı; ikinci kanonik veritabanı eklenmedi.",
    "OmniMem": "Experience/failure ve propose-accept yaklaşımı özgün learning gate'e yansıtıldı; kod kopyalanmadı.",
    "MemPalace": "Verbatim/mining adayı; upstream kimliği güncel resmi depo ile düzeltildi, benchmark reprodüksiyonu yapılmadı.",
    "Graphiti": "Temporal projection adayı; graph backend/LLM yapılandırılmadığı için blocked.",
    "Cognee": "Belge/knowledge graph adayı; canonical bitemporal authority olarak kullanılmadı.",
    "GraphRAG": "Corpus/global reasoning adayı; basit kişisel retrieval için ek LLM maliyeti etkinleştirilmedi.",
    "LightRAG": "Graph+vector referansı; baseline'a ek kazanım ölçülmediğinden zorunlu runtime değil.",
    "HippoRAG": "Associative multi-hop retrieval adayı; aynı corpus üzerinde test edilmedi.",
    "A-MEM": "Zettelkasten linking fikri; canonical truth ve owner approval yerine geçirilmedi.",
    "KAG": "Ontology/logical retrieval adayı; kişisel şema için ağır ek runtime seçilmedi.",
    "EverOS": "Okunabilir arşiv ve rebuildable index fikri; özgün event/vault çekirdeği geliştirildi.",
    "ReMe": "File-as-memory/consolidation referansı; filtrelenmiş session kaydı lossless archive sayılmadı.",
    "Basic Memory": "Markdown/MCP referansı; AGPL kod runtime'a entegre edilmedi.",
    "OpenViking": "Progressive disclosure/context namespace fikri; ayrı engine kurulmadı.",
    "Memvid": "Portable artifact adayı; kendi backup/export biçimi kanonik kayıtların sahibi kaldı.",
    "Claude-Mem": "Lifecycle capture tasarım referansı; HTTP/binary parçaları çalıştırılmadı.",
    "Agent Skills": "Paket standardı benimsendi; upstream scriptler kopyalanmadı.",
    "rank-bm25": "Doğrudan kullanılan bağımsız BM25 implementasyonu.",
    "FastEmbed": "Doğrudan kullanılan ONNX CPU embedding katmanı.",
    "MCP Python SDK": "Doğrudan kullanılan gerçek stdio protocol server/client.",
    "FastAPI": "Doğrudan kullanılan yerel HTTP gateway ve Pydantic sözleşmeleri.",
    "Uvicorn": "Doğrudan kullanılan loopback ASGI sunucusu.",
    "Codex": "Resmi hook/App Server/MCP kaynak referansı; kullanıcı thread'leri okunmadı.",
    "Reflexion": "Feedback→lesson fikri; research code kullanılmadı.",
    "ExpeL": "Biriken evidence→insight fikri; research code kullanılmadı.",
    "Voyager": "Skill library/verifier fikri; oyun/runtime kurulmadı.",
    "TencentDB Agent Memory": "Chat/Skill/Wiki/Code-Graph varlık ayrımı referansı; takım servisi kurulmadı.",
    "RapidOCR": "Gerçek yerel CPU ONNX OCR; üretilmiş görsel ve taranmış PDF üzerinde test edildi.",
    "faster-whisper": "Gerçek tiny/int8 CPU konuşma dökümü; sentetik TTS üzerinde ağsız test edildi.",
    "PyAV": "Sabit container allowlist'i ile yerel ses decode ve video kare örnekleme; FFmpeg binary notices ayrıca envanterde.",
    "pypdfium2": "Taranmış PDF sayfalarının yerel render'ı; PDFium ve bundled bağımlılık notices korunur.",
}


def license_name(text):
    upper = text.upper()
    if "GNU AFFERO GENERAL PUBLIC LICENSE" in upper:
        return "AGPL-3.0 (dosya metni)"
    if "APACHE LICENSE" in upper and "2.0" in upper:
        return "Apache-2.0 (dosya metni)"
    if "MIT LICENSE" in upper or "TERMS OF THE MIT" in upper:
        return "MIT (dosya metni)"
    if "BSD" in upper or "REDISTRIBUTION AND USE IN SOURCE" in upper:
        return "BSD ailesi (tam metne bak)"
    return "Dosya mevcut; ifade elle incelenmeli" if text else "Dosya doğrulanamadı"


lines = [
    "# Source Registry",
    "",
    "Araştırma kanıtı ile çalıştırılan dependency birbirinden ayrılır. Aşağıdaki HEAD snapshot SHA'ları research snapshot'ıdır; kurulan wheel'in o commit olduğu iddia edilmez. Runtime sürümleri `requirements.lock` ile, yayımlanmış artifact hash'leri `reports/package-release-hashes.json` ile sabittir.",
    "",
    "Kontrol zamanı: " + report["checked_at"],
    "",
    "## Upstream değerlendirmesi",
    "",
    "| Proje / sabit kaynak | Son release referansı | Lisans kanıtı | Karar |",
    "|---|---|---|---|",
]
for row in report["candidates"]:
    repo = row["repository"].removeprefix("https://github.com/")
    folder = Path("third_party/upstream") / repo.replace("/", "--")
    license_text = (
        (folder / "LICENSE").read_text("utf-8", errors="replace") if (folder / "LICENSE").exists() else ""
    )
    license_path = row.get("license_source_filename", "LICENSE")
    release = ", ".join(row.get("recent_release_refs", [])[:2]) or "Release tag doğrulanmadı"
    lines.append(
        f"| [{row['name']}]({row['repository']}/tree/{row.get('commit', 'HEAD')}) · `{row.get('commit', 'unverified')}` | {release} | [{license_name(license_text)}]({row['repository']}/blob/{row.get('commit', 'HEAD')}/{license_path}) | {reasons.get(row['name'], 'Araştırma adayı; runtime değil.')} |"
    )
lines += [
    "",
    "## Kurulu paketler",
    "",
    "Tam transitif metadata, gereksinimler ve license dosya SHA-256 değerleri `reports/source-registry.json` içindedir. Orijinal kurulu lisans metinleri `third_party/licenses/` altında korunur. PyPI release hash kaydı indirilen her wheel'in yerelde yeniden hash'lenmesi yerine geçmez.",
    "",
    "| Paket | Sabit sürüm | Dağıtım metadata'sındaki lisans | Saklanan lisans dosyası |",
    "|---|---|---|---|",
]
for row in report["installed_packages"]:
    expression = (
        row.get("license_expression") or row.get("license_metadata") or "Belirtilmemiş; dosyayı incele"
    )
    expression = expression.splitlines()[0][:90].replace("|", "/")
    lines.append(f"| {row['name']} | {row['version']} | {expression} | {len(row['license_files'])} |")
lines += [
    "",
    "## Model ve standartlar",
    "",
    "Embedding modelinin gerçek snapshot ve dosya SHA-256 kayıtları `reports/model-manifest.json`, Whisper tiny ağırlıklarının revision ve SHA-256 kayıtları `reports/speech-model-manifest.json` içindedir. OCR ONNX dosyaları rapidocr-onnxruntime wheel'iyle gelir. Model kartı iddiaları bağımsız kalite benchmark'ı sayılmadı; gerçek yerel testlerin kapsamı TESTING.md ve MEDIA_PIPELINE.md içindedir.",
    "",
    "[Codex hooks](https://learn.chatgpt.com/docs/hooks), [App Server](https://learn.chatgpt.com/docs/app-server), [MCP](https://learn.chatgpt.com/docs/extend/mcp), [Claude hooks](https://code.claude.com/docs/en/hooks), [Gemini hooks](https://geminicli.com/docs/hooks/), [Cursor hooks](https://cursor.com/docs/hooks) entegrasyon yüzeyleri için resmi kaynaklardır. Canlı hesap erişimi bu belgelerin bulunmasından çıkarılmadı.",
    "",
    "Open Brain/OneBrain/Engram/Hippocampus gibi birden fazla projeye işaret edebilen isimler tek runtime bağımlılığına dönüştürülmedi. ProcMEM, LongMemEval/V2, LoCoMo, Memora/FAMA, SkillsBench, AFTER, SkillEvolBench ve MemLens araştırma yaklaşımı olarak değerlendirildi; dataset/code lisans ve yerel reprodüksiyonları bu teslimde doğrulanmadı. Bu nedenle dış benchmark sonuçları bizim sonuçlarımız olarak sunulmaz.",
]
Path("SOURCE_REGISTRY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

license_doc = """# Lisans denetimi

Özgün Second Brain OS kodu Apache-2.0 lisanslıdır; tam metin LICENSE içindedir. NOTICE ve dağıtımla gelen üçüncü taraf lisansları korunmalıdır.

Doğrudan kullanılan uygulamalar: FastAPI (MIT), Uvicorn (BSD ailesi), MCP Python SDK (MIT), rank-bm25 (Apache-2.0), FastEmbed (Apache-2.0), Mem0 (Apache-2.0). Kesin dağıtım sürümü ve kurulu license metni SOURCE_REGISTRY tablosu/third_party/licenses içinde incelenmelidir. Cryptography, NumPy, Pillow, PyPDF, python-docx, Qdrant ve tüm diğer transitif dağıtımlar ayrıca envanterdedir. Lisans metadata'sı tek başına tüm binary/vendored bağımlılıkların tam hukuki analizi değildir.

Medya extra'sı RapidOCR, faster-whisper/CTranslate2, PyAV/FFmpeg ve pypdfium2/PDFium binary'lerini ekler. Wrapper lisansı bundled codec/model/third-party bileşenlerin lisansı yerine geçmez. Kurulu dağıtımın LICENSE/COPYING/NOTICE dosyaları aynen korunur; özellikle FFmpeg ve PDFium'un ek koşulları dağıtım öncesi bu dosyalardan incelenmelidir. Çalışan geliştirme ortamının kaynak arşivi model veya üçüncü taraf wheel binary'lerini paketlemez.

AGPL lisans metni bulunan Basic Memory/OpenViking/Honcho gibi araştırma snapshot'ları runtime'a bağlanmadı. Referans dokümanının arşivde bulunması o servisin çalıştırıldığı anlamına gelmez. Ayrı process kullanmanın otomatik lisans muafiyeti sağladığı varsayılmadı. Supermemory açık repo lisansı ayrı local server binary'sine uygulanmış sayılmadı. Ticari dağıtım için paketlerin gerçek kullanım biçimi ve tüm notices yeniden incelenmelidir.

Gerçek sürüm/commit/lisans dosyası hash'leri reports/source-registry.json; PyPI release artifact SHA-256 değerleri reports/package-release-hashes.json; güvenlik taraması reports/dependency-audit.json içindedir. Bu kayıtlar eksiksiz hukuki uyumluluk sertifikası değildir. Docker base image ve işletim sistemi dağıtımının tam SBOM'u bu oturumda oluşturulmadı.
"""
Path("LICENSE_AUDIT.md").write_text(license_doc, encoding="utf-8")
Path("NOTICE").write_text(
    "Second Brain OS\nOriginal implementation: Second Brain OS contributors.\nThird-party runtime packages retain their original copyrights and licenses.\nSee SOURCE_REGISTRY.md, LICENSE_AUDIT.md and third_party/licenses/.\nUpstream research snapshots are attributed by repository and full commit in reports/source-registry.json.\n",
    encoding="utf-8",
)
model_manifest = Path("data/models/ready.json")
if model_manifest.exists():
    Path("reports/model-manifest.json").write_bytes(model_manifest.read_bytes())
speech_manifest = Path("data/models/speech/ready.json")
if speech_manifest.exists():
    Path("reports/speech-model-manifest.json").write_bytes(speech_manifest.read_bytes())
print("Source registry, license audit and model manifest written")

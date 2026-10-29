# Second Brain OS — teknik teslim raporu

**Güncel teslim: [30 Ekim 2026 v0.1.1 AI yönetimi ve gözlem arayüzü](reports/ai-managed-20261030/REPORT.md).** [v0.1.0 beta raporu](reports/beta-0.1/REPORT.md) ve aşağıdaki 26 Ekim sonuçları tarihsel kayıttır.

26 Ekim 2026, Windows üzerinde çalışan yerel sürüm 0.1.0. Uygulama `http://127.0.0.1:8765` adresinde başlatıldı ve kimlik doğrulaması, medya yetenekleri ve SQLite bütünlüğü gerçek çalışan süreç üzerinden kontrol edildi. Giriş anahtarı `data/owner.token` dosyasındadır; içeriği rapora veya kaynak paketine eklenmedi.

Bu teslim kullanılabilir bir yerel uygulamadır. Başlangıçtaki vizyonun bütün dış servis ve hesap bağlantılarının tamamlandığı iddia edilmez. Her bölümün durumu, modülü, kanıtı ve kalan sınırı [REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md) içindedir.

## Gerçek çalışan kapsam

| Alan | Çalışan davranış | Kanıt |
|---|---|---|
| Kanonik hafıza | Kalıcı SQLite olayları, kaynak hash'leri, ayrı aday/onay registry'si ve 12 bilgi türü | Olay, güven, concurrency ve API testleri |
| Veri alma | ChatGPT export dalları/metadata, PDF, DOCX, metin, kod, JSON/CSV, güvenli ZIP ve medya orijinalleri | Byte eşitliği, idempotency, traversal testleri |
| Zaman ve düzeltme | Valid/known eksenleri, geç bildirilen değişiklik, bounded correction ve çelişki | Geçmiş/şimdiki lexical ve gerçek vector sorguları |
| Arama | FTS5, bağımsız BM25, ilişki + RRF, gerçek ONNX CPU vector ve Mem0/Qdrant | Kaynaklı sonuç ve ACL testleri |
| Uzun metin | Tam metni kapsayan örtüşen embedding parçaları; kaynak karakter aralığı ve bağlam alıntısı | Belge sonundaki Türkçe bilgi için native/Mem0 recall; modelsiz lexical context |
| Öğrenme | Farklı evidence'lardan feedback→LESSON adayı→owner onayı | Üç kanıt ve poisoning testleri |
| Medya | Gerçek RapidOCR, taranmış PDF OCR, Whisper tiny/int8 ve video kare OCR | Gerçek CPU testleri ve `reports/media-evaluation.json` |
| Kuyruk | Kalıcı lease, retry/dead-letter, checkpoint, onay transaction'ında indeksleme outbox'ı, iptal | Ağır işlemde okuma/iptal, yarım import replay, iptal edilen token testleri |
| API/MCP | Aynı domain işlemlerini kullanan FastAPI gateway ve resmi SDK stdio MCP | Gerçek SDK subprocess→HTTP→DB testi |
| Capture | Dört host hook adaptörü, açık thread ID ile Codex read-only kolektör | Host fixtures ve gerçek Codex App Server initialize; özel thread okunmadı |
| Skill/tool | ZIP sürümleme, eski sürüme dönüş, state/export, compatibility ve binary/MCP envanteri | Paket round-trip ve capability testleri |
| Gizlilik | Ayrı hide/forget, lineage temizleme, tombstone, yönetilen backup temizliği ve restore replay | Silinen kaydın eski yedekten geri gelmemesi |
| Kurtarma | Parolalı AES-GCM snapshot, doğrulama, restore journal, migration ve rebuild | Bozuk parola/tag ve restore testleri |
| Arayüz | Türkçe 16 yönetim alanı, responsive, açık/koyu tema ve EN altyapısı | Gerçek CUA aday/onay akışı, medya kuyruğu ve ekran gözlemleri |

Geliştirilen çekirdeğin event/registry, bitemporal correction, trust gate, ACL, lineage deletion, backup/recovery, queue, context builder, dashboard ve adaptör orkestrasyonu özgün koddur. FTS5 SQLite'ın, BM25 rank-bm25'in, embedding FastEmbed/ONNX'in, Mem0 projection gerçek Mem0/Qdrant'ın, MCP resmi Python SDK'nın uygulamasıdır. Medya işlemcileri gerçek RapidOCR, faster-whisper/CTranslate2, PyAV ve PDFium'dur; başarı döndüren taklit servis kullanılmadı.

## Doğrulama

- **64 test geçti**, 0 başarısız/0 skip; bir beklenen local Qdrant payload-index uyarısı. JUnit: `reports/tests.xml`.
- Ruff, format, mypy `--ignore-missing-imports --check-untyped-defs`, JavaScript syntax ve PowerShell parser kontrolleri geçti. Mypy strict değildir.
- Kaynak odaklı secret taraması bulgu üretmedi. Bu tarama genel DLP veya tam güvenlik incelemesi sayılmaz.
- Kurulu 117 üçüncü taraf/Python dağıtımı için public release artifact hash kanıtı alındı; 40 upstream repo snapshot'ı kaydedildi. PyPI bağımlılık taramasında bilinen advisory bulunmadı. Uygulamanın kendi özel paketi PyPI'da olmadığı için pip-audit kapsamında değildir; bundled native codec ve OS açıklarının tam taraması yapılmadı.
- Kaynak paketine `.venv`, `data`, owner/master anahtarları, çalışma DB'si, kişisel export veya model ağırlıkları eklenmez. Kendi wheel'i ayrı kurulum hedefinden import edilerek statik dosyalar ve üç migration kontrol edilir; sonucu `reports/wheel-check.json` içine kaydedilir.

Gerçek kullanıcı sohbetleri, kişisel medya ve canlı model hesapları test verisi olarak kullanılmadı. CUA testi ayrı 8766 portundaki sentetik çalışma alanındaydı; ana çalışma alanında testin yazdığı kayıt sayısı sıfırdır. Her tıklama bağımsız kontrol ajanının açık hedef doğrulamasından sonra yapıldı. `reports/qa-media-candidate.png` sentetik PNG'den gerçek OCR ile çıkan onay bekleyen kaydı gösterir.

## Ölçülen tüketim ve kalite sınırı

Yerel servis ilk açılıştaki read-only smoke ölçümünde yaklaşık **66,3 MiB çalışma kümesi** ve **0,516 CPU saniyesi** kullandı; bu bir peak ölçümü değildir. OCR/PDF/video/altı saniyelik sentetik TTS deneyinin son noktasında yaklaşık **260,9 MiB çalışma kümesi**, toplam **6,125 CPU saniyesi** ölçüldü. Dört işin yaklaşık süreleri 1,566 / 0,677 / 0,588 / 0,855 saniyedir. Bunlar bu cihazda, küçük sentetik örneklerdir; büyük dosya veya Türkçe ses doğruluğu garantisi vermez.

500 soruluk sentetik şablon regression ve 10.000 olay/10.000 assertion performans raporları [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md) içindedir. Subject kimlikleri soruları kolaylaştırır. Son 100 soruluk validation tekrarında FTS/BM25/hybrid regression kontrolleri geçti. Bu sonuçlar genel doğal dil anlama veya son LLM cevabında %100 doğruluk olarak yorumlanmamalıdır. 10k corpus'ta p95 FTS 3,687 ms, BM25 216,504 ms, hybrid 390,127 ms ölçüldü; bu karşılaştırmada model çağrısı yoktu.

Embedding/Mem0/ses inference çalışma anında kişisel veri yüklemez. Mem0 testi Python socket bağlantıları engellenerek çalıştırıldı; dış bağlantı girişimi olmadı. Harici model API harcaması yapılmadı. İlk kurulumda açık paket ve ağırlık dosyaları indirilir.

## Düzeltilen sorunlar

İlk geliştirme turlarında Windows SQLite bağlantı kapanışı, skill SQL placeholder sayısı ve lexical OR eşleşmesinin ilgisiz sayı parçalarını getirmesi yakalandı ve düzeltildi. İlk hatalı benchmark kanıtı korunur. Bu turda PyAV 19'un kaldırdığı decoder parametresi, uzun metnin model penceresinde kesilmesi, ağır işin DB kilidini tutması ve iptal edilen token'a bağlı bekleyen işler düzeltildi. Son test takımında çözülmemiş başarısız test yoktur.

## Açık kalanlar

- Gerçek ChatGPT/Claude/Gemini/Cursor hesabı veya host ayarı etkinleştirilmedi. MCP protokolü testlidir; iki canlı modelin davranış karşılaştırması yapılmadı. ChatGPT'nin tüm normal sohbetlerini evrensel pasif yakalama desteği yoktur.
- Graphiti backend/LLM, Hindsight ve Supermemory gibi ek runtime'lar çalışır entegrasyon diye gösterilmez. Kaynak kararları ve lisans ayrımı SOURCE_REGISTRY içindedir.
- Serbest doğal dilde üretken extraction/reflection ve otomatik skill synthesis için doğrulanmış yerel üretken LLM yoktur. Açık tercih sözdizimi ve tekrarlanan feedback akışı çalışır. Arbitrary skill scriptleri otomatik çalıştırılmaz; compatibility, yürütme başarısı sayılmaz.
- OCR genel nesne/scene açıklaması değildir. Video 15 saniye arayla örneklenir. Gerçek Türkçe ses benchmark'ı yapılmadı. İşlem bütçeleri MEDIA_PIPELINE içindedir.
- Kanonik SQLite/FTS/vector alanları plaintext'tir. Orijinaller AES-GCM, yedekler parola ile şifrelidir. OS/harici kopyalar ve fiziksel SSD forensic silme denetlenmez.
- Docker/Linux/macOS runtime çalıştırılmadı; CI/Compose tanımı vardır. Çok cihaz sync, çok kullanıcılı SaaS provisioning, tam İngilizce çeviri ve her güç kesintisi noktası tamamlanmadı.

## Çalıştırma ve son bağlantılar

Bu bilgisayarda `scripts/Start.ps1 -Background` gizli arka plan sunucusu başlatır ve sağlık yanıtını bekler; adres localhost 8765'tir. Yeni kurulum için INSTALLATION.md ve Setup.ps1 kullanılır. Başka bilgisayarda ilk paket/model indirmesi gerekir.

Owner anahtarıyla giriş yap. Gizlilik bölümünde yalnız gerekli scope'lara sahip model token'ı üret; owner anahtarını host config'ine koyma. `client-config` örneklerini mevcut ayarlara birleştir ve host'un hook güven akışını kendin etkinleştir. Uzak ChatGPT MCP için hesap desteği, OAuth ve güvenli hosting ayrı çalışmadır. Bu adımlar gerçekleşmiş veya bütün hesaplar bağlı gibi raporlanmadı.

Özgün kod Apache-2.0'dır. Lisans dosyaları ve notices `third_party` altında korunur. Sabit model kartları ve hash'leri `reports/model-source-evidence.json` içindedir. Wrapper lisansının bütün native bağımlılıkları kapsadığı varsayılmaz; kaynak paketi bu binary'leri yeniden dağıtmaz.

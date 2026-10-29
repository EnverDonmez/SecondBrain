# Test ve doğrulama

v0.1.1 AI yönetimi: 228 test ve dört araçlı gerçek HTTP/stdio kabulü; [güncel rapor](reports/ai-managed-20261030/REPORT.md). İnsan ekranı salt okunur olarak, üç bölüm ve mobil görünümle ayrıca doğrulandı. Önceki sayılar tarihsel kayıttır.

v0.1 beta: [kabul koşulları](BETA.md), [sonuç raporu](reports/beta-0.1/REPORT.md). `scripts/Verify.ps1` tam regresyonu; `scripts/verify_beta.py` gerçek HTTP/stdio üzerinden sentetik günlük kullanım akışını sınar. `scripts/check_wheel.py` kurulan wheel'in bütün uygulama dosyalarını mevcut kaynakla karşılaştırır. Önceki tarihli test sayıları aşağıda tarihsel kayıttır.

28 Ekim 2026 mimari sadeleştirme turu: dört araçlı MCP, koşullu bağlam, şema 7, alias/özellik kimliği, tekrar kanıtı, güncel sürüm bağlantıları, silme/rebuild ve opsiyonel modülleri yüklemeyen çekirdek için [rapor ve ölçümler](reports/coherent-memory-20261028/REPORT.md). Tekrar üretim: `scripts/Verify.ps1`, `scripts/evaluate_coherent_memory.py`, `scripts/verify_coherent_connection.py`. Eski test turları aşağıda tarihsel kayıttır.

28 Ekim 2026 açık kullanıcı beyanı turunda **171 test geçti**: [rapor](reports/direct-statements-20261028/REPORT.md), [JUnit](reports/direct-statements-20261028/tests.xml), [canlı MCP şema/izin kontrolü](reports/direct-statements-20261028/live-connection.json). Sıradan açık beyanların ikinci onay olmadan kaydı, 3 → 4 güncellemesi, geçmişi koruma, eski istekte geri almama ve HTTP/MCP kısıtlı token akışı doğrulandı. Eski sonuçlar aşağıda tarihleriyle korunur.

27 Ekim 2026 kanıt erişimi turunda **133 test geçti**: [mühendislik raporu](reports/engineering-20261027/ENGINEERING_REPORT.md), [JUnit](reports/engineering-20261027/tests.xml), [canlı MCP sözleşmesi](reports/engineering-20261027/live-connection.json). Yeni 16 regresyon, konu gürültüsü/doğrudan kanıt, açık bağlantı, eski kaynak, ihtilaf, paket eksikliği, yazar metadata'sı ve eşzamanlı düzeltmeyi kapsar. Önce/sonra dört tanısal senaryo ve 5.001 kayıtlı yerel ölçüm genel QA başarısı değildir.

Kişisel veritabanı yön değişiminde önceki **117 test geçti**: [rapor](reports/MEMORY_DATABASE_2026-10-26.md), [JUnit](reports/directory-tests.xml), [canlı harita/kaynak doğrulaması](reports/directory-live-connection.json).

Ekonomik mod güncellemesinde **105 test geçti**: [sonuç ve kapsam](reports/ECONOMY_2026-10-26.md), [JUnit](reports/economy-tests.xml), [5.001 kayıtla ölçüm](reports/economy-evaluation.json). Aşağıdaki önceki tur sonuçları tarihsel kayıttır.

Son devam turunda **96 test geçti**; [güncel rapor](reports/COMPLETION_2026-10-26.md), [JUnit](reports/completion-20261026/tests.xml). Semantik süreçte UTF-8, eşzamanlılık, boşta gerçek Python sürecinin kapanması ve yeniden yükleme; ders gruplama, negatif/sayı sınırları, cache invalidation, scope/clearance ve kısıtlı Codex yapılandırması kapsanır. Önceki 88 testlik düzeltme turu [tarihsel rapordadır](reports/GOAL_FIXES_2026-10-26.md).

26 Ekim 2026 kullanıcı hedefleri kabul denetimi [ayrı sonuç raporunda](reports/GOAL_TEST_REPORT_2026-10-26.md) tamamlandı: yeniden çalıştırılan 64 uygulama testi geçti; 15 ek kabul koşulunun 11'i karşılandı, 4'ü açık kaldı. Rapor doğal Türkçe çıkarım/hatırlama, global/proje bağlamı, skill/tool taşınabilirliği, canlı veri durumu ve kaynak maliyetini ayrıca değerlendirir. Uygulama testlerinin geçmesi bütün ürün hedeflerinin karşılandığı anlamına gelmez.

```powershell
.\scripts\Verify.ps1
.\.venv\Scripts\python.exe -m second_brain --data reports benchmark --split all
.\.venv\Scripts\python.exe -m second_brain --data reports benchmark --performance
```

`reports/tests.xml` gerçek JUnit sonucudur. Test adları ve süreleri burada korunur. Ruff, format check, mypy `--check-untyped-defs` ve JavaScript syntax kontrolü uygulanır. Mypy strict modda değildir; Pydantic sınırları typed, bazı servis içi dictionary'ler dinamiktir.

## Test türleri

| Alan | Kanıt |
|---|---|
| Olay/asset kayıpsızlığı | Byte eşitliği, şifreleme ve SHA-256 |
| Idempotency | Aynı export, source ID ve çok thread'li capture |
| Bitemporal | Mart/Haziran/Eylül, geçmiş known-time, bounded correction |
| Çelişki | Açık supersedes olmadan farklı assertion'ın disputed kalması |
| Yetki | Scope/tenant/clearance, modelden approve/delete/admin reddi |
| Injection | Belge → user policy/preference terfisinin reddi; secret quarantine |
| Import | ChatGPT dalları, metadata, bilinmeyen attachment pointer'ı, ZIP traversal |
| Öğrenme | Üç farklı evidence, candidate lesson, explicit approval |
| Skills | ZIP export, sürüm/state, capability eksikliği ve execution_verified ayrımı |
| HTTP | Gerçek FastAPI uygulamasında auth, CSRF, Host, şema ve export |
| MCP | Resmi SDK istemcisi, gerçek subprocess stdio ve loopback HTTP |
| Yerel motor | Gerçek ONNX embedding + gerçek Mem0/Qdrant ingest/search/delete |
| Kurtarma | Parola/tag bozulması, restore, güncel erasure replay, yeniden import reddi |
| Migration | 1→7 ve 6→7 yükseltme, ham alanları koruma, idempotent migrate, daha yeni schema reddi |
| Uzun belge | Belge sonundaki gerçek semantic eşleşme, Mem0/native chunk retrieval ve kaynaklı context |
| Multimodal | Gerçek görsel/PDF/video OCR ve sentetik TTS; orijinal eşitliği, timestamp, replay dedup, iptal ve silme |
| Token iptali | İptal edilen credential'a bağlı kuyruğun durması, kaynakların kendiliğinden işlenmemesi |
| Property | ISO tarih normalizasyonu için Hypothesis örnekleri |
| UI | Ayrı sentetik sunucuda create→candidate→approve→active; her tıklama bağımsız alt ajan kontrolü |

Opsiyonel engine testi model dosyası yoksa skip olur; bunun sonucu gerçek engine integration başarısı sayılmaz. Buradaki Windows çalıştırmasında model vardı ve test çalıştı. Qdrant local payload index uyarısı raporlanır; hata diye gizlenmez veya server performansı gibi yorumlanmaz.

Önceki yerel tam çalıştırmalardan birinde 96 test geçti, 1 beklenen Qdrant uyarısı. Medya deneyinin metinleri/süreleri ve kaynak byte eşitliği `reports/media-evaluation.json` içindedir. Medya extra'sı olmayan minimal CI ortamında gerçek medya testleri skip edilir; yerelde extra ve ses ağırlığı kurulu olarak çalıştı.

## Koşul ve sınırlamalar

Windows sandbox, Python socketpair oluşturmayı engellediğinde HTTP testleri application koduna ulaşmadan bekledi. Aynı sentetik testler izinli loopback ortamında çalıştırıldı. İlk çekirdek testleri bir Windows SQLite connection kapanış hatası ve skill SQL placeholder hatası buldu; ikisi düzeltildi. İlk benchmark false-positive sorunu da saklanan önceki raporda görünür.

Gerçek kullanıcı sohbeti, canlı Claude/Gemini/Cursor uygulaması, dış Graphiti servisi, Docker, Linux/macOS runtime, üretken LLM answer judge, SSD forensic erase, her noktada güç kesintisi ve çok kiracılı adversarial servis testi yapılmadı. CI tanımı eklemek CI'ın GitHub üzerinde çalıştığı anlamına gelmez.

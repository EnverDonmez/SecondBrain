# Second Brain — kişisel bilgi veritabanı

Second Brain, konuştuğun AI'nın proje kararlarını, tercihlerini ve kaynaklarını oturumlar arasında bulmasını sağlar. Dört MCP aracı yerel SQLite deposuna bağlanır. Sen Özet, Yapılanlar ve Hafıza ekranlarından değişiklikleri izlersin. [Günlük kullanım](USER_GUIDE.md) · [Mimari](ARCHITECTURE.md) · [10 Kasım güncelleme raporu](reports/UPDATE_2026-11-10.md)

## Başlat

Python 3.12+ kurulu yeni bir Windows bilgisayarda önce bağımlılıkları kur:

```powershell
.\scripts\Setup.ps1
```

Ardından uygulamayı başlat:

```powershell
.\scripts\Start.ps1 -Background
```

[Yerel uygulama](http://127.0.0.1:8765) adresini aç. Giriş anahtarı `data/owner.token` dosyasındadır. Bu sahip anahtarını modellere verme. Yeni bilgisayarda önce `scripts/Setup.ps1` çalıştır. Varsayılan kurulum model indirmeyen çekirdektir; yerel medya ve semantik motorlar için `-Full` kullan. Tanılama: `.\.venv\Scripts\python.exe -m second_brain doctor`.

## Çalışan kapsam

- Ham olaylar, şifreli orijinaller, içerik hash'leri ve idempotent ChatGPT ZIP/JSON import.
- Kaynaklı aday → inceleme → onay akışı; dış belge ve model çıkarımı için ayrı güven sınıfları.
- Valid/known time sorguları, geç bildirilen düzeltmeler, çelişki ve sürüm geçmişi.
- SQLite FTS5, bağımsız rank-bm25, birleşik arama ve yerel çok dilli CPU embedding.
- Gerçek Mem0 2.2.1 + yerel Qdrant projection; LLM çıkarımı ve telemetri kapalı.
- Uzun belgelerin tamamında örtüşen parçalarla semantik arama; onay sonrası kalıcı indeksleme işi.
- Gerçek yerel görsel/PDF OCR, ses dökümü ve zamanlı video kare OCR; orijinaller ve aday inceleme sınırı korunur.
- Bütçeli “Beynimi tara”, profil/proje bağlamı ve stdio MCP araçları.
- Codex, Claude Code, Gemini CLI, Cursor hook normalizasyonu; Codex App Server item adaptörü.
- Kalıcı iş kuyruğu, lease/retry/dead-letter, checkpoint ve yeniden indeksleme.
- Skill ZIP sürümleri, enable/disable, rollback için eski sürümü seçme, bağımlılık/yetenek denetimi.
- Şifreli yedek, bütünlük kontrolü, geri yükleme, silme günlüğü replay ve yönetilen eski yedeklerin silinmesi.
- Türkçe responsive yönetim arayüzü, açık/koyu tema ve İngilizce arayüz altyapısı.

## Doğrulama ve sınırlar

Tarihsel araştırma ve teslim kayıtları `reports/` altında saklanır. [Beta kapsamı](BETA.md) · [Veritabanı sözleşmesi](MEMORY_DATABASE.md)

Gerçek protokol, veritabanı, dosya ve yerel model testleri çalıştırıldı. Testler kişisel konuşmalar yerine sentetik veri kullanır. [Test raporu](reports/tests.xml), [benchmark](BENCHMARK_RESULTS.md), [gereksinim öz denetimi](REQUIREMENTS_AUDIT.md) ve [bilinen sınırlar](KNOWN_LIMITATIONS.md) teslimin parçasıdır.

ChatGPT'nin tüm normal sohbetlerini pasif yakalama desteklenmiyor. Bu bilgisayardaki Codex MCP bağlantısı kurulu; diğer istemciler için örnekler `integrations/` altındadır. Kişisel kaynaklar kaydedilmeye başlandı; bütün eski sohbetlerin içeri aktarıldığı varsayılmaz. Otomatik hook kurulumu yapılmadı. Graphiti backend'i, yerel üretken LLM ve gerçek model cevap karşılaştırmaları hazır değil. Yerel OCR/ses/video işlemlerinin test kapsamı ve kalite sınırları [medya belgesinde](MEDIA_PIPELINE.md) açıklanır.

Kanonik SQLite ve FTS alanları **plaintext** tutulur. Ham binary dosyalar AES-GCM, yedekler parola türetilmiş anahtarla şifrelenir. Tam cihaz koruması için işletim sistemi disk şifrelemesi gerekir. Bu uygulama kimlik bilgisi kasası değildir.

## Belgeler

[Kurulum](INSTALLATION.md) · [Kullanım](USER_GUIDE.md) · [Mimari](ARCHITECTURE.md) · [Yapılandırma](CONFIGURATION.md) · [API](API_REFERENCE.md) · [MCP](MCP_REFERENCE.md) · [Şema](MEMORY_SCHEMA.md) · [Capture](CAPTURE_ADAPTERS.md) · [Motorlar](MEMORY_ENGINES.md) · [Skills](SKILL_SYSTEM.md) · [Güvenlik](SECURITY.md) · [Gizlilik](PRIVACY.md) · [Kurtarma](BACKUP_RECOVERY.md) · [Kaynaklar](SOURCE_REGISTRY.md) · [Lisans](LICENSE_AUDIT.md)

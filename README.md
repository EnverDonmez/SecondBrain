# Second Brain — kişisel bilgi veritabanı

**v0.1.1 beta:** Bilgileri konuştuğun AI yönetir; sen Özet, Yapılanlar ve Hafıza ekranlarından izlersin. Elle kayıt ve sınıflandırma gerekmez. Bu bilgisayarda `Start.cmd` dosyasını çift tıkla. [Beta kullanımı ve kapsamı](BETA.md) · [Güncel teslim raporu](reports/ai-managed-20261030/REPORT.md).

Ana hedef: konuştuğun AI'nın tercihlerini, projelerini, konuşma kaynaklarını, skill ve araç bilgilerini ortak bir veritabanından, genelden özele ve düşük bağlam maliyetiyle bulması. **Harita → kayıt kartı → kaynak ayrıntısı** erişimi, kalıcı konuşma kaynakları ve tarihli düzeltmeler için [veritabanı sözleşmesi](MEMORY_DATABASE.md). Yönetim ekranı yardımcıdır; ayrı bir sohbet modeli çalıştırılmaz.

Güncel mimari: **tek SQLite deposu, dört AI aracı ve varsayılan modelsiz erişim**. Özellik kimliği, tekrar kanıtı, güncel sürüm bağlantıları ve değişmeyen bağlamı tekrar taşımayan güncellik kontrolü için [mühendislik raporu](reports/coherent-memory-20261028/REPORT.md), [ADR 0006](docs/adr/0006-coherent-memory.md). Aşağıdaki eski tur sonuçları tarihsel kayıttır.

[Ekonomik hafıza modu](ECONOMY_MODE.md): bilgiyi konuştuğun AI seçer; tek çağrıda kaynaklı kayıt adayları, varsayılan modelsiz indeks/grafik araması ve bütçeli bağlam. AI bağlantıları sayfasında taşınabilir talimat ve manuel JSON aktarımı bulunur. Ayrı ücretli model çağrısı yapılmaz; mevcut sohbet hizmetinin kullanımı devam eder.

Önceki araştırma ve test turları `reports/` altında tarihsel kanıt olarak korunur. Güncel beta doğrulaması `reports/beta-0.1/` altındadır.

Yerel, modelden bağımsız bir hafıza uygulaması. Kanonik gerçeklik SQLite içinde; arama motorları değiştirilebilir projection olarak çalışır. Kullanıcının asıl veri dizini `data/`dır ve sentetik test verisi buraya eklenmez.

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

Gerçek protokol, veritabanı, dosya ve yerel model testleri çalıştırıldı. Testler kişisel konuşmalar yerine sentetik veri kullanır. [Test raporu](reports/tests.xml), [benchmark](BENCHMARK_RESULTS.md), [gereksinim öz denetimi](REQUIREMENTS_AUDIT.md) ve [bilinen sınırlar](KNOWN_LIMITATIONS.md) teslimin parçasıdır.

ChatGPT'nin tüm normal sohbetlerini pasif yakalama desteklenmiyor. Bu bilgisayardaki Codex MCP bağlantısı kurulu; diğer istemciler için örnekler `integrations/` altındadır. Kişisel kaynaklar kaydedilmeye başlandı; bütün eski sohbetlerin içeri aktarıldığı varsayılmaz. Otomatik hook kurulumu yapılmadı. Graphiti backend'i, yerel üretken LLM ve gerçek model cevap karşılaştırmaları hazır değil. Yerel OCR/ses/video işlemlerinin test kapsamı ve kalite sınırları [medya belgesinde](MEDIA_PIPELINE.md) açıklanır.

Kanonik SQLite ve FTS alanları **plaintext** tutulur. Ham binary dosyalar AES-GCM, yedekler parola türetilmiş anahtarla şifrelenir. Tam cihaz koruması için işletim sistemi disk şifrelemesi gerekir. Bu uygulama kimlik bilgisi kasası değildir.

## Belgeler

[Kurulum](INSTALLATION.md) · [Kullanım](USER_GUIDE.md) · [Mimari](ARCHITECTURE.md) · [Yapılandırma](CONFIGURATION.md) · [API](API_REFERENCE.md) · [MCP](MCP_REFERENCE.md) · [Şema](MEMORY_SCHEMA.md) · [Capture](CAPTURE_ADAPTERS.md) · [Motorlar](MEMORY_ENGINES.md) · [Skills](SKILL_SYSTEM.md) · [Güvenlik](SECURITY.md) · [Gizlilik](PRIVACY.md) · [Kurtarma](BACKUP_RECOVERY.md) · [Kaynaklar](SOURCE_REGISTRY.md) · [Lisans](LICENSE_AUDIT.md)

# Bilinen sınırlar

v0.1.1: Günlük arayüz gözlem içindir; düzenlemeyi bağlı AI yapar. `organize` sınırlı metadata düzenlemesidir; açık kullanıcı onayı olmadan model/belge kuralı geçerli kullanıcı kuralı olamaz. Konuşmadaki yazar ve hedef eşlemesi bağlı istemci tarafından bildirilir; dil guard'ları genel niyet/yazar doğrulaması değildir. Ana ekranda kaynaklar ve son sürümler bütçeli gösterilir; daha eski/uzun ayrıntılar AI'nın mevcut sayfalı kaynak okumasından alınabilir. [Rapor](reports/ai-managed-20261030/REPORT.md).

30 Ekim 2026 v0.1 beta: Windows tek kullanıcı/yerel servis kapsamındadır. MCP otomatik başlatması ana istemcinin süreç ömrüne bağlı olabilir; Windows SDK istemci kapanırken alt servisi sonlandırabilir. AI oturumundan bağımsız kullanım için Start.cmd kullanılır. Yeniden açılışta yarıda kalan işler aynı kimlik ve checkpoint ile yeniden kuyruğa alınır. Güncel kabul kanıtı [beta raporundadır](reports/beta-0.1/REPORT.md). Genel serbest dil doğruluğu, tüm sohbetlerin pasif toplanması ve yıl boyu eksiksiz hatırlama kabul iddiası değildir.

28 Ekim 2026 sade sözleşme turu: [ADR 0006](docs/adr/0006-coherent-memory.md). `known_state` yalnız model önceki paketi koruyorsa kullanılabilir; aksi halde tam bağlam tekrar istenir. Anahtar normalizasyonu genel anlamsal eşdeğerlik değildir; bilinmeyen kişi/özellik alias'ları tahmin edilmez. Değişen dayanak bağlantısı görünür olur fakat bağımlı çıkarım otomatik yeniden yazılmaz. Varsayılan araç sayısının azalması ve paket byte ölçümü, belirli bir AI sağlayıcısının faturasında tasarruf garantisi vermez. Önceki sonuçlar aşağıda tarihsel olarak korunur.

28 Ekim 2026: [açık kullanıcı beyanı kabulü](docs/adr/0005-direct-user-statements.md) sıradan bilgi ve güncellemelerde ikinci onay beklemez. Varsayılan aday modu ve korunan davranış/skill değişiklikleri incelemede kalır. Alıntı/niyet/özellik seçiminde bağlı AI'ya güvenilir; guard'lar genel dil/yazar doğrulaması değildir. Bu tur [171 testle](reports/direct-statements-20261028/REPORT.md) doğrulandı; eski adaylar topluca etkinleştirilmedi.

27 Ekim 2026: [kanıt erişimi turu](reports/engineering-20261027/ENGINEERING_REPORT.md) doğrudan/graf sıralamasını, eski kaynak ilgililiğini, görünür ihtilaf/eksiklik durumunu ve tek süreçte tutarlı bağlam derlemeyi ekledi. 133 test ve küçük sentetik önce/sonra ölçümü geçti; bu, yıl boyu genel QA doğruluğu değildir. İhtilaf işareti genel doğal dil çelişki algılama sağlamaz; inceleme durumunun geçmişini tam bitemporal kurmaz. Doğrudan eşleşmeler bir sayfayı doldurursa graf komşuları sonraki sayfada kalabilir.

Son yön değişimi: [ortak kişisel veritabanı sözleşmesi](MEMORY_DATABASE.md), hiyerarşik harita/kart/kaynak erişimi, kalıcı konuşma kaynakları ve çalışma noktaları eklendi. [117 test ve canlı bağlantı raporu](reports/MEMORY_DATABASE_2026-10-26.md) kapsamı belirtir. Geçmişin tamamı import edilmedi; desteklenen bağlantı olmadan bütün platformlar otomatik yakalanmaz.

Ekonomik mod güncellemesi: konuşma modelinin seçtiği kaynak alıntıları `brain.remember` ile aday olarak alınır; `economy` indeksli ve sınırlı grafik araması varsayılandır. Bu özellik genel doğal dil çıkarımını programın içinde çözmez, pasif sohbet yakalama sağlamaz ve bütün platformlara otomatik bağlanmaz. [Akış, maliyet sınırı ve grafik sınırlamaları](ECONOMY_MODE.md).

Bu teslim tüm vizyonun tamamlandığı iddiasında bulunmaz. Kullanılabilir yerel uygulama, testler ve gerçek birkaç motor/protokol entegrasyonu vardır; aşağıdaki gereksinimler açık kalır.

| Konu | Durum / gerekçe |
|---|---|
| ChatGPT tüm sohbetlerinin pasif capture'ı | unsupported; evrensel resmi hook doğrulanmadı |
| Kullanıcının AI hesaplarına bağlanma | Codex yerel MCP kısıtlı anahtarla kuruldu ve gerçek protokol okuması doğrulandı. Yeni host oturumunda yüklenmesi, gerçek model cevabı ve otomatik capture doğrulanmadı; diğer istemciler kurulmadı. |
| Codex App Server backfill/watch | explicit-thread read-only kolektör ve gerçek initialize testi var; kullanıcı thread'inde history/poll ve canlı coverage testi yapılmadı |
| ID'siz hook'ların lossless + replay-dedup garantisi | ikisi aynı anda ispatlanamaz; arrival'lar ayrı saklanır, duplicate olasılığı açık |
| Graphiti temporal projection | backend/LLM yok; installed/verified adapter olarak gösterilmez |
| Hindsight/Supermemory/MemOS/memU vb. | kaynak değerlendirmesi var, runtime entegrasyonu yok |
| Mem0 | gerçek local projection var; LLM extraction/reflection, full benchmark ve prod yük testi yok |
| Semantic model | 128 token pencere örtüşen parçalarla aşılır; uzun belge sonu retrieval testi geçti, curated genel kalite ölçülmedi |
| Genel doğal dil extraction | explicit syntax ve sınırlı doğrudan Türkçe tercih kalıpları aday üretir; soru/alıntı/olumsuz ifadenin tersine yorumlanması için guard'lar var, genel dil anlama yok; Ollama gerçek LLM testi yapılmadı |
| Otomatik skill üretimi/verifier | repeated lesson candidate çalışır; üretken skill synthesis ve arbitrary sandbox execution yok |
| Farklı ifadelerde öğrenme | İki sınırlı workflow eşdeğerliği ve 0,88 eşikli ihtiyatlı yerel embedding gruplaması var; tüm Türkçe ifadelerde anlam/çelişki çözümü yok. Kaynaklar, scope, actor, hassasiyet, sayılar ve bazı karşıt değerler ayrılır; etkinleştirme onay gerektirir. |
| Skill capability kurulumu | dependency discovery var; yeni credential/araç otomatik kurulduğu iddia edilmez |
| Görsel OCR | Gerçek RapidOCR ve taranmış PDF OCR doğrulandı; genel nesne/scene vision modeli ve Türkçe OCR kalite benchmark'ı yok |
| Ses/video | Gerçek tiny/int8 konuşma dökümü + örneklenmiş kare OCR var; yalnız sentetik İngilizce TTS testli, Türkçe kayıt doğruluğu ve tüm video olaylarını kapsama iddiası yok |
| Git repo ingestion | kaynak dosyaları/arşivi import edilir; repository symbol/call graph parser ve incremental Git watcher yok |
| Çok kullanıcı / cihaz sync | namespace tabanı var; multi-user auth provisioning ve conflict-free multi-device sync yok |
| Restore | normal akış ve deletion replay testli; tüm elektrik kesintisi noktaları testli değil |
| Büyük yedek | 100 MiB upload / 300 MiB expanded ZIP bütçesi; streaming backup yok |
| Tam at-rest encryption | binary/backup şifreli; canonical SQLite/FTS/vector plaintext; DPAPI/SQLCipher yok |
| Unmanaged kopyalar | dış export, OS snapshot, eski harici backup ve üçüncü taraf kopyalar denetlenemez |
| Frontend | çalışan buildless JavaScript; TypeScript ve tüm sabit metinler için tam EN çeviri yok |
| Benchmark | 500 sentetik şablon sorusu; curated bağımsız kalite veya final LLM judge değil |
| Platformlar | Windows test edildi; Docker/Linux/macOS CI tanımı var, runtime testi yapılmadı |
| Internet deployment | OAuth/remote MCP hosting yapılmadı; servis loopback ile sınırlı |

Bu sınırlamalar arayüzde motor/işlemci durumları, capability raporları ve ilgili dokümanlarda da gösterilir. Eksik bir servise sahte sağlık veya benchmark sonucu verilmez.

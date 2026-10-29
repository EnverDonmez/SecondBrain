# ADR 0007 — Beta servis yaşam döngüsü

Tarih: 30 Ekim 2026. Durum: kabul edildi.

## Problem

Doğru MCP kataloğu yüklenmiş olsa bile yerel HTTP servisi kapalı olduğunda hafıza araçları çalışmıyordu. Önceki başlatıcı her seferinde yeni süreç açıyordu; paket kontrolü ise şema 4'te kalmıştı. Başarılı çekirdek testleri günlük açılış ve güncel dağıtımın çalıştığını tek başına göstermiyordu.

## Karar

Tek sahipli HTTP servis mimarisi ve SQLite kanonik deposu korunur. Yeni mikroservis, model veya kanonik veri kopyası eklenmez. `service.py`, CLI ve açıkça etkinleştirilen MCP autostart için ortak başlatma/sağlık kontrolüdür. `healthz`, veri yolunun hash'ini, uygulama sürümünü ve PID'yi verir; yolun kendisini veya anahtarları yayınlamaz. Sağlık eşleşmiyorsa çalışan süreç değiştirilmez. `service.lock`, aynı veri dizini için ikinci sunucuyu engeller.

Bağımsız arka plan servisi Start.cmd/Start.ps1 ile açılır. MCP autostart mutlak veri yolu ve açık bayrak ister; ana istemcinin süreç politikalarını aşmaz. Windows SDK Job Object politikası, istemci kapanırken alt servisi de kapatabilir. Bu nedenle MCP autostart, oturumdan bağımsız kalıcı Windows servisi olarak sunulmaz.

Tek servis başlangıcında `running` kalan işler `pending` yapılır. İş kimliği, payload, deneme sayısı, dedup anahtarları ve checkpoint korunur. Worker başlamadan önce yapılır; iptal edilmiş işler geri açılmaz. İşleme başlamadan mevcut credential tekrar doğrulanır.

Kurulum varsayılan olarak çekirdek bağımlılıkları çözer. `-Full` ve `-Dev` ek yetenekleri açıkça seçer. Veritabanı şeması 7'de kalır. Paket doğrulaması sabit eski şema yerine kaynakta bulunan tüm migration ve uygulama dosyalarıyla eşitliği kontrol eder.

## Kanıt

`tests/test_beta.py`, `scripts/verify_beta.py`, `scripts/check_wheel.py` ve `reports/beta-0.1/`.

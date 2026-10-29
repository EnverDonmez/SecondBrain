# Veri sahipliği ve gizlilik

Kullanıcının gerçek konuşmaları bu geliştirme oturumunda import edilmedi, benchmark'a eklenmedi veya dış API'ye yüklenmedi. UI test fixture'ı `.test-tmp/ui-qa`, testler `.test-tmp/`, benchmark geçici beyinleri `reports/` altındaki geçici dizinlerde çalışır. Uygulamanın `data/` beyni başlangıçta kullanıcı içeriği olmadan bırakılır.

Kanonik verinin sahibi kullanıcıdır. Dışa aktarım hesap veya motor lisansına bağlı değildir. JSON/JSONL içerik ve metadata, Markdown okunabilir assertion geçmişi, encrypted backup tam asset bytes'larını taşır. Token ve owner credential'ları normal export'a eklenmez; backup token tablosunu temizler, restore mevcut token revocation durumunu korur.

## Üç farklı işlem

- **Correction/invalidation:** yeni assertion ve zaman aralıkları; eski bilgi tarihsel kanıt olarak kalır.
- **Hide:** güncel transaction görünümünü kapatır; geçmiş bilerek korunur.
- **Permanent forget:** kaynak olay, assertion ailesi, ortak raw asset, vector/FTS/graph, ilişkili feedback/skill ve job sonuçlarını siler. Tombstone yalnız kimlik/hash taşır.

Shared evidence için conservative closure uygulanır: bir ZIP tüm orijinal export'u taşıyorsa yalnız bir cümleyi saklayıp aynı bytes içinde bırakmak silme sayılmaz. Bu nedenle aynı raw asset'e bağlı diğer olay/hafızalar da kapsam önizlemesine dahil edilir. Yönetilen eski `.sbbackup` dosyaları silinir. Yeni yedek silinmiş içerik taşımaz.

Silme günlüğü snapshot'tan ayrı tutulur; eski backup dönse de replay yapılır. SSD wear-leveling, işletim sistemi disk snapshot'ları, dosya geçmişi, daha önce dışarı indirilmiş export/yedekler veya üçüncü taraf kopyaları fiziksel olarak kontrol edilemez. Bu kopyaların silindiği iddia edilmez. Unutulan aynı asset hash'i otomatik yeniden import edilmez; “forget then relearn” için yeni açık kaynak olayı gerekir.

Servis ve MCP telemetrisi uygulama tarafından eklenmez; Mem0 telemetry adaptör import'undan önce kapatılır. İlk pip/model/GitHub indirmeleri ağ kullanır; runtime çekirdeği çevrimdışı çalışır. Ücretli bulut model sağlayıcısı devreye alınmadı.

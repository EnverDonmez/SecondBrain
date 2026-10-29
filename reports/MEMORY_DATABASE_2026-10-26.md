# Kişisel veritabanına yön değişimi — 26 Ekim 2026

Ana ürün hedefi [MEMORY_DATABASE.md](../MEMORY_DATABASE.md) içinde sabitlendi: farklı AI'ların kullanıcı ve projeler hakkında kaynaklı, kalıcı, katmanlı bir veritabanına başvurması. Yönetim arayüzü yardımcıdır; yeni bir sohbet uygulaması veya ayrı düşünme modeli hedeflenmez.

## Yapılan değişiklik

- `brain.navigate`: başlık → proje/kapsam → hiyerarşik konu → kısa kayıt kartı. Üst başlığın kendi kayıtları ayrıca açılır, sayfalama/bütçe yüzünden kayıt kaybolmaz.
- `brain.read`: yalnız seçili kayıt veya kaynaktan birebir karakter aralığı, bütçe ve devam konumu. Skill tanımı okumak çalıştırma izni vermez; tool ayarları/credential adları yönlendirme metnine taşınmaz.
- `brain.remember`: kaynak ve çalışma noktası, `facts=[]` ile de kalıcı saklanabilir. Kaynak hemen aranır; yapılandırılmış tercih/karar adaylarının etkinleşmesi hâlâ sahip onayına bağlıdır. Özet ve AI yorumu onaylı kullanıcı kuralı sayılmaz.
- Konuşma/source indeksi yaş nedeniyle eski kayıtları elemez. Somut görev bağlamı yalnız onaylı kayıtlarla sınırlı kalmaz: ilgili kaynak parçalarını açık güven etiketiyle ve toplam bütçeyle sunar.
- Geçmiş kaynakta eski bir karar varsa güncel bilgi ailesine yönlendiren `current_memory_refs` eklenir. Tarih sorguları ve açık geçmiş erişimi eski/güncel ayrımını korur.
- Şema 6: artımlı konu yolları, kaynak-bilgi eşlemeleri ve kaynak arama indeksi. İzin/revizyon/tarih anahtarlı, sınırlı LRU harita önbelleği; kaynak, bilgi, skill ve tool değişikliğinde yenilenir. Gelecekte geçerli olacak kaydın tarih sınırında da sona erer.
- Kaynak olarak saklanmış fakat yapılandırılmış bilgiye dönüşmemiş kayıt da owner-only silme sınırına dahildir. Silme indeksleri, önbelleği ve otomatik tekrar içeri almayı kapsar.
- MCP sunucu talimatı kişisel geçmişi veritabanından doğrulama ve anlamlı yeni konuşma bilgisini checkpoint/kaynakla kaydetme akışına çevrildi. Mevcut Codex bağlantısına yalnız `brain.navigate`/`brain.read` eklendi; erişim kapsamı/anahtar ve onaylama/silme yetkileri genişletilmedi.

## Kanıt

[Tam test sonucu](directory-tests.xml): **117 test geçti**, bir beklenen yerel Qdrant uyarısı. Ruff lint/format, mypy `--check-untyped-defs`, JavaScript syntax ve secret taraması geçti; secret bulgusu 0.

Yeni kabul testleri şunları doğrular:

- 2024 tarihli bir kaynak, çok sayıda 2026 kaydı eklendikten sonra da sorgu ve tarih filtresiyle bulunur; özgün metnin ilgili aralığı açılır.
- Harita → alt konu → kart → kaynak akışı tüm içeriği başta taşımaz. Üst konu kayıtları ve alt başlık sayfaları kaybolmaz.
- Düzeltmeden sonra geçmiş sürüm, güncel karar diye sunulmaz; açık tarih/geçmiş sorgusuyla korunur. Eski kaynak güncel kararın referansını verir.
- Yetki, tenant, kapsam ve hassasiyet harita sayımlarında/önbellekte de korunur. Gizli ve karantinadaki kaynaklar modele taşınmaz.
- Unicode kaynaklar bütçeli aralıklardan birebir yeniden birleştirilir. Önbellek yazma, silme, tool durumu ve gelecek tarih geçişinde yenilenir.
- Etkin skill/tool metadata'sı gövde ve credential ayarlarından ayrı okunur; yetki kazanımı oluşturmaz.
- Gerçek MCP SDK subprocess → HTTP yolunda yeni harita ve okuma araçları çalışır.

[Canlı bağlantı sonucu](directory-live-connection.json): yeni sürüm çalışan yerel sunucuya uygulandı; yapılandırılmış kısıtlı MCP komutuyla araçlar ve yeni talimat keşfedildi. Kullanıcının bu konuşmada verdiği gerçek proje tarifi bir kaynak ve iki tercih adayı olarak kaydedildi, tekrar çağrı çoğaltmadı. Kaynak haritadan bulundu, birebir metin aralığı okundu ve görev bağlamına **1.534 byte** olarak taşındı (2.400 byte bütçe). Kişisel veritabanına sentetik kayıt eklenmedi. Adaylar otomatik onaylanmadı.

## Henüz iddia edilmeyenler

Kullanıcının eski bütün sohbetleri, dosyaları veya dışarıdan kurduğu bütün skill/tool'lar içeri alınmış değildir. Bağlanmamış platformlarda otomatik capture yoktur. Bu tur, platform istemcilerinin her konuşmada talimata uyduğunu veya gerçek bir yıllık kişisel geçmişte kusursuz cevap verdiğini kanıtlamaz. 2024 senaryosu sentetiktir; gerçek kaynaklar ancak yetkili capture/import/remember yolu ile gelir. Kullanılan sağlayıcının toplam token faturası ölçülmedi; ayrı ücretli hafıza modeli çağrısı eklenmedi.

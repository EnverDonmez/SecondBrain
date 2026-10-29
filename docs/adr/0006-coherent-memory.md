# ADR 0006 — Tek kişisel bilgi deposu ve dar AI sözleşmesi

Tarih: 28 Ekim 2026. Durum: uygulandı.

## Amaç

Konuşulan AI değişse de kaynaklar, tercihler, proje durumu ve skill/tool envanteri aynı yerel depodan alınır. Yeni bir model çalıştırmak, her tur tüm arşivi yüklemek veya ayrı bir graf servisi kurmak gerekmez. Kaynaklı ve tarihli erişim, kusursuz doğal dil hatırlama garantisi vermez.

## Karar

Varsayılan MCP yüzeyi yalnız `prepare_context`, `remember`, `navigate`, `read` sunar. Yönetim arayüzü ve eski uzman motorlar korunur; `SB_MCP_PROFILE=full` eski araçları açıkça seçmek içindir. Yetki denetimleri her iki profilde aynıdır. Dört araç, kaynak kaydı → özellik sürümü → erişim projeksiyonu → bütçeli bağlam zincirini kapsar. Skill destek dosyaları `read(kind=skill,id,path)` ile okunur.

Şema 7, ham `subject/predicate/value` alanlarını değiştirmeden `subject_key/predicate_key` üretir. Anahtarlar harf/ayırıcı farklarını ve dar bir kullanıcı özelliği alias listesini normalleştirir; kişi adlarını anlamsal benzerlikle birleştirmez. Sahip tarafından birleştirilmiş varlık alias'ları yazma, arama ve yeniden indekslemede aynı çözümleyiciyi kullanır. Çakışan aktif iddialar sessizce seçilmez. Scope, tenant ve hassasiyet sınırları korunur.

Aynı özellikte **birebir aynı değer** tekrar söylendiğinde yeni assertion sürümü oluşturulmaz; yeni kaynak `statement_receipts` ile mevcut assertion'a bağlanır. Silme, export ve kaynak okuma bu kanıt ilişkisini de kapsar. Farklı sözcüklerle benzer anlatımın eşdeğer olduğu varsayılmaz.

`related_memory_ids` tarihsel kanıtı korur. `memory_links` projeksiyonu düzeltme sonrası geçerli sürüm ailesine yönelir. Geçmiş tarih sorgusu tarih filtresini yine uygular. Eski bir kaynağa bağlı sonuç `related_version_changed` ile işaretlenir; `read` erişilebilir `related_current_refs` verir. Bağımlı kararın metni otomatik yeniden yazılmaz.

Her tur `prepare_context` çağrılır. Model önceki **tam aynı paketi halen tutuyorsa**, aynı istekle `known_state` gönderebilir. Görünür revizyonlar ve yaklaşan zaman sınırları değişmemişse yalnız `unchanged=true` ve durum/bütçe bayrakları döner; kaynak metni tekrar taşınmaz. Sorgu, scope, bütçe, parametreler veya okuyucu değişirse taze paket döner. Süreç başlangıcı/restore, alias veya indeks onarımı da eski durumu geçersizleştirir. Tarihli sorgu, küçük bütçe ve uzman motor sorguları her zaman yeniden hazırlanır. Durum, okuyucu ve istek parametrelerine bağlı opak HMAC'tir; gizli scope değişikliklerini açığa çıkarmaz.

## Sınırlar

SQLite tek kanonik depodur; FTS, yönlendirme, graf ve bağlam sayaçları türevdir. Ek paket/model/servis eklenmedi. NumPy, BM25 ve medya modülleri çekirdek açılış yolundan çıkarılarak gerektiğinde yüklenir. Önceden kurulu opsiyonel motorları veya kullanıcı verilerini silmek bu kararın kapsamında değildir.

Bu yapı Kruskal veya yapay sinir ağı kullanmaz. FTS ile doğrudan kanıt seçimi ve sınırlı graf gezinmesi kullanır; graf bağlantısı doğruluk veya nedensellik kanıtı değildir. Kaynaklar/kurallar eksikse paket bunu bildirir. AI entegrasyonu olmayan platformdan otomatik yakalama, tüm yıl süren QA doğruluğu ve gerçek sağlayıcı faturasındaki tasarruf test edilmedi.

## Kanıt

`tests/test_coherent_memory.py`: revizyon, okuyucu/scope izolasyonu, gelecekteki zaman geçişi, tekrar kanıtı, alias çakışması, migration, graf sürümü, silme/rebuild, skill dosyası ve sade açılış. `tests/test_mcp.py`: gerçek SDK stdio + HTTP ile çekirdek ve full profiller. Tekrar üretim ve ölçümler [mühendislik raporunda](../../reports/coherent-memory-20261028/REPORT.md).

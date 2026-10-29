# ADR 0008 — AI yönetimi ve insan için gözlem ekranı

30 Ekim 2026 · Kabul edildi · v0.1.1 beta.

Kullanıcı hafızayı elle düzenlemek istemiyor. Konuştuğu AI'nın kayıt ve düzenlemeleri yapmasını, insan arayüzünün yapılanları göstermesini istiyor. Tek SQLite deposu, mevcut AI'nın kullanılması ve dört araçlı erişim korunur; uygulamaya ayrı sohbet modeli eklenmez.

## Ürün davranışı

Ana ekran üç salt okunur bölümdür: Özet, Yapılanlar ve Hafıza. Kayıt oluşturma/düzeltme/onay, JSON aktarımı, motor karşılaştırmaları ve yönetim formları ana gezinmeden çıkarıldı. Kaynak, sürüm geçmişi ve AI'nın metadata değişiklikleri görüntülenebilir. Bilgiyi değiştirmek için kullanıcı AI ile konuşur. Eski yönetim arayüzü yalnız yerel bakım/kurtarma için `/maintenance` adresinde korunur; bu ekran günlük bir işlem gereksinimi değildir ve sahibi için mevcut kimlik doğrulamasını kullanır.

## AI işlemleri

`brain.remember` mevcut kayıt için tek bir `change` kabul eder; aynı istekte yeni facts ile karıştırılmaz. `organize` yalnız konular ve açık kayıt bağlantılarını düzenler. Kullanıcı veya AI açıklaması kaynakta aynen bulunmalıdır. Değer, kimlik, tür, kapsam, gizlilik ve asıl kanıt listesi değişmez. Önce/sonra metadata ve kaynak olayı aynı audit zincirinde tutulur. Yeni erişim kapsamı, araç yürütme, kimlik bilgisi veya admin yetkisi verilmez.

`approve`, `reject`, `hide`, belirli kayıt için konuşmadaki açık kullanıcı talimatı gerektirir. AI belge metnini veya kendi açıklamasını kullanıcı onayı sayamaz. Ucuz dil guard'ları alıntı, soru, ihtimal, bariz olumsuz komut ve genel yetki devrini engeller; bunlar genel dil/yazar doğrulaması değildir. Kullanıcının kısa yanıtının hangi kayda karşılık geldiğini bağlı istemci belirler; belirsizliği konuşmada netleştirmelidir. Kaynağın yazarı hâlâ istemci tarafından bildirilir, bağımsız kimlik kanıtı değildir.

Onaylanan AI çıkarımı `MODEL_INFERENCE/inferred` kalır. Belge/model içeriği kullanıcı kuralına yükseltilmez; karantina engeli korunur. `hide` yalnız kullanımdan kaldırır, geçmiş ve orijinaller kalır. Kalıcı silme ve diğer yönetim uçları kısıtlı model token'larına açılmaz.

Bekleyen kayıtlar `navigate(branch=review)` ve `read(include_pending=true)` ile açıkça, onaylanmamış kanıt olarak açılır. Varsayılan onaylı arama davranışı korunur. Scope/tenant/gizlilik filtreleri ve byte bütçesi uygulanır. Aynı talimatın tekrarı audit makbuzunu kullanır ve sonraki düzenlemeyi geri almaz. Metadata düzenlemesi hatırlama indekslerini aynı transaction içinde yeniler.

Yeni change kaynakları ve önce/sonra metadata, silme kapanımına ve eski yedekten silme günlüğü tekrarına dahil edilir. Özet ekranı API okuma gürültüsünü filtreler; yetkili bağlantı ile gerçekten görülen son erişimi ayırır. Yeni bir gerçeklik kopyası oluşturulmaz.

Kanıt: `tests/test_ai_managed.py`, gerçek stdio/HTTP kabulündeki AI düzenleme ve konuşarak onaylama adımları, `reports/ai-managed-20261030/`.

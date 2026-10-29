# Second Brain — ortak kişisel bilgi veritabanı

28 Ekim 2026 mimari düzenlemesi: [ADR 0006](docs/adr/0006-coherent-memory.md). Varsayılan AI sözleşmesi dört araçtır. Özellik anahtarları farklı yazımları tutarlı çözer, birebir tekrarlar yeni kaynak kanıtı ekler, düzeltmelerde bağlantılar geçerli sürümlere yönelir. `known_state`, önceki paket eldeyse değişmeyen bağlamın tekrar taşınmasını önler; her tur güncellik kontrolü sürer. [Ölçüm ve doğrulama](reports/coherent-memory-20261028/REPORT.md).

Amaç, farklı AI'ların kullanıcıyı ve çalışmalarını eski sohbetleri yeniden tarayarak tahmin etmek yerine kaynaklı bir kişisel veritabanından tanımasıdır. Asıl ürün veritabanı, onun erişim sözleşmesi ve bilgiyi koruyan yaşam döngüsüdür. HTTP/MCP ince bir erişim katmanıdır; yönetim ekranı yardımcı bir inceleme aracıdır. Yeni AI sohbet uygulaması veya ayrı düşünme modeli geliştirmek kapsam dışıdır.

## Bilginin yaşam döngüsü

1. Bağlı konuşma modeli yeni anlamlı bilgiyi kısa, gerçek bir kaynak alıntısıyla `brain.remember` üzerinden kaydeder. `conversation_id`, biliniyorsa gerçek konuşma kimliğidir; bilinmiyorsa uydurulmaz. `checkpoint`, amaç/tamamlanan iş/açık mesele/sonraki adımı taşıyan kısa bir istemci özetidir.
2. Ham kaynak kalıcıdır ve yaşlandığı için aramadan çıkarılmaz. `facts=[]` kullanılabilir: kaynak hemen aranabilir olur; kullanıcı hakkındaki doğrulanmış bilgi gibi yükseltilmez. Kayıtlar yalnız açık silme/gizleme kurallarıyla erişimden çıkar.
3. Açık kullanıcı beyanları `assertion=direct_user` ile sıradan bilgi/tercih/proje durumu/karar olarak ikinci onay beklemeden etkinleşebilir. Aynı özelliğin tek uygun güncel kaydı varsa yeni sürüm onun yerini alır; eski bilgi geçmişte korunur. Belirsiz çıkarımlar, davranış kuralları ve skill/prosedür değişiklikleri inceleme gerektirir. Bir kaynak alıntısının istemciden bildirilmesi bağımsız yazar doğrulaması değildir. [Kabul ve güncelleme sözleşmesi](docs/adr/0005-direct-user-statements.md).
4. Her yazmada ilgili konu yolları, bağlantılar, kaynak eşlemeleri ve arama indeksleri güncellenir. Yeni bir model çağrısı veya bütün hafızayı yeniden özetleme yapılmaz. Konuşma modelinin seçimi/özetlemesi mevcut sohbet kullanımını tüketebilir.
5. Düzeltme eski sürümü ezmez. Valid time bilginin hangi dönemde geçerli olduğunu, known time o bilginin ne zaman öğrenildiğini saklar.

Kaynaklar özete bağımlı değildir. Çalışma noktası yanıltıcı veya eksikse özgün alıntıya dönülebilir. Henüz yakalanmamış sohbet, dosya, skill veya aracın veritabanında olduğu iddia edilmez.

## Genelden özele erişim

`brain.navigate` küçük başlıklar ve kartlar döndürür. Varsayılan bütçe toplam serileştirilmiş yanıt için 1.800 konservatif UTF-8 byte'tır.

```json
{"branch":"root","budget":1200}
{"branch":"projects"}
{"branch":"projects","key":"atlas"}
{"branch":"topics","scope":"atlas"}
{"branch":"topics","scope":"atlas","key":"work/atlas"}
{"branch":"topics","scope":"atlas","key":"work/atlas/storage"}
```

Bu örnekler yalnız örnektir; `atlas` adlı gerçek projenin varlığını göstermez. Başlıklar veriden oluşur. `Work/Atlas/Storage` gibi konu yolları yazma sırasında indekslenir. Alt başlıkları olan bir üst konunun kendi kayıtları `records=true` ile açılabilir. `more=true` ise `next_offset` izlenir; sayfa/bütçe nedeniyle gösterilmeyen içerik silinmez.

Kök harita tercihler/kurallar, projeler, konular, bilgiler/kararlar, konuşmalar/çalışma noktaları, etkin skill'ler ve araçlar için izinli sayımları verir. Başlıkta tüm kayıt içerikleri, skill gövdeleri veya tool ayarları taşınmaz. Bir proje kartı ilgili kapsamın konu dizinine işaret eder. Kayıtlar birden çok konu ve kaynak üzerinden bulunabilir; tek bir ağaç dalına hapsedilmez.

`brain.read` seçilmiş kartı veya kaynağı açar:

```json
{"kind":"memory","id":"gercek-kayit-kimligi","characters":1200,"budget":2400}
{"kind":"event","id":"gercek-kaynak-kimligi","query":"Orion teslim tarihi"}
```

Dönen metin kaynakta birebir bulunan karakter aralığıdır. `start_char`/`end_char` ve `next_offset` ile ayrıntı alınır. Üretilmiş bir özet özgün kaynakmış gibi gösterilmez. Geçmiş kaynak okunduğunda, aynı bilgi ailesinde erişilebilir güncel bir düzeltme varsa `current_memory_refs` gösterilir. Skill okuma çalıştırma izni, tool kataloğu da mevcut oturumda çalıştırılabilirlik garantisi vermez.

Somut görev için `brain.prepare_context` tek çağrıda onaylı ilgili bilgiler/kurallar ve bütçeye sığan kaynak alıntılarını derler. Görevle ilgili olmayan bütün skill/tool envanterini tekrar tekrar taşımaz. Kaynak alıntıları `episodes` altında `source_only`, çalışma noktaları `client_summary` güveniyle ayrılır; onaylı kurallarla karıştırılmaz. Genel kurallar eksikse `policy_context_complete=false` bilgisi korunur.

Bağlam şeması 2'de `truncated=true`, bilinen aday/sonuçların veya kaynak metninin tamamının taşınmadığını belirtir. `false` eksiksiz arama garantisi değildir. Doğrudan eşleşmeler graf komşularına kota açmak için elenmez; graf kaydı `via_memory_id`, `relation`, `graph_depth` ile neden bulunduğunu gösterir. Aynı adımdaki açık bağlantı, varlık ve konu bağlantısından önce gelir. Kaynaklı iddianın `review_required=true` olması, erişilebilir disputed alternatifin inceleme beklediği anlamına gelir; alternatif bu işaretle onaylanmaz. Kaynakların yazar ve yakalama yolu istemciden bildirilmiştir. [Karar ve sınırlar](docs/adr/0004-evidence-before-expansion.md).

## Bir yıl önceki bilgi ve düzeltmeler

- Sorguda yaş nedeniyle puan düşürme veya arşivi dışarıda bırakma uygulanmaz. Bir yıl önceki kaynak indekslenmiş ve izinliyse bugün de aranabilir.
- Konuşma kaynağı için `since`/`until` olay tarihini, `known_at` kaynağın sisteme ne zaman girdiğini sınırlar. Sonradan içeri alınan eski bir konuşma, daha önce de sistem tarafından biliniyormuş gibi gösterilmez.
- Yapılandırılmış bilgide `valid_at` geçmişte geçerli bilgiye, `known_at` o tarihte bilinen sürüme erişir. `include_history=true` geçmişte onaylanmış sürümleri açıkça ister. Geçmiş bir kuralı bulmak onu bugün geçerli yapmaz.
- Kaynakta eski karar bulununca güncel düzeltme bağlantısı kontrol edilir. Çelişkide kesinlik uydurulmaz; kayıt ve tarih belirtilir.

## Otomatik düzenleme ve maliyet

Konu yolları, kaynaklar ve kavram/FTS indeksleri kayıt sırasında artımlı güncellenir. Sık tekrarlanan harita istekleri en fazla 64 girdilik LRU önbellekten karşılanır. Önbellek anahtarı tenant, kullanıcı yetkileri, kapsam, hassasiyet, tarih/sorgu ve veri revizyonunu içerir. Kayıt, kaynak, skill veya tool değişikliği eski önbelleği geçersiz kılar. Gelecekte etkinleşen bilginin tarih sınırında da önbellek sona erer.

Bu düzenleme ilişki icat etmez, az kullanılan eski kaynakları silmez ve bilinmeyen bir semantik model çağrısına geçmez. Aynı konuyu tutarlı adlandırma ve bağlantıları seçme görevi mevcut konuşma modelindedir. Gerçek sağlayıcı token sayacı kullanılmadığından bütçeler konservatif byte sınırıdır; ağ protokolü/araç tanımları ve modelin düşünme kullanımı ayrıca maliyet yaratabilir.

## Kapsam ve gerçek sınırlar

Bu sistem her AI platformuna kendiliğinden bağlanamaz. Yetkili MCP/hook/import yolu ve modelin kayıt/okuma sözleşmesine uyması gerekir. Yeni oturumun araç kataloğunu yüklemesi gerekebilir. Şu anda bu bilgisayardaki Codex bağlantısı doğrulanır; diğer platformlar kurulmadan bağlı sayılmaz. İlk geçmiş veriler import edilmeden kullanıcının tüm geçmişinin bilindiği varsayılamaz.

Hatasız hatırlama, hiç veri kaybı veya her zaman aynı gecikme garanti edilmez. Eksik yakalama, yanlış konu/özet, çelişki, disk kaybı ve izin sınırları vardır. Temel ölçütler geçmiş kaynak bulunabilirliği, güncel/geçmiş ayrımı, erişim doğruluğu, yanıt bütçesi ve gereksiz içerik yüklememe olmalıdır. Yönetim arayüzüne yeni özellik eklemek bu ölçütlerin yerine geçmez.

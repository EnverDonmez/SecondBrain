# ADR 0004 — Kanıtı koruyan sınırlı erişim

Tarih: 27 Ekim 2026. Durum: uygulanmış; bağımsız uzun dönem kalite değerlendirmesi açık.

## Problem

Eski economy sıralaması, sonuç sayısının yarısını doğrudan eşleşmeler yerine graf komşularına ayırıyordu. Yaygın konu düğümleri ilgisiz ama önemli kayıtları öne çıkarabiliyordu. Konuşma araması anahtar kelime eşleşmesinden sonra yalnız tarihle sıralanıyordu; eski, özgül bir kaynak yeni zayıf eşleşmelerin arkasında kalabiliyordu. Sahip incelemesinde disputed kalan alternatif, onaylı değeri kullanan bağlamda görünmüyordu.

## Karar

Tek kanonik SQLite korunur. Yeni runtime/model/servis bağımlılığı eklenmez. Kaynaklar ve onaylı bilgiler farklı sınıflar olarak sunulmaya devam eder.

1. FTS başlangıç penceresi sayfa boyutundan bağımsız 48 kayıttır. Doğrudan eşleşmeler komşulara zorunlu kota vermez; komşular sonraki sonuçları doldurur.
2. Aynı graf adımında açık `related_memory_ids` bağlantısı, ortak varlıktan; ortak varlık, ortak konudan önce gelir. Bunlar doğruluk puanı değil, açıklanabilir erişim öncelikleridir. Toplam yüklenen aday sınırı 96, adım sınırı ikidir.
3. Graf sonucu `via_memory_id`, `relation`, `graph_depth` taşır. Yolun her ara kaydı erişilebilir ve istenen zamanda etkin olmalıdır. Bir ilişki, cümlelerin eşdeğer veya doğru olduğunu kanıtlamaz.
4. Konuşma sorgusu, yaşa göre eleme yapmadan FTS5 BM25 ile; eşitlik halinde tarihle sıralanır. Boş sorgu tarih sırasını korur.
5. `review_required=true`, aynı erişim/zaman sınırında halen disputed alternatif bulunduğunu belirtir. Alternatifin kimliği veya değeri bu sinyalle açılmaz; onaylı değer değiştirilmez. Bu işaret yeni bir kullanıcı kuralı değildir.
6. Bağlam şeması 2, `truncated` alanını içerir. Bilinen sonuçların bütçeye sığmaması, pencerenin doyması veya alıntıyla kısaltılması görünürdür. `false`, eksiksiz hatırlama ispatı değildir. `policy_context_complete` yalnız onaylı kuralların taşınmasını anlatır.
7. Kaynak okumaları yakalama yolunu ve `actor_is_client_reported=true` bilgisini taşır. Mevcut alım yolları yazarı bağımsız doğrulamaz; metadata bu bayrağı false yaparak kendisini güvenilir kılamaz.
8. Desteklenen tek API sürecinde bağlam derleme, DB kilidi içinde gerçekleşir. Aynı anda bir onay/düzeltme/silme, yarısı önceki yarısı sonraki sürümden bir paket üretmez. Bu, çok süreçli/cihazlı snapshot protokolü değildir.

## Araştırmayı nasıl kullandık?

- [memU servis ayrımı](https://github.com/NevaMind-AI/memU/blob/42ef9fa3a8034f5817684cba23ef69fa70a58197/src/memu/app/service.py): düşünme mevcut ajanda; bu uygulamadaki erişim/yazma yolunda ayrıca üretken model yok. memU'nun embedding servisi kurulmadı.
- [Titen kaynak/iddia modeli](https://github.com/RamaAditya49/titen/blob/23302a16d44d01f3759ef56287847f85352d0fc1/docs/architecture/memory-model.md): aday, onaylı iddia ve ham kaynak ayrımını; görünür eksiklik ve inceleme durumunu sözleşmede koruduk.
- [OpenViking katmanları](https://github.com/volcengine/OpenViking/blob/5c066d97094d713238c483c10691d7b4e1cfbf6e/docs/en/concepts/03-context-layers.md) ve [Basic Memory kompakt keşfi](https://github.com/basicmachines-co/basic-memory/blob/9643ec25918e8958629a668e3ce928981ab3ea36/src/basic_memory/mcp/tools/context.py): mevcut harita → kart → kaynak yaklaşımı korundu; tam gövdeler yerine ihtiyaç duyulan kanıtın açılması esas alındı.

Bunlar tasarım referanslarıdır. Upstream kod kopyalanmadı, bu dört ürünün birlikte entegre edildiği veya benchmark'larının tekrarlandığı iddia edilmez. [Araştırma raporu](../../reports/research-20261026/SECOND_BRAIN_ARASTIRMA_RAPORU.md).

## Trade-off ve açık işler

Doğrudan eşleşmeler bir sayfayı doldurursa önemli graf komşusu sonraki sayfada kalabilir. Pencere doygunluğu/`more` görünürdür; doğru adım kapsamı daraltmak veya seçili kaydı açmaktır. Ortak konuya sınırsız yayılma, doğrudan kanıtları tekrar bastırmamalı. PPR/embedding ancak bu tercihin kaçırdığı sorular aynı bütçede ölçülünce değerlendirilir.

`review_required`, yalnız aynı subject/predicate/scope altında kaydedilmiş ve halen disputed durumda olan alternatifleri yakalar. Doğal dilde genel çelişki bulucu değildir. İnceleme durumunun tüm geçmişi bitemporal olarak sürümlenmediğinden geçmişte çözülmüş bir ihtilafı o günkü durumuyla yeniden kurduğu söylenmez; `known_at` sonradan öğrenilmiş alternatifleri dışarıda tutar.

FTS sıralaması anlam doğruluğu garantisi vermez. Türkçe ekler/eş anlamlılar, alias yönlendirmesi, kapsam seçimi, kaynak yakalama kapsamı, çok adımlı kanıtların tamamı ve gerçek token faturası ayrıca ölçülmelidir. Kaynaklar yaş/erişim sıklığı nedeniyle silinmez.

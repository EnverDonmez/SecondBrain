# Second Brain — kanıt erişimi mühendislik raporu

27 Ekim 2026. Amaç: modelin hafızaya başvururken ilgisiz bağlantılar, eski kararlar ve açıklanmayan eksikliklerle karışmasını azaltmak.

## Uygulanan değişiklik

- Doğrudan FTS eşleşmelerinin yarısının konu komşuları için elenmesi kaldırıldı. Sayfa boyutundan bağımsız 48 başlangıç kaydı kullanılıyor; bütün graf adayları toplam 96 ile sınırlı.
- Aynı graf adımında açık kayıt bağlantıları, ortak varlık ve ortak konudan önce geliyor. Her komşu hangi kayıt üzerinden ve hangi ilişkiyle bulunduğunu bildiriyor. Aynı scope/tenant/clearance/onay/zaman filtreleri ara düğümlerde de korunuyor.
- Konuşma sorgusunda BM25 ilgililiği tarihten önce geliyor. Yaş nedeniyle kaynak düşürülmüyor; boş sorgunun tarih sırası korunuyor.
- `review_required`, aynı yetkili kapsam/zaman içinde halen disputed alternatif bulunduğunu bildiriyor. Onaylı değer değişmiyor; alternatifin kimliği/değeri bu sinyalle paylaşılmıyor.
- Bağlam şeması 2'de `truncated`, bilinen sonucun bütçeye sığmadığını, aday penceresinin doyduğunu veya metnin alıntıyla kısaltıldığını gösteriyor. False, eksiksizlik garantisi değil.
- Kaynak okuma, alım yolu ve istemciden bildirilen yazar durumunu gösteriyor. İstemci metadata'sı kendi yazarını bağımsız doğrulanmış ilan edemiyor.
- Desteklenen tek API sürecinde bağlam derleme boyunca düzeltme/onay/silme yazmaları araya girmiyor. Tek pakette farklı sürümlerin karışması için eşzamanlı regresyon testi var.
- Onaylı kurallar, kaynak alıntıları ve istemci çalışma özeti ayrı tutuluyor. Bütün serileştirilmiş paket byte bütçesine tabi. Gerekmediğinde politika uyarısı için boşuna bütçe ayrılmıyor.

## Araştırmayla ilişki

[ADR 0004](../../docs/adr/0004-evidence-before-expansion.md), memU'nun ajan/servis ayrımını, Titen'in kaynak–iddia ayrımını ve OpenViking/Basic Memory'nin aşamalı okuma fikirlerini hangi amaçla kullandığımızı açıklar. Mevcut harita → kart → kaynak düzeni korundu. Bu ürünlerin kodu kopyalanmadı; yeni paket, ayrı model veya servis bağımlılığı eklenmedi. Tam motor geçişi için aynı veride Titen/Basic Memory prototipi kıyası hâlâ açık.

## Değişiklik öncesi / sonrası tanısal karşılaştırma

İki koşuda aynı sentetik içerik tarifleri ve aynı sorgu/bütçeler kullanıldı; ayrı geçici DB'ler ve rastgele kayıt kimlikleri üretildi. Bu, dondurulmuş büyük bir bağımsız benchmark değildir. Değişiklik öncesi uygulama dosyaları `baseline/` altında ve iki raporda SHA-256 ile korunur. Değerlendiricinin gold kimlikleri arama girdisi olarak verilmedi.

| Senaryo | Önce | Sonra |
|---|---|---|
| Doğrudan dört kanıt, yüksek önem verilmiş ortak konu gürültüsü içinde | İlk dörtte 2/4 gerekli kayıt | 4/4 gerekli kayıt |
| Açık bağlantılı kanıt, geniş konu hub'ı içinde | İlk ikide 1/2 gerekli kayıt | 2/2 gerekli kayıt |
| 2024 tarihli özgül kaynak, yeni zayıf eşleşmeler arasında | Doğru kaynak ilk sırada değildi | Doğru kaynak ilk sırada |
| Onaylı değerin disputed alternatifi | İnceleme sinyali yoktu | `review_required=true`; alternatif etkinleşmedi |

Kaynaklar: [önce](evidence-before.json), [sonra](evidence-after.json). Bu sayılar genel hatırlama doğruluğu, Türkçe dil kapsamı veya LLM yanıt başarısı değildir.

## Ölçüm ve doğrulama

- **133 test geçti:** mevcut 117 test ve 16 yeni adversarial/regresyon örneği. [JUnit](tests.xml). HTTP/MCP, yerel semantik motor ve önceki medya testleri de çalıştı; test atlanmadı.
- Yeni örnekler doğrudan/graf kanıtı ayrımı, konu gürültüsü, sayfalama, eski kaynak, 512–3.000 byte bütçe, kaynak adayı eksikliği, ihtilaf gizlilik/zaman sınırı, sahte doğrulanmış yazar metadata'sı ve eşzamanlı düzeltmeyi kapsıyor.
- Ruff lint ve biçim kontrolü; mypy `--check-untyped-defs` ile 42 kaynak dosyası; JavaScript sözdizimi; kaynak secret taraması geçti. Qdrant'ın yerel payload index uyarısı sürüyor; önceki testlerde de vardı.
- **5.001 sentetik kayıt**, ortak konu hub'ı ve açık bağlantılarla bir sorgu: ilk arama **12,304 ms**, 15 sonraki aramanın medyanı **11,354 ms**, en yakın sıra yöntemiyle p95 **12,814 ms**. 96 aday sınırı korundu; bağlam **2.760/3.000 byte**. Pencere doygunluğu ve eksiklik görünür. [Ölçüm](performance.json).
- Varsayılan yolun ek LLM/embedding metodunu çağırması testte hata sayıldı; bu yolda ek model çağrısı **0**. Bu, konuştuğun AI hizmetinin token kullanımının sıfır olduğu anlamına gelmez.
- [Gerçek yapılandırılmış MCP/HTTP bağlantısı](live-connection.json) yeni talimatı, şema 2'yi, byte bütçesini, harita okumasını ve private kapsam reddini doğruladı. Kontrol gerçek hafızaya sentetik kayıt yazmadı. Servis mevcut veri diziniyle yalnız loopback üzerinde çalışıyor. Eski host oturumları eski sunucu talimatını önbellekte tutabilir; yeni oturum yeni talimatı alır.

Windows sandbox içinde HTTP testlerinin asyncio/socketpair başlangıcı bekledi. Aynı sentetik testler yerel socket erişimine izin verilen çalıştırmada tamamlandı; test kodunda engel atlatan bir değişiklik yapılmadı.

## Açık sınırlar

Doğrudan eşleşmeler bir sayfayı doldurursa ilişkisel kanıt sonraki sayfada kalabilir. Konu hub'larının SQL maliyeti aday metni sayısıyla sınırlı değildir. Bu tek sorgulu sentetik ölçüm üretim p95'i veya önceki sürüme göre hızlanma iddiası değildir.

İhtilaf işareti aynı subject/predicate/scope altında kaydedilmiş, halen disputed alternatif içindir; genel doğal dil çelişki çözümü ve geçmiş inceleme durumlarının bitemporal tekrar kurulması değildir. Modelin her turda doğru aracı çağırması, yakalanmamış geçmişin bulunması, bütün AI platformlarının bağlı olması ve bir yıllık kişisel corpus'ta kusursuz hatırlama kanıtlanmış değil.

Sonraki kalite eşiği: izinli gerçek/sentetik Türkçe corpus'ta kapsam yönlendirmesi, alias'lar, geçmiş/güncel karar, çok adımlı tüm kanıtların kapsanması ve gerçek sağlayıcı token kullanımı. İyileştirme seçimi bu kaçırmalara göre yapılmalı; PPR veya embedding ihtiyaç ölçülmeden varsayılan olmamalı.

## Tekrar çalıştırma

```powershell
.\scripts\Verify.ps1
.\.venv\Scripts\python.exe -m scripts.evaluate_evidence_retrieval --phase after
.\.venv\Scripts\python.exe -m scripts.evaluate_evidence_performance
.\.venv\Scripts\python.exe -m scripts.verify_evidence_connection
```

`--phase before` arşivlenmiş önce dosyalarını ve sonuçlarını yeniden yazar; mevcut kodda çalıştırmak eski sürümü otomatik yüklemez. Tarihsel önce sonucunu yeniden üretmek için `baseline/` sürümü ayrı, izole bir checkout/package içinde kullanılmalıdır. Kişisel `data/` üzerinde benchmark çalıştırılmaz.

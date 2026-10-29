# AI yönetimi ve sade gözlem arayüzü

30 Ekim 2026 · **v0.1.1 beta** · Windows yerel çalışma alanı.

Uygulamanın günlük arayüzü üç bölüme indirildi: **Özet, Yapılanlar, Hafıza**. İnsan kayıt eklemez, sınıflandırma/onay formları kullanmaz. Konuştuğu AI'ya değişikliği söyler; ekranda yapılanları, kaynakları, geçmişi, netleştirilmesi gerekenleri ve bağlantıların son erişimini izler.

## Uygulanan davranış

- Ana gezinmeden elle kayıt, onay/red, JSON paketleme, motor karşılaştırması ve teknik yönetim sayfaları çıkarıldı. Arama ve kaynak/geçmiş görüntüleme salt okunurdur. Eski teknik ekran yalnız `/maintenance` bakım/kurtarma adresinde korunur.
- Özet API'si kanonik kayıtlardan ve audit zincirinden türetilir. Ayrı bir gerçeklik kopyası veya sohbet modeli eklenmedi. Okuma gürültüsü işlem akışından filtrelenir; bağlantıya yetki verilmiş olması ile son erişim gözlemi ayrı gösterilir.
- Mevcut dört AI aracı korunur. `remember.change.organize` yalnız konular ve açık bağlantıları, kaynak açıklamasıyla düzenler. Değer, tür, kimlik, kapsam, gizlilik ve asıl kaynak listesi korunur.
- Bekleyen kayıtlar `navigate(branch=review)` ve `read(include_pending=true)` ile açıkça onaylanmamış kanıt olarak açılır. Varsayılan onaylı hatırlama davranışı değişmez.
- Belirli kayıt için konuşmadaki açık kullanıcı talimatıyla `approve`, `reject` ve `hide` yapılabilir. Alıntı, model/belge kaynaklı sözde kullanıcı onayı, bariz olumsuz komut ve genel yetki devri kabul edilmez. Net olmayan hedefi AI konuşmada netleştirmelidir.
- AI çıkarımı onaylanınca da `MODEL_INFERENCE/inferred` kalır. Belge bilgisi kullanıcı kuralına yükseltilmez. `hide` geçmişi korur; kalıcı silme veya genel admin/credential yetkisi verilmez.
- Önce/sonra metadata audit'te tutulur. Aynı işlemin tekrarı eski değişikliği yeniden uygulayıp sonraki düzenlemeyi geri almaz. Değişiklik kaynakları ve metadata geçmişi silme kapanımına dahil edilir.

Mimari karar: [ADR 0008](../../docs/adr/0008-ai-managed-observation.md). Sözleşme sürümü 4; SQLite şeması **7** olarak kaldı. Yeni paket bağımlılığı yoktur.

## Doğrulama

| Kontrol | Sonuç |
|---|---|
| Tam regresyon | **228 test geçti**, 0 başarısız/0 atlandı; [JUnit](tests.xml) |
| Yeni yönetim testleri | 16 vaka: kaynak koruma, metadata geçmişi, tekrar/sonraki değişiklik, kapsam/gizlilik/tenant, açık kullanıcı onayı, olumsuz komut, dış kural terfisi, karantina, hide/red ve silme kapanımı |
| Gerçek HTTP/stdio | Dört araçla kaynaklı kaydetme, düzeltme, tarihli okuma, konu düzenleme ve konuşarak onay; çıkarım türü korundu; [kabul](acceptance.json) |
| İnsan ekranı | Üç bölüm, kaynak ayrıntısı, arama, mobil menü ve çıkış gerçek tarayıcıda doğrulandı; [UI sonuçları](ui-checks.json) |
| Mobil | 390 piksel viewport'ta yatay taşma yok; [görsel](ui-mobile.png) |
| Statik/tip kontrolleri | Ruff lint/format, mypy ve iki JavaScript dosyasının sözdizimi geçti |
| Wheel | Uygulamanın 65 kaynak/asset/migration dosyası kurulu wheel ile eşleştirilir; [wheel kontrolü](wheel-check.json) |
| Canlı mevcut veri | Sürüm değişiminde kaynak ve iddia hash'leri aynı kaldı; gerçek servis ve mevcut kısıtlı bağlantı hazır; ayrıntı yerel `local-*.json` dosyalarında |

Bir beklenen Qdrant local payload-index uyarısı vardır; başarısızlık değildir. UI tıklamalarının beşi de güncel AX gözlemini inceleyen bağımsız kontrol ajanı onayından sonra yapıldı. Görseller sentetik veri gösterir; kişisel kaynak metni kamuya açık rapora taşınmadı.

Ek bir görsel senaryo için yeni kalıcı “Test AI” anahtarı oluşturma isteği otomatik izin incelemesinde reddedildi. Bu ek erişim oluşturulmadı; UI doğrulaması mevcut sentetik kayıtlar üzerinde salt okunur sürdürüldü. Asıl HTTP/stdio kabulü ayrı geçici depoda tamamlandı. Üretim bağlantısında yeni anahtar veya yeni erişim kapsamı verilmedi.

## Çalışan uygulama ve sınırlar

Yerel servis [127.0.0.1:8765](http://127.0.0.1:8765) üzerinde v0.1.1 ile yeniden açıldı; açık uygulama sekmesi yeni arayüzle yenilendi. Kullanıcının bu turdaki arayüz tercihi, kendi açık cümlesine dayanan `DECISION` olarak proje hafızasına kaydedildi. Güncelleme öncesindeki diğer kayıtlar değiştirilmedi; test verileri ana depoya eklenmedi.

AI işlemleri bağlı konuşma istemcisinin çalışmasına ve mevcut yetkilerine bağlıdır. Bu arayüzün içinde yeni bir sohbet modeli veya sürekli çalışan düzenleme ajanı yoktur. İstemci eski MCP şemasını önbellekte tutuyorsa yeni `change`/`review` alanları için bağlantıyı yeniden yüklemek veya yeni oturum açmak gerekir. Temel erişim mevcut bağlantıyla ayrıca doğrulandı.

Dil guard'ları genel doğal dil anlama veya bağımsız yazar doğrulaması sağlamaz. AI'nın her düzenlemesi otomatik doğru kabul edilmez; kaynağı, türü, geçmişi ve gerektiğinde konuşmadaki kullanıcı kararı korunur. Tüm platformların pasif yakalanması ve kusursuz yıl boyu hatırlama iddiası yoktur. [Diğer sınırlar](../../KNOWN_LIMITATIONS.md).

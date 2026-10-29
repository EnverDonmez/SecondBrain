# Second Brain: ortak kişisel veritabanı için açık kaynak araştırması

**Tarih:** 26 Ekim 2026 · **Kapsam:** düşük maliyetli, modelden bağımsız, kaynaklı ve uzun ömürlü kişisel hafıza · **Sonuç türü:** kaynak ve seçili kod incelemesine dayalı teknik karar raporu.

## 1. Karar özeti

**Senin tarifine en uygun çözüm, düşünme işini konuştuğun AI'ya bırakan; ham kaynakları kalıcı saklayan; bilgiyi başlık → kayıt → kaynak olarak açan tek bir kişisel veritabanıdır. Araştırdığım hiçbir hazır paketin bu koşulların tamamını, Türkçe ve uzun süreli gerçek kullanımda kanıtlanmış olarak sağladığını söyleyemiyorum.**

En değerli adaylar ve onlardan alacağımız şeyler:

| Öncelik / rol | Proje | Bizim hedefimize katkısı | Kararım |
|---|---|---|---|
| Mevcut AI'nın hafızayı yazması | [memU](https://github.com/NevaMind-AI/memU) | Yargı ve sentez ajan tarafında, hafıza servisi saklama/erişim tarafında | Sorumluluk bölümü için en yakın referans; embedding ve kaynak arşivi sınırlarını uyarlamadan bütünüyle geçmeyelim |
| Modelsiz, kaynaklı veritabanı çekirdeği | [Titen](https://github.com/RamaAditya49/titen) | Gözlem, kaynaklı iddia, çelişki, kapsam ve bütçeli bağlam ayrımı | İlk karşılaştırmalı prototip adayı; genç ve Bun tabanlı, büyük ürün yüzeyinin tamamına ihtiyacımız yok |
| Genelden özele bilgi düzeni | [OpenViking](https://github.com/volcengine/OpenViking) | Kaynak/hafıza/skill ad alanları; kısa temsil, genel bakış, ayrıntı | Bilgi mimarisi için güçlü referans; tam çalışma yığını bu bütçe için ağır |
| Hazır, okunabilir kişisel bilgi tabanı | [Basic Memory](https://github.com/basicmachines-co/basic-memory) | Markdown, ilişki grafiği, MCP, kompakt keşif ve seçili okuma | Hazır ürüne geçiş seçeneği olarak denemeye değer; tarih penceresi ve lisans planı önemli |
| Özgün konuşmayı koruma | [MemPalace](https://github.com/MemPalace/mempalace) | Özet yerine birebir kaynak, proje/konu kapsamları, değiştirilebilir arama arka ucu | Arşiv ve kapsam fikri değerli; tam zamansal doğruluk katmanını ayrıca kurmak gerekir |
| Yakalama ve kurtarma | [agentmemory](https://github.com/rohitg00/agentmemory) | Host hook'ları, tekrar işleme, kesinti sırasında biriktirme, oturum devamlılığı | Yakalama bileşenleri referans alınmalı; varsayılan bakım ve kalıcılık davranışı kanonik depo için aynen alınmamalı |
| İleri ilişkisel arama | [HippoRAG 2](https://github.com/OSU-NLP-Group/HippoRAG) | Sorgudan başlayan ilişkisel yayılım ve çok adımlı kanıt bulma | Algoritma/deney adayı; tam kütüphane sıfır ek model çağrısı sağlamıyor |
| Zaman içinde değişen ilişkiler | [Graphiti](https://github.com/getzep/graphiti) | Zamansal bilgi grafiği ve değişen ilişkiler | Zamansal şema referansı; ilk varsayılan motor olarak önermiyorum |

**Önerim:** Birden fazla hafıza sistemini aynı verinin sahibi yapmayalım. Mevcut kanonik SQLite çekirdeğini ölçüm tabanı olarak tutup memU'nun ajan/servis ayrımını, OpenViking'in katmanlı erişim fikrini ve Titen'in kaynak–iddia sınırlarını değerlendirelim. Titen ve Basic Memory'yi aynı veri ve bütçeyle rakip prototipler olarak sınayalım. Ölçüm başka bir çekirdeğin açık üstünlüğünü gösterirse geçiş yapalım; mevcut kodu korumayı amaç haline getirmeyelim.

Bu rapor bir entegrasyon uygulaması değildir. Araştırma sırasında çalışan veritabanına yeni motor, paket, model veya otomasyon kurulmadı.

## 2. Araştırma yöntemi ve kanıt sınırı

37 depo adresi kontrol edildi; **36 erişilebilir açık depo** için güncel metadata ve kaynak envanteri alındı. Bir adres yanlış/eskiydi; doğru `asg017/sqlite-vec` ayrıca doğrulandı. Standart README/lisans/bağımlılık taramasına ek olarak 14 adayın seçili uygulama ve tasarım dosyaları incelendi. Ana adaylar commit SHA'sıyla sabitlendi; diğer kaynaklarda kontrol zamanı ve dosya SHA-256 kaydedildi. Ek A'da bütün adaylar, [source-ledger.json](source-ledger.json) ve [implementation-ledger.json](implementation-ledger.json) içinde dosya kanıtları bulunur.

Üç kanıt düzeyini ayırıyorum:

- **Doğrulanan kaynak davranışı:** okunan kod veya sözleşmede doğrudan görülen davranış. Örneğin bir arama yolunun LLM istemcisi çağırması veya bir bakım fonksiyonunun kayıt silmesi.
- **Proje sahibinin sonucu/iddiası:** README veya kendi benchmark'ında yayımlanan sayı. Bağımsız ölçüm gibi kullanılmadı.
- **Benim değerlendirmem:** projemizin hedeflerine göre uygunluk, mimari tercih ve önerilen deney. Bir hız/başarı garantisi değildir.

Upstream projeler kurulup ortak corpus üzerinde çalıştırılmadı; ücretli model veya değerlendirme çağrısı yapılmadı. Dolayısıyla aşağıdaki öncelikler performans liderlik tablosu değil, gerekçeli mühendislik seçimidir. Kaynak incelemesi tam güvenlik denetimi sayılmaz. `main` belgesi, öneri durumundaki ADR ve yayımlanmış paket aynı şey değildir; gördüğüm uyuşmazlıkları ayrıca belirtiyorum.

## 3. Hangi şartlara göre seçim yaptım?

| Şart | Kabul ölçütü | Tek başına yeterli olmayan şey |
|---|---|---|
| Aynı hafızayı farklı AI'ların kullanması | Açık veri biçimi, yetkili MCP/API, taşınabilir kimlik ve kapsam | Bir ürünün kendi sohbet uygulamasına hafıza eklemesi |
| Yaklaşık maliyetsiz kullanım | Hafıza yazma/okuma yolunda zorunlu ayrı üretken model olmaması | Açık kaynak lisansı veya “local” etiketi |
| Bir yıl önceki şeyi hatırlama | İzinli özgün kaynak arşivi, tarihli indeks ve doğrulanabilir kaynak bağlantısı | Yalnız son özetin veya en sık erişilen notların tutulması |
| Bilgi karmaşasını azaltma | Sabit kimlik, alias, tür, kapsam, zaman, sürüm ve çelişki yönetimi | Daha fazla kenar veya daha büyük embedding modeli |
| Az token | Kısa keşif, seçili okuma, toplam çıktı bütçesi ve görünür eksiklik | Yalnız top-k döndürmek veya “compact” bayrağı |
| Konuştukça büyüme | Güvenilir yakalama, tekrar güvenliği, artımlı indeks, kaynaktan yeniden kurulum | LLM'nin her seferinde hatırlamayı kendisinin akıl etmesi |
| Kendi kendini optimize etme | Kaynağı bozmayan indeks/önbellek/temsil güncellemesi; ölçülen geri bildirim | Az kullanılan eski kaynağı otomatik silmek |

Bu şartlarla popüler bir “AI agent framework”, küçük bir kişisel veritabanından daha uygun olmayabilir. Skill/tool bilgisi saklamak da o aracın yeni AI oturumunda gerçekten kullanılabilir olduğu anlamına gelmez.

## 4. En uygun adayların ayrıntılı değerlendirmesi

### 4.1 memU — düşünmeyi mevcut ajana bırakma bakımından en yakın eşleşme

**Lisans:** Apache-2.0 metni doğrulandı. GitHub metadata'sındaki `NOASSERTION` etiketi tek başına karar için kullanılmadı. İncelenen ana commit: `42ef9fa3a8034f5817684cba23ef69fa70a58197`.

Güncel `MemoryService`, dışarıda hazırlanmış hafıza/skill içeriğini saklayan ve embedding ile erişen bir servis. Kaynak kodunun açıklaması ve yapısı, servis içinde sohbet/üretken LLM çağrısı yerine embedding istemcisi kullandığını gösteriyor. **Bu, senin “zaten konuştuğum AI gerekli bilgiyi hazırlasın” fikrine doğrudan uyuyor.** [Servis kodu](https://github.com/NevaMind-AI/memU/blob/42ef9fa3a8034f5817684cba23ef69fa70a58197/src/memu/app/service.py).

Geliştirici akışında uygulama konuşmaları sağlar; `prepare` görevleri ve çalışma alanını oluşturur; mevcut ajan hafızayı/skill'i düzenler; `commit` değişiklikleri saklar. Sentez işi ortadan kalkmaz, dışarıdaki ajana taşınır. Ayrı zamanlanmış ajan turu çalıştırılırsa mevcut hesabın kullanımını yine tüketir. Ham konuşma arşivinin uygulama tarafından ayrıca korunması gerekir; yalnız düzenlenmiş wiki çıktısını saklamak bütün ayrıntıları korumak değildir. [Geliştirici sözleşmesi](https://github.com/NevaMind-AI/memU/blob/42ef9fa3a8034f5817684cba23ef69fa70a58197/docs/developer.md).

İkinci sınır embedding: yerel veri deposu seçmek bütün işlemleri çevrimdışı yapmaz. Varsayılan sağlayıcı ayarları bulut embedding yolları içeriyor. Buna karşılık “LLM yok” beyanı doğru kapsamda: üretken çağrı yok; embedding çağrısı var. Ayrıca eski `docs/sqlite.md` örneğinde görülen `llm_profiles` argümanı güncel servis imzasında yok; kurulum tarifini sürüme sabitlemeden kopyalamamalıyız. [Embedding varsayılanları](https://github.com/NevaMind-AI/memU/blob/42ef9fa3a8034f5817684cba23ef69fa70a58197/src/memu/embedding/defaults.py), [SQLite belgesi](https://github.com/NevaMind-AI/memU/blob/42ef9fa3a8034f5817684cba23ef69fa70a58197/docs/sqlite.md).

**Alınacak:** ajan tarafından hazırlanan yazma sözleşmesi, hafıza/skill/kaynak işlerinin ayrılması, kendisini tekrar tekrar hafızaya alan döngüleri önleme. **Aynen alınmayacak:** bizim zorunlu modelsiz yolumuzu değiştiren embedding varsayılanı; ham kaynağın yerine yalnız sentezlenmiş dosyaları koymak. “Wiki graph” adlı ADR öneri durumunda ve kendi içinde grafik olmayan hibrid erişim yönüne düzeltme içeriyor; adı nedeniyle uygulanmış grafik motoru kabul etmedim. [ADR 0007](https://github.com/NevaMind-AI/memU/blob/42ef9fa3a8034f5817684cba23ef69fa70a58197/docs/adr/0007-three-independent-memory-lines-wiki-graph.md).

### 4.2 Titen — ayrı model gerektirmeyen kaynaklı çekirdek için güçlü aday

**Lisans:** Apache-2.0. Ana commit: `23302a16d44d01f3759ef56287847f85352d0fc1`. **Durum:** 1.0 öncesi; API'nin kararlı olduğu varsayılamaz.

Varsayılan yerel yol Bun ve SQLite/FTS5 kullanıyor; embedding veya üretken LLM zorunlu değil. İddiaları çağıran taraf yazıyor. Böylece çıkarım maliyeti veritabanının gizli arka plan işine dönüşmüyor. [Proje açıklaması](https://github.com/RamaAditya49/titen).

Veri modelinin bizim için en yararlı kısmı şu ayrım: gözlem/kanıt, kaynağa bağlı ve itiraz edilebilir iddia, çalışma noktası. Kaynak bağlantısı destekleme/çürütme/niteleme ilişkisini taşıyabiliyor; çelişen iddiaların otomatik tek gerçeğe kaynaştırılması yerine izlenebilir çözüm öngörülüyor. Tam bitemporal sorgu eşdeğerliğini bu incelemeyle kanıtlamadım. [Hafıza modeli](https://github.com/RamaAditya49/titen/blob/23302a16d44d01f3759ef56287847f85352d0fc1/docs/architecture/memory-model.md).

Önemli artısı, yayımladığı değerlendirmelerde başarısız koşulları da açıklaması. Fakat küçük, konuya ayrılmış bir havuzla bütün geçmişin karıştığı havuzdaki sonuçlar aynı değil. Kendi raporları, kapsamlandırmanın büyük etkisini ve bazı önerilen optimizasyonların başarısızlığını gösteriyor. Bu sonuçları bizim Türkçe geçmişimizde yeniden üretmedik. [Havuzlanmış veri deneyi](https://github.com/RamaAditya49/titen/blob/23302a16d44d01f3759ef56287847f85352d0fc1/docs/testing/2026-08-07-pooled-store.md).

**Alınacak:** gözlem–iddia ayrımı, aramadan önce yetki/kapsam, kanıt zinciri, bütçeli bağlam, geri bildirimi ölçmeden sıralamayı değiştirmeme. **Sınır:** yönetişim/federasyon/ajan koordinasyonu gibi geniş yüzeyin tamamı tek kullanıcılı hafıza için gereksiz olabilir. Yaşam döngüsü/retention ayarları ham arşivin silinmemesi şartıyla incelenmeli. İngilizce ağırlıklı sözlüksel erişimin Türkçe kalitesi ayrıca ölçülmeli.

### 4.3 OpenViking — genelden özele temsil için en güçlü mimari referanslardan biri

**Lisans:** AGPL-3.0. İncelenen ana commit: `5c066d97094d713238c483c10691d7b4e1cfbf6e`.

Kaynaklar, hafızalar ve skill'lerin ortak bir ad alanında ele alınması bizim kapsamımıza uyuyor. Katman belgesi kısa dizin özeti, genel bakış ve kaynak ayrıntısını ayırıyor. L0/L1 dizin yan dosyaları; her normal dosya için mutlaka ikisi birden varmış gibi davranılmamalı. [Katman sözleşmesi](https://github.com/volcengine/OpenViking/blob/5c066d97094d713238c483c10691d7b4e1cfbf6e/docs/en/concepts/03-context-layers.md).

**Önemli düzeltme:** katmanlı bilgi temsili ile arama algoritması aynı şey değil. v0.4.23 sürüm notları dizin içinde rekürsif arama/üst düğüm puan yayılımının kaldırılıp global vektör çağırma ve tek yeniden sıralama yoluna geçildiğini açıkça söylüyor. “Dosya sistemi gibi düzenli” ifadesinden “arama mutlaka tepeden aşağı iner ve en ucuz yolu bulur” sonucu çıkmıyor. [v0.4.23 sürüm notu](https://github.com/volcengine/OpenViking/releases/tag/v0.4.23).

`search(mode="context")` bütçe, ayrıntı seviyesi ve tekrarları bir sunucu isteğinde birleştiren değerli bir yaklaşım; bazı anlam genişletme veya digest seçenekleri ise ek LLM işi yapabiliyor. Tam semantik kurulumun embedding ve VLM gereksinimi var. [Erişim API'si](https://github.com/volcengine/OpenViking/blob/5c066d97094d713238c483c10691d7b4e1cfbf6e/docs/en/api/06-retrieval.md), [kurulum kapsamı](https://github.com/volcengine/OpenViking).

**Alınacak:** açık ad alanı, kısa temsil → kaynak ayrıntısı, her kaynak türüne uygun sunum ve tek bütçe derleyicisi. **Aynen alınmayacak:** zorunlu VLM/embedding iş akışı ve üretilmiş özeti kaynak gerçeği saymak. Tam ürüne geçiş ancak maliyet, kaynak koruma ve lisans/dağıtım planı birlikte uygunsa düşünülmeli.

### 4.4 Basic Memory — hazır, insan tarafından da okunabilen alternatif

**Lisans:** AGPL-3.0. Ana commit: `9643ec25918e8958629a668e3ce928981ab3ea36`.

Markdown dosyaları, wikilink'ler, gözlemler/ilişkiler ve MCP araçları, hafızayı modele kapalı bir iç durum olmaktan çıkarıyor. Notlar farklı araçlar tarafından okunup düzenlenebiliyor; SQLite yerel kurulum yolu var. Bu, özel geliştirme yükünü azaltabilecek gerçek bir ürün alternatifi. [Proje](https://github.com/basicmachines-co/basic-memory).

Güncel `bm_context`, grafik keşfinde `compact` ile gövdeleri/gözlemleri dışarıda bırakıp seçili notları sonradan okutabiliyor. Ancak kompakt çıktı sabit token sınırı değildir. Daha önemlisi, **varsayılan `since="7d"` ilişkili sonuçları yakın zamandaki değişikliklere sınırlar.** Bir yıl önceki bağlantı için bu varsayılanı körlemesine kullanamayız; bu kaynakların silindiği anlamına da gelmez. [Güncel araç sözleşmesi](https://github.com/basicmachines-co/basic-memory/blob/9643ec25918e8958629a668e3ce928981ab3ea36/src/basic_memory/man/man3/bm-context%283%29.md), [araç kodu](https://github.com/basicmachines-co/basic-memory/blob/9643ec25918e8958629a668e3ce928981ab3ea36/src/basic_memory/mcp/tools/context.py).

**Alınacak:** okunabilir dosyalar, tipli ilişkiler, gövdesiz keşif ve sonra okuma. **Sınır:** dosya/DB senkronizasyonu ve not sürümleri, tek başına bizim valid/known time ve çelişki modelimizin yerine geçmez. Yıllık hatırlama, silme ve token bütçesi için adaptör gerekir. Hazır ürün yolu tercih edilirse, doğrudan denenecek iki adaydan biri budur.

### 4.5 MemPalace — özgün metin arşivi ve kapsamlı erişim için değerli

**Lisans:** MIT. Proje, konuşmayı özetleyip yalnız seçilmiş bilgiyi tutmak yerine birebir metin olarak saklamayı; insan/proje, konu ve içerik bölümleriyle kapsamlandırmayı öne çıkarıyor. Varsayılan erişim arka ucu ChromaDB; alternatif arka uç sözleşmesi var. Bu nedenle “yerel” ve “LLM gerektirmiyor” ifadesi “hiç model yok” demek değil: semantik erişim için embedding yolu bulunuyor. [Proje](https://github.com/MemPalace/mempalace), [arka uç sözleşmesi](https://github.com/MemPalace/mempalace/blob/develop/mempalace/backends/base.py).

Bizim için esas değer, yorumlanmış hafıza ile özgün konuşmayı birbirine alternatif yapmaması. Bir yıl sonra sorulan ve o gün önemsiz görünen bir ayrıntı, yalnız özette hiç bulunmayabilir.

**Alınacak:** ham arşiv, proje/konu kapsamları, aramayı kanonik içerikten ayıran adaptör. **Sınır:** yüksek retrieval recall, doğru güncel karar veya güvenilir Türkçe cevap garantisi değildir. Tipli tercihler, zamansal düzeltme ve yetki politikaları ayrı değerlendirilmelidir. Benchmark'taki “raw”, hibrid ve LLM ile yeniden sıralanan yolları birbirine karıştırmıyorum. [Metodoloji](https://github.com/MemPalace/mempalace/blob/develop/benchmarks/BENCHMARKS.md).

### 4.6 agentmemory — yakalama tarafında güçlü, kanonik depo olarak koşullu

**Lisans:** Apache-2.0. Ana commit: `c5b8ebfb32eb6a08fe301d3bb75840f3597b66c8`.

Native hook'lar, oturum/araç olayları, offline spool ve tekrar işleme tasarımı önemli. LLM sıkıştırması opsiyonel; modelsiz BM25 yolu mevcut. Araç yüzeyini küçük bir çekirdek listeye indirme seçeneği de token maliyeti açısından yararlı. [Proje](https://github.com/rohitg00/agentmemory).

Fakat iki kritik sınır var. Kendi kalıcılık belgesi, varsayılan dosya tabanlı KV deposunda kabul edilmiş yazmanın hemen diskte olmayabileceğini; periyodik kayıt ve replay yolunun her API yazısı için güç kesintisi garantisi vermediğini açıklıyor. [Kalıcılık belgesi](https://github.com/rohitg00/agentmemory/blob/c5b8ebfb32eb6a08fe301d3bb75840f3597b66c8/docs/reliability/state-storage.md).

Otomatik unutma kodunda yalnız puan düşürme değil, TTL dolan hafızanın ve belirli eski/düşük önem gözlemlerinin gerçekten silinmesi bulunuyor. Dolayısıyla “kendi kendini optimize ediyor” gerekçesiyle bu yolu ham kişisel arşive aynen uygulamak hedefimize ters düşebilir. İlgili ayarlar açıkça kontrol edilmeli. [Unutma kodu](https://github.com/rohitg00/agentmemory/blob/c5b8ebfb32eb6a08fe301d3bb75840f3597b66c8/src/functions/auto-forget.ts), [ayar örneği](https://github.com/rohitg00/agentmemory/blob/c5b8ebfb32eb6a08fe301d3bb75840f3597b66c8/.env.example).

**Alınacak:** host adaptörleri, kalıcı alım kuyruğu, kararlı olay kimliği, kendi hafıza araçlarının çıktısını tekrar yakalamayı engelleme. **Aynen alınmayacak:** ham veriyi silebilen otomatik bakım ve uygulamamızın kabul ettiği kayıp aralığından daha zayıf bir yazma garantisi.

### 4.7 HippoRAG 2 — ilişkilerden bulma için araştırma adayı

**Lisans:** MIT. Ana commit: `d5c8329422e0a0b834a15874545cb6a74b4f9b26`.

Bilgi grafiği ve Personalized PageRank ile, soruya doğrudan benzemeyen fakat ilgili bir varlık üzerinden bağlanan pasajları bulmayı ele alıyor. Bu, “konudan ilgili diğer bilgilere geçme” hedefimizle örtüşüyor. [Proje ve çalışma](https://github.com/OSU-NLP-Group/HippoRAG), [makale](https://arxiv.org/abs/2502.14802).

Ancak tam boru hattı salt graf yürüyüşü değil. OpenIE çıkarımı, embedding ve sorguyla ilgili aday olguları süzen LLM yolu bulunuyor; `DSPyFilter` kodunda LLM inference çağrısı doğrudan görülüyor. [Ana uygulama](https://github.com/OSU-NLP-Group/HippoRAG/blob/d5c8329422e0a0b834a15874545cb6a74b4f9b26/src/hipporag/HippoRAG.py), [filtre](https://github.com/OSU-NLP-Group/HippoRAG/blob/d5c8329422e0a0b834a15874545cb6a74b4f9b26/src/hipporag/rerank.py).

**Alınacak:** sorguya bağlı başlangıç düğümleri ve kontrollü ilişkisel yayılım fikri. İlişkileri mevcut AI yazarsa graf algoritmasını ayrıca model çağırmadan deneyebiliriz. Bu uyarlamanın tam HippoRAG sonuçlarını koruyacağı iddiası yok. Mevcut FTS/graf tabanına karşı ölçülmeden varsayılan yapılmamalı.

### 4.8 Graphiti — değişen bilgiyi temsil etmek için güçlü, maliyeti ayrı

**Lisans:** Apache-2.0. Ana commit: `5c27edfa8d3e0f49b2571bcebb4261bcc89ee037`.

Zamansal graf ve episodik kaynaklardan ilişki çıkarma, geçmişte doğru olup bugün değişen bilgiyi ele almak için değerli. Fakat varsayılan kurulum graf arka ucu ve yapılandırılmış çıktı verebilen bir LLM/embedding yolu içeriyor. Başka sağlayıcı veya yerel model seçmek mümkündür; bu, ilave hesaplama işini ortadan kaldırmaz. [Kurulum ve tasarım](https://github.com/getzep/graphiti), [bağımlılıklar](https://github.com/getzep/graphiti/blob/5c27edfa8d3e0f49b2571bcebb4261bcc89ee037/pyproject.toml).

**Alınacak:** olay ile çıkarılmış ilişkiyi ayırma, geçerlilik ve geçmiş değişimini koruma. **Karar:** mevcut SQLite zamansal çekirdeğini sırf graf adı var diye değiştirmeyelim. İlişki sorguları gerçekten darboğaz olursa projection olarak deneyelim; ikinci kanonik gerçeklik yaratmayalım.

## 5. Diğer adaylar: ne için uygun, neden ilk seçim değil?

| Aday | Yararlı tarafı | Bizim hedefimiz için sınır / karar |
|---|---|---|
| [AliceMemory](https://github.com/samrusani/AliceMemory) | SQLite, az araçla devamlılık, kararlar/açık işler, kaynak açıklaması | MIT; public alpha. Kendi belgelerinde kapsam, silme/türetilmiş metin ve güvenlik sınırları açık. Şu haliyle sorgusuz kanonik çekirdek seçmem; devamlılık fikirlerini incelerim |
| [Claude-Mem](https://github.com/thedotmack/claude-mem) | Host hook'ları ve katmanlı aramayla oturumlar arasında devamlılık | Apache-2.0. Güncel kurulum hosted observer/deneme ve host ya da harici model sağlayıcısı seçenekleri içeriyor; gözlem/sıkıştırma AI işi. Adaptör ve aşamalı okuma referansı, zorunlu ek çıkarım olmadan çalışan çekirdeğimizin doğrudan karşılığı değil |
| [doobidoo/mcp-memory-service](https://github.com/doobidoo/mcp-memory-service) | Yerel embedding, SQLite-vec, ilişki ve konsolidasyon | Apache-2.0. Yerel model maliyeti ve yaşam döngüsü ayrıntıları var; decay/forget politikası ham arşive uygulanmamalı |
| [Mem0](https://github.com/mem0ai/mem0) | Yaygın hafıza API'si; `infer=False` ile çıkarım LLM'sini atlama | Apache-2.0. Bu bayrak embedding'i kaldırmaz; graf/diğer seçenekler ayrıca incelenmeli. Mevcut projection'ı koruyabiliriz, ana verinin sahibi yapmak için neden yok |
| [Hindsight](https://github.com/vectorize-io/hindsight) | Retain/recall/reflect, gözlemler, kaynaklı ve farklı arama yolları | MIT. Retain/reflect üretken model işi içerebilir; PostgreSQL/servis işletimi var. Mevcut abonelik kullanılsa da ek çağrılar kullanım tüketir |
| [MemOS](https://github.com/MemTensor/MemOS) | İz → strateji → dünya modeli → skill; çok katmanlı deneyim | Apache-2.0. Yerel plugin ve ana proje farklı yüzeyler; reflection/sentez model işini, host bağımlılığını ve yükseltmeyi ayrıca yönetmek gerekir |
| [Cognee](https://github.com/topoteretes/cognee) | Belgeden graf ve semantik hafıza | Apache-2.0. LLM/embedding ve işlem hattı maliyeti; kaynaklı kişisel ledger'ın doğrudan yerine koymuyorum |
| [Letta](https://github.com/letta-ai/letta) | Stateful ajan, bellek blokları ve ajan kontrollü hafıza | Apache-2.0. Başlıca ürün ajan runtime'ı; bizim ince, platformdan bağımsız veritabanı hedefinden geniş |
| [LangMem](https://github.com/langchain-ai/langmem) | Uzun süreli semantik/prosedürel hafıza için araçlar | MIT. LangGraph/ajan ekosistemi ve sentez adımları; bütün depoyu taşımak yerine kavram referansı |
| [A-MEM](https://github.com/agiresearch/A-mem) | Zettelkasten benzeri bağlantılı notlar ve evrilen hafıza | MIT. Not çıkarımı/güncelleme LLM işi içerir; serbest bağlantı üretimi doğru kaynak/otorite demek değil |
| [PageIndex](https://github.com/VectifyAI/PageIndex) | Uzun belgede ağaç yapısı üzerinden ayrıntıya inme | MIT. Vektörsüz olmak modelsiz olmak değil: indeks/özet ve reasoning katmanında LLM kullanılıyor. Belge alt modülü adayı |
| [RAPTOR](https://github.com/parthsarthi03/raptor) | Rekürsif özet ağacı | MIT. Hiyerarşi üretirken özetleme/embedding işi, değişiklikte bakım; kişisel ham arşivin yerine geçmez. Son push tarihi eski; araştırma referansı |
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | Büyük corpus üzerinde topluluk/ilişki temelli bağlam | MIT. Graf çıkarımı ve özetler için model işi; küçük kişisel sorgular için varsayılan yük olarak gerekçelendirilmedi |
| [LightRAG](https://github.com/HKUDS/LightRAG) | Graf ve vektör erişimini birleştirme | MIT. LLM/embedding çıkarım boru hattı; aynı veriyle ek kazanç ölçülmeden yeni varsayılan olmamalı |
| [Memvid](https://github.com/memvid/memvid) | Taşınabilir tek dosya, zamanlı/versiyonlu içerik | Apache-2.0. Arşiv/index taşınabilirliği ilginç; bizim iddia/kaynak/izin/düzeltme sözleşmesinin tamamını karşılıyor varsaymadım |
| [Memori](https://github.com/MemoriLabs/Memori) | SQL temelli hafıza ve entegrasyon | Apache-2.0 metni görüldü. Üretken çıkarım ve mevcut çağrıları izleme katmanını ayrıca değerlendirmek gerekir |
| [a-memory](https://github.com/Cipher208/a-memory) | SQLite, tipli graf, katmanlar ve yerel çalışma | MIT. Yeni alternatif; bakım/terfi ve gerçek üretim iddiaları bağımsız doğrulanmadı. Kayıpsızlık ve Türkçe testten önce seçmem |
| [localmem-mcp](https://github.com/OpenAgentHQ/localmem-mcp) | Küçük Python store + MCP, yerel embedding | MIT. Küçük semantik erişim tabanı olarak uygun; kaynak/çelişki/tarihli kişisel model için ek katman gerekir |
| [MCP reference memory](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | Çağıran AI'nın entity/ilişki yazdığı yalın tasarım | Referans uygulama; JSONL ve substring erişimi ölçekli, kaynaklı kişisel veritabanı yerine yeterli değil. Güncel repo lisansı geçiş metni içeriyor |
| [Supermemory](https://github.com/supermemoryai/supermemory) | Entegrasyon ve profil API'si açısından fikir verir | Açık SDK/repo ile asıl sunucu aynı şey değil. Resmî self-host belgesi sunucu binary'sinin açık kaynak olmadığını söylüyor; tam açık kaynak motor kısa listesinden çıkarıldı |

Özellikle Alice için pazarlama özetiyle sınırlı kalmadım: kendi [bilinen sınırlar belgesindeki](https://github.com/samrusani/AliceMemory/blob/a6a5f49eebb7377f40b388f2ffe07290b05b85fb/docs/alpha/known-limitations.md) açık noktaları kararın parçası yaptım. doobidoo için [decay uygulaması](https://github.com/doobidoo/mcp-memory-service/blob/ef25b93d9565d28388175edf4923c35d39d248fa/src/mcp_memory_service/consolidation/decay.py) sıralama mantığının önemli olduğunu gösteriyor; bu dosyadan tek başına tüm silme davranışını çıkarmıyorum. Mem0'nun [varsayılan çıkarım API'si](https://github.com/mem0ai/mem0/blob/main/LLM.md), PageIndex'in [istemci uygulaması](https://github.com/VectifyAI/PageIndex/blob/e38b40ebaeea26d2c7206b80ce7bc9bf2935cdec/pageindex/client.py) ve Supermemory'nin [kendi sunucu açıklaması](https://supermemory.ai/docs/self-hosting/overview) maliyet/açıklık ayrımını destekliyor.

## 6. “Sinir ağı gibi, Kruskal yaparak” ifadesinin teknik karşılığı

Senin amacın açısından dört iş birbirinden ayrılmalı:

1. **Harita:** Projeler, kişiler, tercihler, konular, skill'ler ve araçlar arasında okunabilir düzen.
2. **Bulma:** Soruya uygun başlangıç kayıtlarını seçmek.
3. **İlişkilerden genişletme:** İlk kayıttan bağlantılı kanıtları bütçeli biçimde toplamak.
4. **Doğruluk kontrolü:** Kaynak, tarih, kapsam, çelişki ve yetkiyi kontrol etmek.

Kruskal, ağırlıklı grafın en küçük yayılım ağacını kurar. Bir sorunun doğru cevabını veya doğru kişisel bilgiyi bulmaz. Bütün grafı böyle bir ağaca indirgemek, anlamlı çapraz bağlantıları da atabilir. Dijkstra en kısa yolu bulsa bile kenar ağırlıkları “gerçeklik” değildir. PPR, sorgu başlangıçlarından bağlantılı kayıtları puanlayabilir; doğruluğu yine kaynak/zaman katmanı sağlar. [NetworkX MST sözleşmesi](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.tree.mst.minimum_spanning_tree.html), [PageRank ve personalization](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html).

**Önerdiğim erişim:** izin/kapsam/tarih filtresi → doğrudan kimlik/alias/FTS adayları → gerekirse birkaç sorgu başlangıcından graf yayılımı → çelişki/güncel sürüm kontrolü → bütçeli kanıt paketi. Bilinen bir kayıt için her defasında kökten dolaşmak gereksiz; doğrudan adresleme kısa yol olmalı. Yanlış dal seçilince bütün hafızanın kaçırılmaması için alternatif indeks yolu da bulunmalı.

Kanonik grafı “optimizasyon” adına budamayalım. Sorguya özel küçük bir kanıt alt grafı çıkarmak, özgün ilişkiyi silmekten farklıdır. Bir yöntemin adı biyolojik veya graph-based diye daha doğru olduğunu varsaymayalım; FTS tabanından daha iyi olduğu ölçülmeli.

## 7. En uygun teknik bileşim

### 7.1 Tek kanonik depo, değiştirilebilir erişim indeksleri

SQLite + FTS5, tek kullanıcı ve yerel uygulama verisi için makul bir başlangıç olmaya devam ediyor. FTS5; önek, BM25, snippet ve özel tokenizer/synonym genişletme olanakları sunuyor. Bu bir genel dil anlama modeli değildir. [SQLite kullanım alanı](https://www.sqlite.org/whentouse.html), [FTS5](https://www.sqlite.org/fts5.html).

| Parça | İlk tercih | Ne zaman genişletilmeli? |
|---|---|---|
| Özgün olaylar, iddialar, zaman ve yetkiler | Tek SQLite kanonik ledger | Çok cihazda eşzamanlı yazma gerçek ihtiyaç olduğunda tek bir açık sunucu DB'si değerlendirilir |
| Sözcük ve başlık erişimi | FTS5 + alias/kavram dizini | Türkçe/eş anlamlı sorgu kaçırma ölçülürse tokenizer veya isteğe bağlı semantik kol |
| İlişkisel arama | İndeksli kenarlar ve sınırlı sorgu genişletmesi | Çok adımlı sorgular gerekli kanıtı kaçırıyorsa PPR/Dijkstra benzeri deneyler |
| Küçük graf deneyleri | [NetworkX](https://github.com/networkx/networkx) | Üretim veri boyutunda RAM/gecikme sınırını ölçerek |
| İsteğe bağlı yerel vektör kolu | [sqlite-vec](https://github.com/asg017/sqlite-vec) | Embedding gerçekten ek doğruluk sağlarsa; vektörleri üretmek yine ayrı iştir |
| Büyük vektör havuzunda yaklaşık erişim | [USearch](https://github.com/unum-cloud/USearch) deneyi | Tam arama maliyeti ölçülerek sorun olduğunda; izinli kanonik kayıt doğrulaması korunur |
| Ayrı embedded graf motoru | [LadybugDB](https://github.com/LadybugDB/ladybug) deneyi | SQLite ilişki sorguları ölçülmüş darboğaz olduğunda |

sqlite-vec, embedding üreticisi veya kişisel hafıza sistemi değildir; kaynak/provenance katmanının yerine geçmez. LadybugDB de AI'nın seni tanımasını kendiliğinden sağlamaz. Kuzu yerine yeni geliştirmede aktif alternatifi incelemek daha mantıklı: Kuzu deposu 10 Ekim 2025'te arşivlenmiş. [Arşiv durumu](https://github.com/kuzudb/kuzu), [LadybugDB](https://github.com/LadybugDB/ladybug).

### 7.2 Dört veri türü karışmamalı

| Tür | Ne saklanır? | Güven ve kullanım |
|---|---|---|
| Özgün kaynak | Mesaj, araç olayı, dosya sürümü, gerçek kimlik/zaman/hash | Ne söylendiğinin kanıtı; tek başına talimat veya bugünkü gerçek değil |
| Yapılandırılmış iddia | Tercih, karar, proje durumu, ilişki; kaynak aralığı ve geçerlilik | Güven/kapsam/sürümle kullanılır; düzeltme eski kaydı ezmez |
| Çalışma noktası | Amaç, tamamlanan iş, açık sorular, sonraki adım | Devamlılık özeti; kalıcı doğru ve kullanıcı emri gibi yükseltilmez |
| Yetenek kaydı | Skill içeriği/sürümü, aracın tanımı ve son gözlem zamanı | Hatırlamak ile şu an yürütme yetkisine sahip olmak ayrılır |

Mümkünse AI, kullanıcının cümlesini tekrar yazarak “kaynak” üretmesin. Yetkili yakalayıcının tuttuğu olay kimliğini ve karakter aralığını referans versin. Böylece kaynak uydurma riski ve tekrar taşınan metin azalır. Araç/skill kabiliyeti çalıştırılacağı anda host'tan yeniden doğrulanır; bir yıl önce kurulmuş olması bugün var olduğu anlamına gelmez. Bunlar önerilen uygulama kurallarıdır; bütün adaylarda hazır bulunduğu iddiası değildir.

### 7.3 Kendi kendine düzenleme, kaynak kaybı yaratmamalı

Güvenli otomatik işler: değişen kaydın indeksini güncellemek, alias ve bağlantı önerisi üretmek, tekrarları işaretlemek, önbelleği yenilemek, bayat özeti yeniden oluşturmak, erişim planını ölçmek. Bunlar kaynak üzerine yazmadan yapılabilir.

Şu işleri varsayılan yapmam: az erişildi diye kaynağı silmek, birbiriyle çelişen iki tercihi modelin sessizce birleştirmesi, AI'nın kendi önceki cevabını yeni kullanıcı kanıtı saymak, tek başarılı retrieval'dan yeni kalıcı kullanıcı kuralı üretmek. memU'nun kendi hafıza üretim turunu yeniden madenciliğe almamayı ele alan [ADR'si](https://github.com/NevaMind-AI/memU/blob/42ef9fa3a8034f5817684cba23ef69fa70a58197/docs/adr/0015-bridging-must-not-mine-its-own-run.md) ve agentmemory'nin kendi hafıza araçlarını capture'dan dışlayan [değişiklik notu](https://github.com/rohitg00/agentmemory/blob/c5b8ebfb32eb6a08fe301d3bb75840f3597b66c8/CHANGELOG.md), bu döngünün pratik önemini gösteriyor.

### 7.4 Her AI ile ortak hafıza: protokol yeterli değil, bağlantı da gerekiyor

MCP; host, istemci ve sunucu arasındaki bağlam/araç alışverişini standartlaştırıyor. Yerel stdio ile uzak Streamable HTTP farklı bağlantı biçimleri. Protokol, host'un gelen bağlamı nasıl kullanacağını belirlemiyor. Dolayısıyla veritabanına “gereken bilgileri beyne kaydet” yazmak, bağlantısız herhangi bir AI'nın bunu görmesini veya en yüksek öncelikte uygulamasını sağlamaz. Bu, hedefin vazgeçilmesi gereken kısmı değil; host başına adaptör gerektiren kısmıdır. [Resmî MCP mimarisi](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture).

Önerdiğim bağlantı sözleşmesi:

| Host durumu | Uygun bağlantı | Kanıtlanması gereken |
|---|---|---|
| Yerel araç/MCP destekli AI | Küçük araç yüzeyi ve aynı kanonik servise erişim | Yetki, oturum/proje kimliği, araç çağırma ve kesintiden kurtarma |
| Uzak araç bağlantısı destekli AI | Kimlik doğrulanan uzak MCP/API | İstemcinin taşıma/kimlik doğrulama desteği; hangi verinin uzak modele gönderildiği |
| Hook veya izinli transcript dışa aktarımı olan host | Kaynak yakalayıcı + checkpoint + sorgu araçları | Kaynak kapsaması, olay sırası, tekrar güvenliği ve host sürüm uyumu |
| Hiç araç/bağlayıcı/dışa aktarım desteği olmayan kapalı platform | Kullanıcının taşıdığı sınırlı bağlam paketi | Otomatik çift yönlü hafıza olduğu söylenemez |

Okuma ve yazma yetkileri ayrı olmalı; aynı kullanıcıya hizmet etseler de bir istemcinin diğer projenin tüm geçmişini kendiliğinden alması gerekmez. Güvenilir kullanıcı talimatı, içe aktarılan konuşma metni ve AI'nın çıkardığı iddia ayrı tutulmalı. Hatırlanan metin yeni bir sistem talimatı gibi yürütülmemeli. İlk desteklenecek host'ları seçip bağlantı testleri tamamlanmadan “hangi AI olursa olsun otomatik çalışır” sözü vermeyelim. Bunlar önerilen entegrasyon kurallarıdır.

## 8. Maliyet: “açık kaynak” ve “az token” aynı şey değil

Hafıza maliyetini şu parçalara ayırmalıyız:

**Toplam kullanım = yazma/çıkarım + indeks/embedding + sorgu genişletme/yeniden sıralama + AI'ya dönen bağlam + bakım.**

| Yol | Ayrı üretken model işi | Başka maliyet | Bizim başlangıç tercihi |
|---|---|---|---|
| Mevcut konuşma modeli kısa kayıt argümanı hazırlar | Hafıza servisi çağırmaz | Mevcut sohbetin çıktı token'ı ve araç sonucu | Evet |
| FTS/alias ve indeksli graf erişimi | Yok | Yerel CPU/disk ve dönen bağlam | Evet |
| Yerel embedding | Üretken LLM yok | Model dosyası, RAM, CPU, ilk indeksleme | İsteğe bağlı |
| Bulut embedding | Üretken LLM olmayabilir | Ayrı servis çağrısı, ücret/veri aktarımı | Varsayılan değil |
| Arka planda sentez/reflection ajanı | Var | Aynı hesabın kotası veya API maliyeti | Ölçülmüş ihtiyaç olmadan değil |
| Her sorguda LLM rerank/yanıt üretimi | Var | Ek gecikme ve kullanım | İlk sürümde değil |

Bir özetin tekrar kullanılması tasarruf sağlayabilir; ama her turda yeniden özet üretmek tasarrufu yok edebilir. Kabaca, tekrar kullanımın azalttığı bağlam yükü; özet üretimi, güncelleme ve fazladan yönlendirme maliyetini aşmalıdır. Aynı model adını kullanmak veya mevcut abonelikle çalışmak, ikinci çağrının bedelsiz olduğunu göstermez.

Araç tanımları da bağlam maliyetine katılabilir. Küçük bir `remember / navigate / read / prepare_context` yüzeyi, onlarca sürekli açık araçtan daha uygun olabilir. Bunun getirisi gerçek istemci/model üzerinde ölçülmeli; MCP protokol çıktısının boyutu doğrudan faturalanan sağlayıcı token sayısı değildir. Titen'in [taşınabilir bütçe birimleri](https://github.com/RamaAditya49/titen/blob/23302a16d44d01f3759ef56287847f85352d0fc1/src/core/tokens.ts) gibi tahminler de sağlayıcı tokenizer'ının yerini kesin olarak tutmaz.

## 9. Benchmark'lara nasıl baktım?

### 9.1 Birbiriyle karşılaştırılamayan sayılar

- agentmemory'nin yayımladığı %95,2 değeri `recall_any@5`: doğru oturumlardan **herhangi birinin** ilk beşte olması. Bütün gerekli kanıtların geldiğini, küçük bir token bütçesine sığdığını veya yanıtın doğru olduğunu göstermez. Kendi raporu her soru için yaklaşık 48 oturumdan ayrı indeks kurulduğunu da açıklıyor. [Metodoloji](https://github.com/rohitg00/agentmemory/blob/c5b8ebfb32eb6a08fe301d3bb75840f3597b66c8/benchmark/LONGMEMEVAL.md).
- MemPalace ham/hibrid/LLM rerank sonuçlarını ayırıyor. %100'e ulaşan bir ayarın belirli yanlış sorular incelenerek iyileştirildiğini kendi benchmark belgesinde açıklaması, o sayıyı genel garanti saymamamız için yeterli. [Benchmark notları](https://github.com/MemPalace/mempalace/blob/develop/benchmarks/BENCHMARKS.md).
- Alice'ın LongMemEval belgesi, evidence oturum kimliklerindeki etiketlerin cevaplayıcıya görünmesiyle ilgili bilinen bir sorun taşıyor. Bu koşuldaki sayılar düzeltilmiş bağımsız bir kıyas yerine konamaz. [Açıklama](https://github.com/samrusani/AliceMemory/blob/a6a5f49eebb7377f40b388f2ffe07290b05b85fb/docs/benchmarks/longmemeval/README.md).
- Titen'in ayrılmış ve havuzlanmış veri koşulları çok farklı sonuç veriyor. Konu/kapsam daraltmanın faydası var; fakat doğru proje kimliği sisteme cevap anahtarından verilirse gerçek yönlendirme problemi ölçülmez. [Koşul karşılaştırması](https://github.com/RamaAditya49/titen/blob/23302a16d44d01f3759ef56287847f85352d0fc1/docs/testing/2026-08-07-pooled-store.md).

Bu nedenle “A %96, B %90; A daha iyi” biçiminde bir sıralama yapmadım. Recall@1, recall_any@5, bütün kanıtların kapsanması, QA doğruluğu ve aynı bütçedeki yanıt kalitesi ayrı ölçülerdir.

### 9.2 Bizim için uygun açık değerlendirmeler

| Kaynak | Neyi sınar? | Bizim kullanımımız |
|---|---|---|
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | Bilgi çıkarma, oturumlar arası akıl yürütme, güncelleme, zaman ve bilmiyorum diyebilme | Uzun sohbet hafızası için ana dış kıyas; temizlenmiş veri revizyonu sabitlenmeli |
| [LongMemEval-V2](https://github.com/xiaowu0162/LongMemEval-V2) | Ortamı tanıyan iş arkadaşı gibi davranma; iş akışı, değişen durum, yerel tuzaklar | Proje/skill/tool ve “nasıl çalışıyoruz?” beklentine özellikle yakın |
| [LoCoMo](https://github.com/snap-research/locomo) | Uzun dönemli diyalog, zamansal/çok adımlı sorular | Tamamlayıcı; repo lisansı CC BY-NC 4.0, veri/dağıtım koşulları ayrıca korunmalı |
| Kendi Türkçe kabul setimiz | Gerçek dil, kapsam ve kişisel karar değişiklikleri | İngilizce benchmark başarılarının Türkçeye taşındığını varsaymamak için şart |

LongMemEval'in [makalesi](https://arxiv.org/abs/2410.10813) ve LoCoMo'nun [makalesi](https://arxiv.org/abs/2402.17753), bunların yalnız hızlı arama benchmark'ı olmadığını gösteriyor. Veri setleri geliştirme, test ve hak/lisans açısından kendi koşullarıyla kullanılmalı.

### 9.3 Önerdiğim karşılaştırma protokolü

**Aynı olay kaydı, aynı kaynak kapsamı, aynı son cevap modeli ve aynı bağlam bütçesi:** mevcut çekirdek, yalın FTS5 tabanı, Titen prototipi, Basic Memory prototipi. memU'nun ajan hazırlama yolu ayrıca aynı yazma bütçesiyle denenir. Bütün sistemleri aynı anda üretime kurmak yerine ayrı sentetik/izinli corpus üzerinde ölçeriz.

İki koşul gereklidir: proje/kapsamın çağıran tarafından bilindiği durum ve doğal sorudan bulunması gereken durum. Bir de tek kullanıcıya ait tüm yılın karışık geçmişi olmalıdır; yalnız her soru için küçük ve temiz bir havuz yetmez. Kaynak kimlikleri rastgeleleştirilir, gold cevap/oturum etiketleri erişim katmanına verilmez. Önce corpus yazılır, sonra sorular sorulur; gelecekteki güncelleme önceden bilinememelidir.

Ölçüler: doğru kaynak recall@k, **bütün gereken kanıtların kapsanması**, yanlış eski değeri seçme, gerekçesiz cevap verme, kaynakla doğrulanabilir yanıt doğruluğu, kişisel kapsam ihlali, sağlayıcının ölçtüğü giriş/çıkış token'ı, toplam araç turu ve soğuk/sıcak p50–p95–p99 gecikme. Yazma, sorgu ve bakım maliyetleri ayrı tutulur. Kayıt kabul edildiğinde process öldürme, tekrar gönderme, elektrik kesintisi benzeri durumlar ve eski yedekten geri yükleme ayrıca sınanır. Bu araştırmada bu deneyler bütün upstream adaylarda çalıştırılmadı.

Önerilen Türkçe set, en az şu senaryoları içermeli:

1. 365 gün önce söylenmiş, sonradan hiç erişilmemiş bir ayrıntı.
2. “SQLite seçtik” sonrasında “PostgreSQL'e geçtik”; geçmiş ve bugün için farklı doğru cevap.
3. Aynı isimde iki proje ve iki kişi; doğru kapsamı sorudan bulma.
4. `İ/ı`, Türkçe ekler, kısaltmalar ve Türkçe/İngilizce eş anlamlı sorular.
5. Üç veya daha fazla ilişki üzerinden gereken kanıt; mevcut iki adım sınırının kaçırdığı örnek.
6. Yeni skill sürümü, devre dışı tool ve başka makinede mevcut olmayan yetenek.
7. Soruda ima edilen fakat hiç kaydedilmemiş bilgi; doğru “kayıt bulamadım” yanıtı.
8. AI çıkarımı ile doğrudan kullanıcı tercihi arasındaki fark.
9. Tekrar işlenen aynı olay ile farklı günlerde aynı cümlenin tekrar söylenmesi.
10. Silinen kaynak, ondan türemiş özet ve eski yedekten geri gelme denemesi.

## 10. Mevcut projemize dürüst etkisi

Mevcut `MEMORY_DATABASE.md`, `directory.py`, `retrieval.py`, `remember.py`, `memory.py` ve ilgili test/raporlar üzerinden değerlendirdim. Bu bölüm dış projelerin ölçümü değil, bizim kodumuz hakkındaki incelememdir.

**Doğru yönde olanlar:** tek kanonik SQLite, kaynak ile aday bilgiyi ayırma, valid/known time, harita/kart/kaynak erişimi, kaynak aralığı, düzeltme referansı, izinli projeksiyonlar, küçük bütçe, artımlı indeks ve önbellek. Bunları yeni bir hafıza framework'ü geldi diye silmek gerekmez.

**Hedefin henüz tamamı olmayanlar:**

- İstemcinin seçtiği kısa alıntı, bütün özgün konuşmanın alındığını kanıtlamaz. Tam kapsamlı yakalama ve kapsama raporu, arama algoritmasından önce gelmeli.
- `remember.actor` istemciden bildiriliyor. Güvenilir host olayı ile modelin yeniden anlattığı kullanıcı sözü farklı kanıt sınıfları olmalı; mümkünse gerçek olay kimliği/aralığına referans verilmeli.
- Başlık yolları ve küçük sözlük, genel Türkçe anlam/alias çözümünü tek başına karşılamıyor. Sorgu kaçırmaları ölçülmeli.
- Sınırlı aday sayısı ve iki graf adımı maliyeti sınırlar; bütün ilişkili kanıtların bulunmasını garanti etmez. Gerekli durumda bütçeli genişletme ve görünür eksiklik gerekir.
- Onaylı bilgi haritası ile henüz kaynak seviyesindeki konuşma bilgisi farklı. Kaynak hemen aranabilir olsa da sürekli büyüyen bir arşivde tüm anlamlı bilgilerin yapılandırılması ve inceleme yükü için açık politika gerekiyor.
- Mevcut MCP talimatı modelin her turda doğru araç çağıracağını garanti etmez. Host adaptörü, güvenilir checkpoint ve gerçekten uygulanmış yakalama yolu ölçülmeli.
- Geçen 117 uygulama testi, yıl boyu gerçek kişisel corpus'ta kusursuz hatırlama veya toplam token tasarrufu kanıtı değil.

## 11. Bundan sonra önerdiğim sıra

| Sıra | İş | Tamamlandı sayılması için kanıt |
|---|---|---|
| 1 | Gerçek yakalama sözleşmesi ve kaynak arşivi | Seçilmiş host'larda olay kapsamı, kararlı kimlik, tekrar ve çökme testi; kayıt alınmadığında açık durum |
| 2 | Tipli kişisel şema ve düzeltme akışı | Tercih/proje/skill/tool/çalışma noktası ayrımı; kaynak aralığı; geçmiş/güncel ve inceleme politikası |
| 3 | Aynı veride rakip prototipler | FTS5 tabanı, mevcut çekirdek, Titen ve Basic Memory; aynı bütçe ve aynı sorular |
| 4 | Kaçırılan sorulara göre iyileştirme | Önce alias/kapsam/yönlendirme; gerekiyorsa yerel embedding veya sorguya bağlı graf yayılımı |
| 5 | Ölçülen güvenli otomatik bakım | Özet/projection tazeliği, duplicate işaretleme, erasure closure; ham kaynak için otomatik yaş silmesi yok |

**Bugün seçim yapmam gerekirse:** verinin sahibini değiştirmeden devam ederim; memU'dan mevcut ajana iş devretme sözleşmesini, OpenViking'den katmanlı temsili, Titen'den kanıt/iddia ve bütçeli derleme modelini alırım. Hazır ürüne geçiş ihtimalini açık tutar, önce Titen ve Basic Memory ile ölçerim. Capture için agentmemory yaklaşımını incelerim ama onun depo ve otomatik unutma varsayılanlarını kopyalamam. HippoRAG/Graphiti/PageIndex'i ancak belirli, ölçülmüş bir sorun için devreye alırım.

Bu yaklaşımın başarısı “daha fazla motor kurduk” ile değil, **doğru ve güncel kanıta daha az gereksiz içerikle, sürdürülebilir maliyetle ulaşabildik mi?** sorusuyla ölçülmeli.

## Ek A. Tam kaynak envanteri

Envanter; adayların değerlendirme kapsamını, kontrol anındaki arşiv durumunu ve üst düzey lisansını gösterir. Her bağımlılığın ve dağıtılan binary'nin lisansı denetlendi anlamına gelmez. GitHub'ın otomatik lisans etiketi ile gerçek dosya farklıysa metin esas alındı. AGPL açık kaynak bir lisanstır; burada “kullanılamaz” denmiyor. Kod alma, ayrı servis kullanma ve dağıtım planı için lisans incelemesi yapılmalıdır.

<!-- INVENTORY_START -->
| Depo | İncelenen rol | Üst düzey lisans / kapsam | Son push (UTC) / arşiv durumu | Sabitleme |
|---|---|---|---|---|
| [NevaMind-AI/memU](https://github.com/NevaMind-AI/memU) | Mevcut ajanla hafıza yazma | Apache-2.0 (metin) | 2026-10-26 / arşivli değil | `42ef9fa3a803` |
| [volcengine/OpenViking](https://github.com/volcengine/OpenViking) | Katmanlı bağlam altyapısı | AGPL-3.0 | 2026-10-26 / arşivli değil | `5c066d97094d` |
| [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | Taşınabilir kişisel bilgi tabanı | AGPL-3.0 | 2026-10-26 / arşivli değil | `9643ec25918e` |
| [doobidoo/mcp-memory-service](https://github.com/doobidoo/mcp-memory-service) | Yerel semantik hafıza | Apache-2.0 | 2026-10-26 / arşivli değil | `ef25b93d9565` |
| [samrusani/AliceMemory](https://github.com/samrusani/AliceMemory) | Kaynaklı oturum devamlılığı | MIT | 2026-10-26 / arşivli değil | `a6a5f49eebb7` |
| [RamaAditya49/titen](https://github.com/RamaAditya49/titen) | Modelsiz kaynak/iddia çekirdeği | Apache-2.0 | 2026-10-19 / arşivli değil | `23302a16d44d` |
| [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory) | Host yakalama ve devamlılık | Apache-2.0 | 2026-10-26 / arşivli değil | `c5b8ebfb32eb` |
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | MCP referans sunucuları | MIT → Apache-2.0 geçişi; docs CC BY 4.0 | 2026-10-25 / arşivli değil | `ef9808f71090` |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | Hafıza API'si | Apache-2.0 | 2026-10-26 / arşivli değil | `main` + dosya SHA-256 |
| [getzep/graphiti](https://github.com/getzep/graphiti) | Zamansal bilgi grafiği | Apache-2.0 | 2026-10-26 / arşivli değil | `5c27edfa8d3e` |
| [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) | Retain/recall/reflect hafızası | MIT | 2026-10-26 / arşivli değil | `main` + dosya SHA-256 |
| [MemTensor/MemOS](https://github.com/MemTensor/MemOS) | Hafıza ve skill yaşam döngüsü | Apache-2.0 | 2026-10-26 / arşivli değil | `main` + dosya SHA-256 |
| [topoteretes/cognee](https://github.com/topoteretes/cognee) | Graf/semantik veri hattı | Apache-2.0 | 2026-10-26 / arşivli değil | `main` + dosya SHA-256 |
| [letta-ai/letta](https://github.com/letta-ai/letta) | Stateful ajan runtime'ı | Apache-2.0 | 2026-10-18 / arşivli değil | `main` + dosya SHA-256 |
| [memvid/memvid](https://github.com/memvid/memvid) | Taşınabilir hafıza dosyası | Apache-2.0 | 2026-07-14 / arşivli değil | `main` + dosya SHA-256 |
| [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory) | Açık SDK; sunucu çekirdeği kapalı | MIT açık repo; sunucu kapalı | 2026-10-25 / arşivli değil | `main` + dosya SHA-256 |
| [OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) | İlişkisel erişim araştırması | MIT | 2026-10-06 / arşivli değil | `d5c8329422e0` |
| [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex) | Belge ağacı ve reasoning erişimi | MIT | 2026-10-26 / arşivli değil | `e38b40ebaeea` |
| [parthsarthi03/raptor](https://github.com/parthsarthi03/raptor) | Özet ağacı araştırması | MIT | 2024-09-03 / arşivli değil | `master` + dosya SHA-256 |
| [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | Graf + vektör RAG | MIT | 2026-10-22 / arşivli değil | `main` + dosya SHA-256 |
| [langchain-ai/langmem](https://github.com/langchain-ai/langmem) | Ajan hafıza araçları | MIT | 2026-10-26 / arşivli değil | `main` + dosya SHA-256 |
| [MemoriLabs/Memori](https://github.com/MemoriLabs/Memori) | SQL hafıza entegrasyonu | Apache-2.0 (metin) | 2026-10-03 / arşivli değil | `main` + dosya SHA-256 |
| [MemPalace/mempalace](https://github.com/MemPalace/mempalace) | Özgün konuşma arşivi/erişim | MIT | 2026-10-25 / arşivli değil | `develop` + dosya SHA-256 |
| [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | Host capture ve AI sıkıştırması | Apache-2.0 | 2026-10-26 / arşivli değil | `main` + dosya SHA-256 |
| [networkx/networkx](https://github.com/networkx/networkx) | Graf algoritmaları kütüphanesi | BSD-3-Clause (metin) | 2026-10-22 / arşivli değil | `main` + dosya SHA-256 |
| [kuzudb/kuzu](https://github.com/kuzudb/kuzu) | Arşivlenmiş embedded graf DB | MIT | 2025-10-10 / arşivli | `master` + dosya SHA-256 |
| [LadybugDB/ladybug](https://github.com/LadybugDB/ladybug) | Embedded graf DB | MIT | 2026-10-26 / arşivli değil | `main` + dosya SHA-256 |
| [unum-cloud/USearch](https://github.com/unum-cloud/USearch) | Vektör ANN kütüphanesi | Apache-2.0 | 2026-10-25 / arşivli değil | `main` + dosya SHA-256 |
| [xiaowu0162/LongMemEval](https://github.com/xiaowu0162/LongMemEval) | Uzun sohbet değerlendirmesi | MIT | 2026-05-11 / arşivli değil | `main` + dosya SHA-256 |
| [snap-research/locomo](https://github.com/snap-research/locomo) | Diyalog veri/değerlendirme deposu | CC BY-NC 4.0; OSS lisansı değil | 2024-08-13 / arşivli değil | `main` + dosya SHA-256 |
| [agiresearch/A-mem](https://github.com/agiresearch/A-mem) | Bağlantılı ajan notları araştırması | MIT | 2025-12-12 / arşivli değil | `main` + dosya SHA-256 |
| [Cipher208/a-memory](https://github.com/Cipher208/a-memory) | SQLite katmanlı hafıza | MIT | 2026-10-26 / arşivli değil | `master` + dosya SHA-256 |
| [OpenAgentHQ/localmem-mcp](https://github.com/OpenAgentHQ/localmem-mcp) | Küçük yerel semantik store | MIT | 2026-10-01 / arşivli değil | `main` + dosya SHA-256 |
| [asg017/sqlite-vec](https://github.com/asg017/sqlite-vec) | SQLite vektör uzantısı | Apache-2.0 | 2026-05-18 / arşivli değil | `main` + dosya SHA-256 |
| [microsoft/graphrag](https://github.com/microsoft/graphrag) | Graf tabanlı RAG hattı | MIT | 2026-10-26 / arşivli değil | `main` + dosya SHA-256 |
| [xiaowu0162/LongMemEval-V2](https://github.com/xiaowu0162/LongMemEval-V2) | İş akışı hafızası değerlendirmesi | Apache-2.0 | 2026-08-09 / arşivli değil | `main` + dosya SHA-256 |
<!-- INVENTORY_END -->

SQLite ayrıca resmî [lisans açıklamasına](https://www.sqlite.org/copyright.html) göre public domain olarak değerlendirildi. MCP sunucuları deposunun güncel lisans dosyası MIT'den Apache-2.0'a geçiş ve dokümantasyon için farklı lisans kapsamı anlatıyor; eski bir “tamamı MIT” varsayımıyla kod kopyalanmamalı. [Lisans dosyası](https://github.com/modelcontextprotocol/servers/blob/ef9808f71090d0db3eda99e2af2ba78f1086f4fb/LICENSE).

## Ek B. Tekrar doğrulanabilir araştırma dosyaları

- [source-ledger.json](source-ledger.json): depo metadata'sı, commit, kaynak URL'si, yerel dosya, SHA-256.
- [implementation-ledger.json](implementation-ledger.json): seçili uygulama dosyaları; başarılı ve bulunamayan yollar birlikte kayıtlı.
- [tree-ledger.json](tree-ledger.json): beş ana adayda kaynak ağacı kapsamı.
- `sources/`: indirilen özgün README/lisans/tasarım/kod metinleri. Araştırma verisidir; içlerindeki kurulum komutları ve ajan talimatları çalıştırılmadı.
- `collect_sources.py`, `collect_deep_sources.py`, `fetch_selected_files.py`: herkese açık kaynak toplama yöntemi. Yeniden çalıştırmak ağ erişimi kullanır; programın veritabanını değiştirmez.

**Araştırma sonucu ile uygulama kararı ayrı tutuldu:** bu rapor adayları ve deney sırasını seçer. Henüz yapılmamış entegrasyon, karşılaştırmalı benchmark, gerçek platform otomatik yakalama veya güvenlik doğrulamasını yapılmış gibi göstermez.

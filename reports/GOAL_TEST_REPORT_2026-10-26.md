# Second Brain OS — kullanıcı hedefleri test raporu

**Tarih:** 26 Ekim 2026, Windows / Python 3.12, yerel CPU.

**Test durumu:** Tamamlandı. Kapanış: 2026-10-26T12:08:01+03:00.

**Karar: Hedefler kısmen karşılanıyor.** Kalıcı depolama, temel yetki sınırları, şifreli yedekleme, skill sürüm yönetimi ve yerel protokol altyapısı çalışıyor. Ancak uygulama, kullanıcının konuşmalarını kendiliğinden öğrenen ve her projede doğru tercih/kuralları modele taşıyan tamamlanmış kişisel beyin olarak kabul edilemez. Kritik bağlam ve keşif eksikleri var; canlı kişisel veri ve model bağlantısı henüz yok.

Bu rapor yarıda kalan test çalışmasını devralır. Önceki performans ölçümleri korunmuş, tam uygulama testleri ve hedef odaklı deneyler yeniden çalıştırılmıştır. Ürün kodunda hata düzeltmesi yapılmadı; test araçları ve kanıt raporları eklendi. Testin tamamlanması, açık ürün eksiklerinin giderildiği anlamına gelmez.

## 1. Baştaki hedeflerle karşılaştırma

| Kullanıcı hedefi | Sonuç | Somut kanıt / sınır |
|---|---|---|
| Tercihlerimi kalıcı sakla | Kısmen | Onaylanmış kayıtlar süreç yeniden başlatmasında ve yedekten dönüşte korunuyor. Serbest Türkçe tercih cümlelerinden otomatik aday çıkarımı 0/8; özel `Tercihim:` / `Kuralım:` sözdizimi 2/2. |
| Konuşmalardan alınan dersleri öğren | Kısmen | Aynı ders üç ayrı kaynak olayda tekrarlandığında tek aday oluşuyor; kullanıcı onayı gerekiyor. Aynı kaynak olayın tekrar gönderimi sayıyı şişirmiyor. Aynı anlamın farklı cümleleri birleştirilmiyor. |
| Projeleri, kararları ve konuşma konularını hatırla | Kısmen | Kayıt/sürüm/zaman sorguları çalışıyor. Ham konuşma timeline içinde görünse de onaylanmış hafızaya dönüşmedikçe normal recall ile bulunmuyor. Proje bağlamına genel tercihler ve kurallar eklenmiyor. |
| Skill'leri koru ve AI kullanımına sun | Kısmen | ZIP orijinali, sürümler, etkinleştirme, eski sürüme dönüş ve SKILL.md erişimi çalışıyor. Modelin `brain.get_skill` yanıtında paketteki yardımcı script içeriği yok; keyfi script çalıştırma uygulanmamış. |
| Tool'ları koru ve AI kullanımına sun | Eksik | Tool envanteri ve şifreli tam yedek mevcut. Etkin tool tanımı modelin capability/context çıktısında yok; canonical JSON/JSONL export tool tanımlarını taşımıyor. Harici MCP tanımı çalıştırılan bir entegrasyon anlamına gelmiyor. |
| AI ihtiyaç duyduğu doğru bilgiyi kullansın | Kısmen | Gerçek HTTP/MCP üzerinden kaynaklı retrieval doğrulandı. Küçük Türkçe deneyde semantik arama yardımcı oluyor ama tüm doğal soruları çözemiyor. Gerçek bir üretken modelin nihai cevapları değerlendirilmedi. |
| Gereksiz kaynak tüketmeden çalış | Kısmen | Boşta temel süreç hafif; model yüklendiğinde bellek ciddi artıyor. BM25 her sorguda corpus/ranker kuruyor, vektör arama kayıtları doğrusal tarıyor. Büyük, indeksli semantik yük ve çok saatlik dayanıklılık garantisi yok. |
| Gerçek sohbetlerim ve kullandığım AI ile hazır çalış | Henüz doğrulanmış değil | Canlı veritabanında olay, hafıza, skill, tool ve model token sayıları sıfır. HTTP servisinin sağlıklı olması kişisel AI bağlantısının etkin olduğu anlamına gelmiyor. |

## 2. Uygulama test paketi ve kalite denetimleri

Tam paket: **64 geçti, 0 başarısız, 0 atlandı; 19,50 saniye.** [JUnit](goal-audit-final-tests-20261026.xml), [konsol kaydı](goal-audit-final-pytest-20261026.log).

Bu paket gerçek SQLite işlemlerini, zamansal düzeltmeleri, çelişkileri, scope/tenant/clearance sınırlarını, modelin kendini onaylayamamasını, capture/import tekrarlarını, job iptal/retry akışını, silme ve restore sonrasında yeniden içeri almama davranışını, migration'ı, gerçek HTTP + subprocess stdio MCP akışını, yerel embedding/Mem0, OCR/PDF/ses/video yollarını kapsıyor. Opsiyonel motor ve medya testleri bu çalıştırmada atlanmadı.

Tek uyarı Qdrant local payload indekslerinin etkisizliğiyle ilgili; test hatası değil, server Qdrant performansı kanıtı da değil.

Ruff lint, Ruff format, mypy (`--check-untyped-defs`, strict değil), iki JavaScript dosyasının sözdizimi ve kaynak secret taraması: **6/6 başarılı**. Secret taraması sıfır bulgu verdi; pattern taraması kapsamlı güvenlik incelemesi yerine geçmez. [Makine çıktısı](goal-audit-20261026/final/quality.json).

Windows sandbox içindeki ilk HTTP test denemesi socketpair işlemi sırasında ilerlemedi ve durduruldu. Yukarıdaki sonuç loopback erişimi olan ortamda, ayrı sentetik test dizininde tamamlanan çalıştırmaya aittir. Bu durum önceki sohbetin model kapasitesi hatasından ayrıdır.

## 3. Ek kabul kontrolleri

**15 kontrol: 11 başarılı, 4 hedef karşılanmadı.** Bunlar yukarıdaki 64 testten ayrı, kullanıcı hedeflerine göre hazırlanmış kabul deneyleridir. Başarısız kabul koşulları gizlenmemiştir; deney betiğinin işlemi tamamlaması ürünün bütün koşulları geçtiği anlamına gelmez.

| Kabul koşulu | Sonuç |
|---|---|
| Tamamen ayrı Python süreci açıldığında 8 olay / 3 hafıza / 2 skill / 1 tool korunur | Geçti |
| Yeni skill sürümü etkinleşince eski sürüm devre dışı kalır | Geçti |
| Şifreli yedekten dönüşte bütün okunan satırlar, skill ZIP byte'ları ve tool etkinlik durumu korunur | Geçti |
| Eski skill sürümüne dönüş orijinal paketi korur | Geçti |
| Devre dışı skill modelden gizlenir | Geçti |
| Proje bağlamı yetkili model için genel tercih ve kuralları da taşır | **Karşılanmadı** |
| Konulu görev bağlamı genel kullanıcı kuralını da taşır | **Karşılanmadı** |
| 149 farklı bağlam bütçesinde byte sınırı ve üst tahmin korunur | Geçti |
| Bağlam kaynakları verilen kayıtların kaynaklarıyla aynı olur | Geçti |
| Canonical JSON/JSONL export tool tanımlarını içerir | **Karşılanmadı** |
| Etkin tool capability veya context üzerinden modelce keşfedilir | **Karşılanmadı** |
| Okuma yetkili model onaylayamaz veya silemez | Geçti |
| Yalnız proje yetkili okuyucu global kayıtları veya skill'leri göremez | Geçti |
| Dört istemcinin sabit kimlikli hook tekrarları çoğaltılmaz | Geçti |
| Aynı kaynak feedback 8 kez gönderildiğinde tek kanıt kalır | Geçti |

[Ayrıntılı gözlemler](goal-audit-20261026/final/supplemental.json), [deney kodu](../scripts/goal_audit_completion.py).

## 4. Türkçe anlama ve hatırlama deneyi

12 onaylanmış sentetik hafıza, 24 bilinen cevaplı sorgu: 12 anahtar kelime, 4 doğal soru, 8 farklı ifadeyle sorulmuş soru. Sonuç doğru kaydın ilk sırada gelmesidir. Bu küçük, hedefli bir tanı deneyidir; genel başarı oranı olarak genellenemez.

| Motor / indeks | Anahtar kelime | Doğal soru | Farklı ifade |
|---|---:|---:|---:|
| FTS, vektörsüz | 12/12 | 0/4 | 0/8 |
| BM25, vektörsüz | 12/12 | 0/4 | 0/8 |
| Hybrid, vektörsüz | 12/12 | 0/4 | 0/8 |
| Gerçek yerel vector, 12 kayıt indeksli | 10/12 | 3/4 | 3/8 |
| Gerçek yerel hybrid, 12 kayıt indeksli | 12/12 | 3/4 | 3/8 |

Örneğin kayıtlı `SecondBrain SQLite` anahtarları bulunurken, “Hafıza uygulamamızda hangi veritabanına karar verdik?” sorusu indeksli hybrid ile de bulunamadı. Anahtar kelime doğruluğuyla doğal dil başarısı aynı şey değildir. FTS varsayılan arama motorudur; bağlamın konulu araması hybrid kullanır.

Bilgisi bulunmayan 6 soru, her 5 motor/indeks koşulunda boş sonuç ve `abstain=true` üretti. Bu, 6 ayrı bilinmeyen sorunun 30 motor koşulu denemesidir; 30 bağımsız soru değildir. Nihai bir dil modelinin yanıt üretimini ölçmez.

Tercih çıkarımında 8 serbest cümle aday üretmedi; özel sözdizimli 2 kontrol üretti. İki uyumlu tercih (`Kısa cevap`, `Koyu tema`) aynı genel predicate nedeniyle sırasıyla `active`, `disputed` oldu. Bu gerçek bir kullanım eksikliğidir; zaman/çelişki testlerinin geçmesiyle kapanmaz.

Aynı anlamdaki üç farklı düzeltme cümlesi ayrı ayrı birer kanıt sayıldı, ders adayı oluşmadı. Tam aynı metnin 8 ayrı olayda tekrarı ise tek ders adayı oluşturdu; onaydan önce aktif ders sayısı sıfır kaldı.

[Güncel deney verileri](goal-audit-20261026/final/functional.json). Yerel embedding deneyinde socket bağlantıları engellenmişken ağ girişimi sayısı sıfırdı; bu gözlem bütün uygulama yollarının evrensel ağ güvenliği garantisi değildir.

## 5. Kaynak tüketimi ve ölçek

### Boşta çalışma ve RAM

- Canlı servis 3 salt okunur sağlık/durum ölçümünde HTTP 200 döndü; yanıtlar yaklaşık 30–38 ms, RAM yaklaşık **71,7 MB** oldu.
- Ayrı temel sentetik süreç, embedding yüklenmeden yaklaşık **57,5 MB**; 12 kayıtlık yerel model deneyinden sonra yaklaşık **746,1 MB** RAM kullandı. Model dosyaları kurulu olsa bile yükleme maliyeti ayrıca oluşuyor.
- 60 saniyelik boş worker ölçümünde bir mantıksal çekirdeğin yaklaşık **%0,39'u** kullanıldı; RAM farkı yaklaşık **0,74 MB**, saniyede yaklaşık **1,97 veritabanı bağlantısı** açıldı. Worker düzgün durdu. Bu süre uzun vadeli bellek sızıntısı olmadığını ispatlamaz.
- `.venv` yaklaşık 714 MB, model dosyalarının da bulunduğu `data` yaklaşık 835 MB: yalnız bu iki dizin toplam yaklaşık **1,55 GB**. Bu geliştirme ortamı boyutudur, optimize minimal kurulum boyutu değildir.

[Boşta 60 saniye](goal-audit-20261026/final/soak.json), [canlı HTTP](goal-audit-20261026/final/live-http.json), [disk/metadata](goal-audit-20261026/final/live-metadata.json).

### Önceki oturumdan korunan 50.000 kayıt ölçümü

Her motor için 30 sorgu. 50.000 olay / 50.000 hafıza; veritabanı yaklaşık 60,7 MB. Bu ölçüm aynı gün önceki test çalışmasından alınmıştır; bu devam turunda yeniden çalıştırılmadı.

| Motor | p50 | p95 | Deneyin ≤2 saniye eşiği |
|---|---:|---:|---|
| FTS | 8,17 ms | 8,94 ms | Geçti |
| BM25 | 1.095,18 ms | 1.439,19 ms | Geçti |
| Hybrid, vektörsüz | 1.420,37 ms | 1.797,73 ms | Geçti |

**Bu 50.000 kayıt deneyinde semantik indeks yok.** Hybrid sonucunu 50.000 indeksli embedding aramasının sonucu gibi yorumlamak yanlış olur. [Korunan ham ölçek raporu](goal-audit-20261026/performance.json), [benchmark kodu](../second_brain/benchmark.py).

### Ek gerçek semantik ölçek ölçümü

1.000 sentetik hafıza gerçek yerel multilingual embedding modeliyle indekslendi. İndeksleme **441,94 saniye (7 dakika 22 saniye)** sürdü; 1.000 kayıt / 1.000 chunk üretildi. İndeks sonrası süreç RAM'i yaklaşık **933,3 MB** oldu. Bu süre kayıtların ilk oluşturulmasını içermez; modelin yüklenmesi ve gerçek indeksleme yolunu içerir.

| Motor, 1.000 kayıt gerçekten indeksli | Sorgu sayısı | p50 | p95 |
|---|---:|---:|---:|
| Vector | 10 | 133,21 ms | 135,72 ms |
| Hybrid | 10 | 160,04 ms | 172,26 ms |

Bu deneyde sorgu kalitesi puanlanmadı; 10 örnekte nearest-rank p95 en yavaş örneğe denk gelir. RAM ölçümü süreç working set'idir, tepe RAM değildir. 50.000 gerçek semantik kaydın veya eşzamanlı sorguların performansı bu veriden kanıtlanamaz. [Ham semantik ölçüm](goal-audit-20261026/final/semantic-scale.json).

Kod incelemesinde BM25 için her sorguda adayların okunup tokenize edildiği ve `BM25Okapi` nesnesinin yeniden kurulduğu; vector aramada uygun vektörlerin JSON'dan çözülüp doğrusal tarandığı görüldü. İndeksleyici ayrıca her hafıza için tokenizer'ı serialize/parse ederek kopyalıyor ve embedding'i ayrı çağırıyor. Bunlar kaynak kodundan gözlenen işlemlerdir; toplam süredeki ayrı payları profillenmedi. Bu tasarımın “aşırı optimize” olduğu söylenemez. Tokenizer tekrar kullanımı, cache, toplu embedding ve kalıcı vektör indeksleri ayrı iyileştirme konularıdır; yalnız bu ölçümlerden belirli bir hız kazancı vaat edilemez. [Arama kodu](../second_brain/retrieval.py), [embedding/index kodu](../second_brain/providers.py).

## 6. Öncelikli açıklar ve kapanış ölçütleri

| Öncelik | Açık | Kapanış için gereken kanıt |
|---|---|---|
| P1 | Genel kurallar/tercihler proje ve konu bağlamından düşüyor | Global + proje yetkili model her iki grubu bütçe içinde almalı; yalnız proje yetkili modele global veri sızmamalı. Sığmayan zorunlu kural için açık uyarı olmalı. |
| P1 | Bağımsız tercihler aynı predicate altında çelişiyor | `Kısa cevap` ve `Koyu tema` birlikte aktif olmalı; gerçek birbirini geçersiz kılan tercihler sürümlenmeli. |
| P1 | Serbest konuşma otomatik kullanılabilir hafızaya dönüşmüyor | Açık extraction/proposal ve kullanıcı onayı akışı; Türkçe tercih/düzeltme/proje örnekleri ve hatalı çıkarım ölçümü. Ham kayıt ile onaylı hafıza ayrımı korunmalı. |
| P1 | Tool envanteri AI'ya ve canonical export'a taşınmıyor | Güvenli metadata capability/context içinde bulunmalı; export/import ile korunmalı. Keşif ile çalıştırma izni ayrı tutulmalı. |
| P1 | Canlı kişisel corpus ve AI bağlantısı yok | Kısıtlı token ile gerçekten kullanılan istemciden capture → proposal → onay → kaynaklı recall zinciri; kullanıcının mevcut verisi korunarak ayrı doğrulama. |
| P2 | Türkçe retrieval ve derslerin anlam eşlemesi zayıf | Daha büyük bağımsız Türkçe sorgu kümesi, negatifler, zaman ve scope kontrolleri; doğru kayıt ve gereksiz sonuç ölçümleri. |
| P2 | Skill paketi var ama yardımcı dosya/model erişimi sınırlı | İzinli dosya okuma/export ve bağımlılık yolu; gerçek host üzerinde görev başarısı. Keyfi otomatik çalıştırma varsayılmamalı. |
| P2 | İndeksleme ve arama maliyeti büyüyor | Kalıcı indeks/cache/batch uygulandıktan sonra aynı donanım ve veriyle tekrar ölçüm; RAM/CPU ve kalite birlikte raporlanmalı. |

## 7. Bu sonuçların sınırları

Sentetik kayıtlar kullanıldı; kullanıcı `data/` veritabanına test hafızası, skill veya model token'ı eklenmedi. Canlı serviste yalnızca sağlık/durum okundu, veritabanında yalnız metadata ve bütünlük sorgulandı. Canlı snapshot'ta bütünlük `ok`, olay/hafıza/skill/tool/token sayıları sıfırdı.

Gerçek ChatGPT/Claude/Gemini/Cursor hesap aktivasyonu, kişisel sohbetleri içeri alma, üretken LLM cevap kalitesi, çok saatlik yük, 50.000 gerçek semantik kayıt, çoklu eşzamanlı kullanıcı, her güç kesintisi noktası, Docker/Linux/macOS ve Türkçe gerçek ses kalite benchmark'ı bu raporda başarılı sayılmıyor. Bunlar ürünün hazır olduğunu kanıtlayan testler olarak sunulamaz. Bağlanmamış hesaplar için aktivasyon yapılmadı.

Arayüz için önceki [UI doğrulaması](UI_QA.md) ve görseller mevcut. Bu devam turunda yeni tarayıcı tıklama testi yapılmadı; HTTP ve JavaScript doğrulaması yeniden çalıştı. Önceki UI raporu bu turda yeni gözlem yapılmış gibi sunulmuyor.

ID'siz hook'larda iki aynı payload ayrı olay olarak korunuyor. Sabit kaynak kimliği olmadan tekrar teslim ile bilerek yinelenen mesaj ayrımı yapılamadığı için hem eksiksiz saklama hem kusursuz tekrar ayıklama birlikte garanti edilemez. Tam aynı olay kimlikli tekrarlar dört istemcide de ayıklandı.

## 8. Yeniden çalıştırma

Proje kökünde, `.venv` ve mevcut yerel modellerle:

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp/goal-audit-repeat --junitxml=reports/goal-audit-repeat.xml
.\.venv\Scripts\python.exe scripts/goal_audit.py functional --output-dir reports/goal-audit-repeat
.\.venv\Scripts\python.exe scripts/goal_audit_completion.py supplemental
.\.venv\Scripts\python.exe scripts/goal_audit_completion.py soak
.\.venv\Scripts\python.exe scripts/goal_audit_completion.py semantic-scale
.\.venv\Scripts\python.exe scripts/goal_audit_completion.py quality
```

Completion betiği sonuçlarını `reports/goal-audit-20261026/final/` altında yazar; tekrar çalıştırma aynı adlı deney JSON'unu yeniler. Eski sonuçları korumak için önce bu rapor klasörünü kopyalayın. Gerçek kişisel veritabanını test için kullanmayın. HTTP/MCP testleri Windows ortamında yerel socket izni gerektirir.

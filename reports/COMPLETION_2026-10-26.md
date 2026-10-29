# Önceki sohbetin eksikleri üzerinde yapılan çalışma

26 Ekim 2026. Başlangıç değerlendirmesi: [gereksinim incelemesi](REQUIREMENTS_REVIEW_2026-10-26.md). Bu rapor son devam turuna aittir; önceki raporlar tarihsel kanıt olarak korunur.

## Sonuç

Üç öncelikte çalışan değişiklikler yapıldı: sınırlı Codex MCP bağlantısı kuruldu, farklı ifadelerde arama/öğrenme iyileştirildi ve semantik modelin sürekli RAM tutması giderildi. **Bütün kişisel AI vizyonu tamamlandı denmiyor:** kişisel hafıza hâlâ boş, otomatik sohbet yakalama ve gerçek model cevabı zinciri bu turda etkinleştirilmedi/doğrulanmadı.

## Yapılan değişiklikler

- **Codex bağlantısı:** Kullanıcının açık onayıyla yalnız `global` ve `secondbrain` kapsamlarında, clearance 1 ve `read/propose/capture` yetkili anahtar oluşturuldu. Codex config'ine yalnız Second Brain kaydı eklendi; diğer ayarlar korundu. Gizli değer config'e yazılmadı, yerel token dosyası kullanıldı. `brain.commit_memory` ve `brain.forget` istemci allowlist'ine alınmadı; sunucu yetki kontrolü de korunuyor. Eski config özel `data/connections/codex/config.before.toml` dosyasındadır.
- **Arama:** Hybrid akışına küçük Türkçe/İngilizce kavram sözlüğü ve önek eşleştirmesi eklendi. FTS/BM25 motorları ayrı davranışlarını korur. BM25/sözlük corpus'u tekrar kullanılır; vektörler JSON'u her sorguda tek tek çözmek yerine float32 matriste hesaplanır. Cache'ler boyut sınırlıdır ve şema 4 revision trigger'larıyla geçersizleşir. Yetki, zaman ve scope filtreleri korunur. Büyük matrisler gruplar halinde doğrusal taranır; ANN eklenmedi.
- **Öğrenme:** İki açık workflow eşdeğerliği yanında, yerel modelle ihtiyatlı semantik gruplama eklendi. 0,88 benzerlik, ortak terim, sayı, negatiflik ve bazı karşıt değer kontrolleri kullanılır; gruptaki gözlenen tüm ifadelerle eşleşme aranır. Scope, outcome, actor ve hassasiyet ayrılır. Üç farklı kaynak olayından sonra tek ders adayı oluşur. Tekrarlı feedback mevcut adayı yeniden üretmez. İnceleme listesi varyantları ve kaynakları birlikte gösterir; etkinleştirme kullanıcı onayı gerektirir.
- **Kaynak kullanımı:** Model ve parçalama tokenizer'ı ana servisten ayrı, seri çalışan offline sürece taşındı. İkinci tokenizer kopyası kaldırıldı; ONNX CPU arena kapatıldı. Süreç varsayılan 30 saniye boşta kalınca normal kapanır; sonraki istek modeli yeniden yükler. Windows UTF-8, launcher/gerçek Python süreç ayrımı, eşzamanlı istekler ve yeniden yükleme test edildi.

MCP config alanları [resmî OpenAI MCP belgesindeki](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) stdio, `cwd`, `env` ve `enabled_tools` sözleşmesine dayanır. Kullanılan kod ve gerçek protokol testleri ayrıca yerel kanıt sağlar.

## Ölçümler

| Kontrol | Sonuç |
|---|---|
| Tam uygulama testleri | **96 geçti**, hata/atlama yok; 21,94 saniye; bir beklenen Qdrant local uyarısı |
| Mevcut kabul kontrolleri | **15/15**; bütün ürün vizyonunu kapsamaz |
| Ruff, format, mypy, iki JS syntax, secret taraması | **6/6**; mypy strict değil |
| Eski 24 soruluk tanı kümesi, hybrid top-1 | **20/24**: anahtar sözcük 12/12, doğal soru 3/4, farklı ifade 5/8. Son incelemede farklı ifade 3/8 idi. |
| Ek 20 soruluk sentetik küme | **18/20** top-1; bilinmeyen beş soruda 0 kayıt |
| Aynı tıklama kuralının üç ifadesi | Kanıt sayısı **1 → 2 → 3**, tek inceleme adayı |
| Gerçek modelle üç dağıtım/test ifadesi | **1 → 2 → 3**, semantik ders adayı; olumsuz ve farklı sayılı örnekler ayrı |
| 10.000 gerçek semantik kayıt indeksleme | **120,98 saniye**, 10.000 chunk |
| 10.000 kayıt, sıcak hybrid arama | Medyan **232,65 ms**, örnek maksimumu **243,53 ms** |
| Dört eşzamanlı istek, 12 sorgu | Medyan **864,47 ms**, örnek maksimumu **1.078,15 ms** |
| İlk arama / cache hazırlama | **1.723,39 ms**; bu örnekte model zaten yüklüydü |
| İndeksleme sonrası ana süreç | **61,99 MB**; model süreci ayrıca **730,61 MB** örnekledi |
| Arama sonrası ana süreç | **130,65 MB**; model süreci ayrıca yaklaşık **730,68 MB** |
| 30 saniye boşta sonrası | Model süreci kapalı, ana süreç **130,61 MB** |
| Boş kişisel veritabanıyla canlı servis | Yaklaşık **69,90 MB**, model süreci kapalı |

MB değerleri byte/1.000.000 olarak verilmiştir. Bunlar working set örnekleridir; tepe RAM değildir. Aktif toplamda ana süreç ve modelin ikisi de hesaba katılmalıdır. Modelin aktif bellek maliyeti hâlâ yüksektir. 10.000 kayıt deneyi tek yerel koşudur; p95 sütununda kullanılan değer küçük örneklerin maksimumudur, istatistiksel güven aralığı yoktur. Veri hazırlama ölçülen indeks süresine dahil değildir. Ek soru kümesi bu geliştirme turunda yazılmıştır; bağımsız dış kalite benchmark'ı değildir. Son model cevabı doğruluğu ölçülmedi.

## Canlı durum ve sınırlar

Canlı servis son kodla yeniden başlatıldı; SQLite bütünlüğü `ok`, şema sürümü 4. Kullanıcının veritabanına sentetik olay/hafıza eklenmedi. Olay, hafıza, skill ve tool sayıları 0; kısıtlı bağlantı anahtarı sayısı 1.

Gerçek config'teki stdio komutu ve anahtar ile MCP initialize, bağlam okuma, kapsam dışı erişim reddi ve onay yetkisi reddi doğrulandı. Bu SDK testi Codex arayüzünde yeni araç kataloğunun yüklenmesi veya gerçek model cevabı testi değildir. **Yeni Codex oturumu açılması ya da uygulamanın yeniden başlatılması gerekebilir.** Bağlantı otomatik olarak bütün sohbetleri toplamaz. Mevcut hook ve açık thread kolektörü ayrı, kullanıcı tarafından başlatılan kayıt yollarıdır.

Otomatik onay denetimi ilk kalıcı erişim girişimini açık yetki eksikliğinden durdurdu; kullanıcı daha sonra sınırlı bağlantıyı açıkça onayladı ve bu bağlantı kuruldu. Ek kalıcı ajan talimatı ve otomatik mesaj yakalama yolu önerisi onay kapsamının dışında bulundu; bu ek değişiklikler uygulanmadı. Otomatik sohbet toplama/başlangıçta hafıza çağırma ve indirilen tüm skill/tool'ların otomatik alınması açık kalır.

Genel Türkçe anlama, tüm çelişkilerin semantik çözümü, çok büyük corpus/uzun süreli yük ve farklı cihazlarda davranış bu sonuçlardan çıkarılamaz. [Bilinen sınırlar](../KNOWN_LIMITATIONS.md) geçerlidir.

## Kanıtlar ve yeniden çalıştırma

- [96 test JUnit](completion-20261026/tests.xml), [konsol](completion-20261026/pytest.log), [kabul](completion-20261026/supplemental.json), [kalite](completion-20261026/quality.json).
- [Eski tanı kümesinin yeni sonucu](completion-20261026/functional.json), [ek sorular ve gerçek modelle öğrenme](completion-20261026/new-quality.json).
- [Son 10.000 kayıt ölçümü](completion-20261026/final/scale-10000.json). Önceki ara ölçüm `completion-20261026/scale-10000.json` içinde korunur; tokenizer kopyası kaldırılmadan önce alınmıştır.
- [Gerçek MCP bağlantısı ve DB metadata](completion-20261026/live-connection.json), [son canlı runtime](completion-20261026/live-after.json), [wheel kurulumu](wheel-check.json).

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp/completion-repeat
.\.venv\Scripts\python.exe scripts/completion_evaluation.py quality --output reports/completion-repeat
.\.venv\Scripts\python.exe scripts/completion_evaluation.py scale --size 10000 --output reports/completion-repeat
.\.venv\Scripts\python.exe scripts/live_connection_check.py
```

HTTP/MCP testleri loopback erişimi gerektirir. Bu turda arayüz tıklaması yapılmadı.

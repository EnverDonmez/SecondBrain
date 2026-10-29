# Second Brain OS — testlerden sonra yapılan düzeltmeler

26 Ekim 2026. [Önceki test raporu](GOAL_TEST_REPORT_2026-10-26.md) düzeltme öncesinin tarihsel kaydıdır.

**Sonuç:** Dört başarısız kabul koşulu kapandı; kabul kontrolleri artık **15/15**. Uygulama testleri 64'ten **88'e** çıktı ve hepsi geçti. Yerel servis yeni kodla yeniden başlatıldı. Sağlık, yeni API sözleşmeleri ve SQLite bütünlüğü doğrulandı; kişisel veritabanına test kaydı veya bağlantı token'ı eklenmedi.

## Düzeltilen davranışlar

| Alan | Yeni davranış |
|---|---|
| Proje/görev bağlamı | Yetki varsa genel kullanıcı kuralları ve tercihler ekleniyor. Proje kuralları konulu sorguda da korunuyor. Yalnız proje yetkili okuyucuya global veri açılmıyor. |
| Bağlam bütçesi | Kurallar öncelikli. `policy_context_complete=false` ve uyarı eksik kuralı bildiriyor. Metadata ve boyut tahmini bütçeye dahil. |
| Bağımsız tercihler | Dil, uzunluk, format, tema ve kod dili ayrı alanlar. Kısa yanıt ile koyu tema birlikte aktif olabiliyor; kısa ve uzun yanıt gibi gerçek çelişkiler hâlâ `disputed` kalıyor. |
| Türkçe çıkarım | Bazı doğrudan talepler kaynaklı inceleme adayı oluyor. Capture/hook/App Server ve ChatGPT import kullanıcı mesajlarında aynı sınırlı çıkarımı kullanıyor. Adaylar otomatik etkinleşmiyor. |
| Tool keşfi/export | Etkin global tool metadata'sı yetkili modelin capability listesinde ve bütçe elverirse bağlamında. Devre dışı tanımlar ve credential ortam adları modelden gizli. Canonical JSON/JSONL artık `tool_configs` içeriyor. |
| Skill yardımcı dosyaları | `brain.get_skill_file(id, path)` ile en fazla 64 KiB UTF-8 paket dosyası okunuyor. Yol, clearance ve etkinlik sınırları korunuyor. Script çalıştırılmıyor. |
| İndeksleme | Tokenizer her kayıtta yeniden oluşturulmuyor; sınırlı cache ile tekrar kullanılıyor. Kayıtlar 64 chunk sınırında gruplanıyor; inference batch boyutu 16. İptal kontrolleri ve silinen kaydı geri yazmama davranışı korunuyor. |

## Ölçülmüş sonuçlar

| Ölçüm | Önce | Sonra |
|---|---:|---:|
| Tam uygulama testleri | 64 geçti | **88 geçti**, 0 hata, 0 atlama; 16,71 saniye |
| Hedef kabul koşulları | 11/15 | **15/15** |
| Aynı tanı kümesindeki 8 doğrudan Türkçe cümleden aday çıkarımı | 0/8 | **8/8** |
| Kısa yanıt + koyu tema | active / disputed | **active / active** |
| 1.000 gerçek semantik kayıt indeksleme | 441,94 saniye | **12,59 saniye**, yaklaşık **35 kat hızlanma** |
| İndeks sonrası süreç working set | 933,3 MB | **942,3 MB** |
| Vector arama p95, 1.000 kayıt / 10 sorgu | 135,72 ms | 141,53 ms |
| Hybrid arama p95, 1.000 kayıt / 10 sorgu | 172,26 ms | 171,63 ms |

İndeksleme hızlandı; RAM azalması veya sorgu hızı artışı bu ölçümde gösterilmedi. Aynı yerel makine ve aynı sentetik veri üreten betik kullanıldı; çoklu tekrar/istatistiksel güven aralığı yok. RAM anlık working set, tepe değer değil. Arama deneyinde 10 sorgu var; 50.000 gerçek semantik kayıt ve eşzamanlı yük ölçülmedi.

8/8 çıkarım, desteklenen kalıpların bu tanı kümesindeki sonucudur; genel Türkçe anlama başarısı değildir. Sorular, alıntılar, koşullu örnekler ve olumsuz ifadelerin pozitif tercihe çevrilmemesi için regresyonlar eklendi. Onay sınırı korunuyor.

## Kanıtlar

- [88 testin JUnit çıktısı](goal-fixes-20261026/tests.xml), [konsol kaydı](goal-fixes-pytest.log).
- [15 kabul kontrolü](goal-fixes-20261026/supplemental.json), [Türkçe çıkarım/bağlam deneyi](goal-fixes-20261026/functional.json).
- [Yeni semantik ölçüm](goal-fixes-20261026/semantic-scale.json), [eski semantik ölçüm](goal-audit-20261026/final/semantic-scale.json).
- [Kalite kontrolleri](goal-fixes-20261026/quality.json): Ruff, format, mypy, iki JS syntax kontrolü ve secret taraması 6/6 başarılı. Mypy strict değil. Tek pytest uyarısı bilinen Qdrant local payload-index uyarısı.
- [Çalışan uygulama](goal-fixes-20261026/live-check.json): HTTP sağlıklı, yeni bağlam/tool sözleşmeleri yüklü, SQLite `ok`, kullanıcı kayıt sayıları değişmedi.
- [Ayrı dizine kurulan wheel testi](wheel-check.json): yeni modül, statik dosyalar, migration ve bütünlük doğrulandı. Wheel ve kaynak arşivi güncellendi.

## Açık kalan işler

1. **Kişisel AI bağlantısı etkin değil.** Canlı veritabanı hâlâ boş. Kısıtlı token, kullanılacak istemcinin yapılandırması ve host güven onayı ayrı kurulum işi.
2. **Genel semantik öğrenme çözülmedi.** Aynı dersin farklı cümleleri otomatik birleşmiyor. Doğal Türkçe retrieval için daha geniş bağımsız veri gerekiyor; önceki 24 sorguluk kümedeki semantik başarısızlıklar kapanmış sayılmıyor.
3. **RAM ve büyük ölçek arama açık.** BM25 corpus'u yeniden kuruyor, vektörler doğrusal taranıyor. Bu turdaki hız kazanımı indekslemededir; kalıcı ANN veya genel corpus cache eklenmedi.
4. **Genel skill yürütme/verifier yok.** Dosya erişimi tamamlandı; güvenilmeyen kod otomatik çalıştırılmıyor.
5. **Eski generic tercihler topluca dönüştürülmedi.** Yeni çıkarımlar ayrı alanları kullanır; mevcut kişisel kayıtlar sessizce yeniden yazılmaz. Şema sürümü 3 kaldı.

## Yeniden doğrulama

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp/goal-fixes-repeat --junitxml=reports/goal-fixes-repeat.xml
.\.venv\Scripts\python.exe scripts/goal_audit.py functional --output-dir reports/goal-fixes-repeat
.\.venv\Scripts\python.exe scripts/goal_audit_completion.py supplemental --output-dir reports/goal-fixes-repeat
.\.venv\Scripts\python.exe scripts/goal_audit_completion.py semantic-scale --output-dir reports/goal-fixes-repeat
.\.venv\Scripts\python.exe scripts/goal_audit_completion.py quality --output-dir reports/goal-fixes-repeat
```

Eski kanıtlar korunur; yeni çıktı dizini seçilebilir. Gerçek HTTP/MCP testleri yerel socket erişimi gerektirir. Bu turda yeni tarayıcı tıklama testi yapılmadı; HTTP capture → aday → onay → recall ve gerçek SDK MCP dosya/tool çağrıları test edildi.

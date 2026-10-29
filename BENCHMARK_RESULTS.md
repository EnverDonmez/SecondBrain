# Ölçülmüş değerlendirme sonuçları

Tarih: **26 Ekim 2026**. Kaynaklar: `reports/evaluation/result-all.json`, `reports/performance/performance.json`, `reports/tests.xml`. Raporlar kod tarafından üretilir; hazır başarı çıktısı değildir.

## SecondBrain-TR-Eval 0.1.0-synthetic

500 soru: 100 fact, 100 preference, 100 temporal, 50 correction, 50 unknown, 50 injection, 50 privacy. Deterministik split: 300 development / 100 validation / 100 test. Dataset hash'i raporda bulunur. Test bölümü query düzeltmesi validation üzerinde yapıldıktan sonra tüm-suite doğrulamasında çalıştırıldı.

**Bu test kolaylaştırıcı subject kimlikleri kullanır.** Şablon tabanlı sentetik regression ölçümüdür; bağımsız curated benchmark, doğal Türkçe konuşma cevabı veya LLM factual accuracy ölçümü değildir. Retrieval correctness ile final answer correctness aynı metrik değildir.

| Motor | Kaynaklı retrieval@1 | Recall@5 | MRR@10 | Temporal | Abstention | Privacy kontrol hatası | p95 / 500 soruluk corpus |
|---|---:|---:|---:|---:|---:|---:|---:|
| FTS5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 2.534 ms |
| rank-bm25 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 9.810 ms |
| Hybrid | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 12.829 ms |

Citation precision@1 ve correction success bu sentetik kümede 1.00. Injection adaylarının 50/50'si terfi ettirilemedi. Harici API ücreti $0. Başlangıç validation raporu `initial-validation-before-query-fix.json` içinde tutuldu: ortak sayı parçalarına OR eşleşmesi nedeniyle abstention başarısızdı. O rapordaki `privacy_leaks` alanı tüm ilgisiz sonuçları da hata sayıyordu; gerçek yetkisiz scope içeriği görüldüğü şeklinde yorumlanmamalıdır. Son sürümde exact permission filtreleri ve daha sıkı lexical coverage ile bu regresyon kapandı.

## 10.000 olay / 10.000 assertion performansı

Windows, CPU, her motor için 30 sorgu; network/model çağrısı yok. SQLite dosyası yaklaşık 12.15 MB. Bunlar warm local sentetik corpus ölçümleridir; eşzamanlı kullanıcı veya büyük multimodal workload değildir.

| Motor | p50 | p95 | ≤2 saniye hedefi |
|---|---:|---:|---|
| FTS5 | 3.130 ms | 3.687 ms | geçti |
| BM25 | 209.738 ms | 216.504 ms | geçti |
| Hybrid | 280.022 ms | 390.127 ms | geçti |

Yerel embedding ve Mem0 için gerçek integration smoke testi geçti; aynı 500 soruluk tam semantic/memory-engine benchmark çalıştırılmadı. Semantic kalite kazancı, skill task success, final LLM answer accuracy, model değiştirme davranışı, gerçek API faturası ve donanımlar arası RAM/CPU karşılaştırması **ölçülmedi**. Bu metrikler sıfır veya başarılı olarak doldurulmadı.

FTS5 varsayılan kalır: bu suite daha karmaşık motorun ≥5 yüzde puan kazancını göstermez. Gerçek Türkçe paraphrase, yazım hatası, uzun konuşma ve çok sıçramalı sorularla bağımsız eval gerekir.

# Hafıza ve arama motorları

`MemoryEngine` arayüzü health, capabilities, initialize, ingest, retrieve, invalidate, delete, reindex ve recover işlemlerini tanımlar. Yeni motor kanonik kayıtları sahiplenmez; sonuç ID'leri kanonik erişim/validity filtresinden geçmelidir.

| Motor | Gerçek durum | Rol / sınır |
|---|---|---|
| SQLite 3.53.1 / FTS5 | verified | Varsayılan BM25 lexical; model gerektirmez |
| rank-bm25 0.2.2 | verified | Aynı kanonik veri üzerinde bağımsız BM25 |
| Yerel ilişki görünümü + RRF | verified | Lexical ve subject/predicate adaylarını birleştirir; Graphiti değildir |
| FastEmbed 0.9.1 / multilingual MiniLM | verified | Gerçek ONNX CPU embedding/cosine; 96 token parça, 80 token stride, kaynak karakter aralığı |
| Mem0 2.2.1 / Qdrant local | experimental, locally tested | Gerçek ingest/search/delete; LLM inference kapalı, disposable RAM projection |
| Graphiti | blocked | Graph backend ve yapılandırılmış LLM yok; gerçek integration testi yapılmadı |
| Hindsight | unsupported in runtime | Ek servis yaşam döngüsü ve model bütçesi doğrulanmadı |
| Supermemory | unsupported in runtime | SDK/repo lisansı ayrı binary'yi kapsıyor kabul edilmedi |
| MemOS | research only | Belirli auth advisory'sinin fixed release'i burada doğrulanmadı |

Mem0 adaptörü onaylı assertion metnini `infer=False` ile kaydeder. Bu test Mem0'nun LLM extraction/reflection kalitesini ölçmez. Gerçek yerel FastEmbed provider ve Qdrant kullanılır; sahte embedding yoktur. Fail-closed `NoInference` guard'ı yanlışlıkla ücretli/harici model çağrısını engeller. Ek sparse BM25 modelinin runtime'da gizlice indirilmemesi için Mem0 sparse encoder kapatılmıştır; Mem0 projection dense semantic arama yapar, lexical karşılaştırmayı ayrı rank-bm25 motoru sağlar. Test sırasında socket bağlantıları engellendi ve girişim olmadığı doğrulandı. Upstream provider factory eşlemesi yalnız kurulum sırasında değiştirilir; kullanılan sürüm sabittir. Bu seam gelecekteki Mem0 sürümlerinde uyumluluk testi gerektirir.

Mem0/Qdrant RAM projection'u snapshot'a kopyalanmaz, tekrar kurulabilir. Silme sırasında çalışma anındaki Mem0 kayıtları da kaldırılır. Qdrant local payload index uyarısı beklenen bir sınırlamadır; gerçek server performansı test edilmedi. Mem0'nun retrieval sonucu tek başına kimlik, ACL veya temporal otorite taşımaz; kanonik filtre yeniden uygulanır.

Onaylama transaction'ı aynı transaction içinde `vector_memory` işi oluşturur; model kuruluysa worker tüm metni örtüşen parçalara böler. 128 token model penceresi için subject/predicate prefix'i 20 token, değer parçası 96 token ile sınırlandırılır. Canonical değer kısaltılmaz. Yerel vector ve Mem0 sonuçları en iyi parçayı kanonik ID altında birleştirir, eşleşen karakter aralığını verir. Context bu kaynaklı alıntıyı kullanır. Uzun belgenin sonundaki Türkçe soru-cevap hem native vector hem gerçek Mem0 üzerinde test edildi. Mem0 search izinli canonical ID listesiyle filtrelenir ve sonuçta tekrar yetki denetimi uygulanır.

Default motor seçimi FTS5'tir. Kolay sentetik regresyonda karmaşık motorlar en az 5 puan ek doğruluk göstermedi; bu nedenle varsayılan yapılmadılar. Gerçek doğal dil ve çok sıçramalı graph testleri için ayrı curated veri gerekir.

26 Ekim devamında hybrid akışına küçük ve denetlenebilir Türkçe/İngilizce kavram sözlüğü ve yaygın ekler için önek eşleştirme eklendi; orijinal FTS/BM25 anlamı değiştirilmedi. Bu sözlük genel Türkçe dil modeli değildir. BM25 ve sözlük corpus'u sınırlı cache kullanır. Vektör cosine hesabı float32 matrislerle yapılır; 32 MiB üstü 512 kayıtlık gruplarda taranır. Arama hâlâ doğrusal maliyetlidir, ANN yoktur. Model ve tokenizer ayrı offline süreçtedir; 30 saniye boşta kapanır. Güncel ölçümler ve soğuk başlangıç sınırı [devam raporunda](reports/COMPLETION_2026-10-26.md).

Graphiti'nin [resmi advisory'si](https://github.com/getzep/graphiti/security/advisories/GHSA-gg5m-55jj-8m5g) belirli node-label filtrelerine yönelik güvenlik sınırını belgeler. Bu çalışmada Graphiti dependency kurulmadı; yalnız README/release/LICENSE snapshot'ı araştırma kanıtıdır.

# Gereksinim öz denetimi

Durum anlamları: **verified** yerelde ilgili test çalıştı; **working** uygulama yolu var, tüm edge case'ler doğrulanmış sayılmaz; **experimental** kapsamı sınırlı çalışan yol; **blocked** dış runtime/hesap/izin gerekiyor; **unsupported** bu sürümde uygulanmadı. Tam vizyonun bütünü verified değildir.

## 22 görev bölümü

| İstek | Gerçekleşme ve modül | Test / kanıt | Sınır / dış bileşen |
|---|---|---|---|
| 1. Kaynak ve doğrulama | verified araştırma okuma, 40 upstream snapshot, paket release hash'leri | source-registry.json, package-release-hashes.json | Derin code/security review bütün adaylara yapılmadı |
| 2. Bağımsız beyin | working canonical events/assertions/skills | HTTP + MCP + export testleri | Gerçek kişisel corpus kullanılmadı |
| 3. Modüler C+B mimari | working 20 bileşenin modüler karşılığı | ARCHITECTURE, typed API, contract testleri | Dağıtık servis ölçeği testli değil |
| 4. OSS sentez | verified FTS/rank-bm25/FastEmbed/Mem0/MCP | gerçek CPU ve Mem0 integration testi | Diğer adaylar research/blocked; taklit adapter yok |
| 5. Kanonik arşiv | verified events/vault/registry/export | bytes/hash/idempotency/branch testleri | JSON export binary içermez; backup tam içerir |
| 6. Zamansal hafıza | verified memory.py | late knowledge, three decisions, bounded correction | Graphiti yok; öz temporal engine |
| 7. Öğrenme | working feedback→LESSON adayı→approval | üç farklı evidence testi | Üretken reflection/skill synthesis yok |
| 8. Arama/bağlam | verified FTS/BM25/local vector/RRF/context | retrieval ve budget testleri | Semantic full eval ve neural reranker yok |
| 9. AI istemcileri | verified MCP protocol, hook/item normalization, gerçek Codex initialize; explicit-thread kolektör var | SDK subprocess, host fixtures, codex-handshake.json | Canlı host kurulumu ve kullanıcı thread history/watch testi eksik |
| 10. Skill/tool taşınabilirliği | working registry/version/state/export/compatibility | skill ZIP round-trip, missing capability, inventory testleri | Otomatik arbitrary install/execute yok |
| 11. Multimodal | verified text/PDF/DOCX, gerçek image/scanned-PDF OCR, tiny ASR, video frame OCR ve sidecar | test_media_pipeline.py, media-evaluation.json | Küçük sentetik İngilizce ses testli; genel vision ve Türkçe gerçek ses kalite ölçümü yok |
| 12. Web dashboard | working 16 alan + tema/locale altyapısı | CUA create/review/approve ve sayfa gözlemleri | Tam EN ve tüm e2e kombinasyonları testli değil |
| 13. Güvenlik/sahiplik | verified temel ACL/CSRF/trust/quarantine/delete | security+restore+namespace testleri | SaaS red-team, full DB encryption yok |
| 14. Teknik kurulum | verified Windows venv/CLI/API | yerel servis liveness ve browser | Docker/Linux/macOS çalıştırılmadı |
| 15. Dayanıklılık | working persistent jobs/lease/retry/checkpoint/rebuild/migrations | retry/dead-letter/concurrency/reindex/upgrade | Dağıtık sync ve her crash noktası yok |
| 16. Benchmark | verified 500/10k sentetik harness | gerçek JSON raporları | Curated/LLM judge/skillsbench reprodüksiyonu yok |
| 17. Maliyet | working local usage ledger, deterministic zero-API core | recorded $0 external API; timing reports | Bulut bütçe/provider uygulaması etkin değil |
| 18. Kalite | verified unit/integration/API/MCP/property/security/restore | JUnit, Ruff, mypy, syntax | CI dosyası var, remote CI koşmadı |
| 19. Belgeler | working istenen referanslar + ADR + audit | dosya envanteri | Gelecek runtime versiyonları ayrı doğrulanmalı |
| 20. Özerk geliştirme | gerçek kod, paket kurulumu, test ve düzeltme | kaynak ağacı ve raporlar | Ücretli servis / kişisel veri paylaşımı yapılmadı |
| 21. Tamamlanma | kısmi vizyon, kullanılabilir uygulama | aşağıdaki 8 senaryo | Gerçek dış hesaplar ve bütün motorlar tamamlanmadı |
| 22. Öz denetim | bu dosya ve gerçek sonuç raporları | TESTING / BENCHMARK_RESULTS | Yapılmayan testler başarı diye gösterilmedi |

## İstenen 20 temel bileşenin karşılığı

1–5: `core.py`, `events.py`/`vault.py`, `memory.py`, `entities.py`, bitemporal assertion sürümleri. 6–8: `importers.extract_explicit`, opsiyonel `OllamaProvider`, `learning.py`, conflict/approval gate. 9–11: `retrieval.py` query plan/filter/rank/context. 12–13: `api.py`, `mcp_server.py`, `capture.py`, client config generator. 14–15: `skills.py`, `tools.py`, `multimodal.py`. 16–18: `security.py`, `privacy.py`, `queue.py`, migrations, `backup.py`. 19–20: `benchmark.py`, `tests/`, `static/` dashboard. Modül dosyasının bulunması tüm vizyonun o başlıkta tamamlandığı anlamına gelmez; üst tablodaki sınırlar geçerlidir.

## Sekiz uçtan uca senaryo

| Senaryo | Çalıştırılan yol | Sonuç |
|---|---|---|
| 1. Kişisel tercih | sentetik user event→proposal→approve→HTTP/MCP recall | verified; gerçek model cevabı değil |
| 2. Kullanıcı düzeltmesi | feedback×3→candidate lesson→owner approval→recall | verified; özgür metin semantik birleştirme yok |
| 3. Proje geçmişi | PostgreSQL→SQLite→PostgreSQL, valid/known soruları | verified canonical engine; Graphiti yok |
| 4. Model değiştirme | aynı MCP verisi iki sentetik client çağrısında tutarlı | protocol verified; iki canlı model hesabı kullanılmadı |
| 5. Skill aktarımı | aynı ZIP export, compatibility gereksinim karşılaştırması | verified package; gerçek farklı host yürütmesi yok |
| 6. Unutma | preview→hard forget→eski backup restore→replay→re-import reject | verified yönetilen lineage; dış kopyalar kapsam dışı |
| 7. Kötü niyetli kaynak | document→POLICY/USER_PREFERENCE ve secret/injection terfi denemeleri | verified gate; her saldırı biçimi kapsanmaz |
| 8. Beynimi tara | scope+clearance+validity+budget içinde kaynaklı context | verified; skills capability execution ayrı |

## Kullanıcı müdahalesi gereken son bağlantılar

Owner anahtarıyla yerel dashboard'a giriş; kapsamlı model token'ı üretme; host config örneğini mevcut ayarlara birleştirme; Codex/diğer host'ta hook trust; varsa yerel Ollama modeli seçme. Uzak ChatGPT MCP için hesap uygunluğu, OAuth ve güvenli yayınlama ayrıca gerekir. Bunlar bu oturumda otomatik gerçekleşmiş sayılmadı.

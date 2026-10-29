# HTTP API

Yerel servis: `http://127.0.0.1:8765`. Canlı OpenAPI: `/api/openapi.json`; tamamen yerel şema görüntüleyicisi `/api/docs`. Dokümantasyon arayüzü CDN veya dış JavaScript yüklemez.

Kimlik doğrulama `Authorization: Bearer <token>` veya sahip oturum cookie'siyle yapılır. Cookie ile değişiklik istekleri `X-Brain-Request: 1` gerektirir. Başka origin'den POST reddedilir. Model token'larına approve/delete/admin verilemez.

| Yol | İşlem |
|---|---|
| `GET /healthz` | Hassas bilgi içermeyen liveness |
| `POST /api/login`, `/api/logout` | Sahip oturumu |
| `GET /api/status`, `/api/diagnostics` | Sağlık ve kaynak durumu; ayrıntılar owner |
| `POST /api/events`, `GET /api/events/{id}` | Capture ve orijinal kaynak |
| `POST /api/memories`, `GET /api/memories/{id}` | Aday ve assertion ayrıntısı |
| `POST /api/memories/{id}/approve|reject|hide` | İnceleme / erişimden kaldırma |
| `POST /api/search` | Tip, subject, predicate, scope, source, valid_at, known_at, engine, limit, offset |
| `POST /api/action/brain.{operation}` | MCP ile ortak domain işlemleri |
| `POST /api/import` | Multipart file, scope, sensitivity; kalıcı job döndürür |
| `GET /api/assets/{id}` | Yetkili orijinal binary indirme |
| `GET /api/media/capabilities` | Gerçek işlemci durumu |
| `POST /api/assets/{id}/derivative`, `POST /api/assets/{id}/ocr` | Kaynağa bağlı türev / yerel OCR |
| `POST /api/assets/{id}/process` | `operation`: ocr, pdf_ocr, transcribe veya video; opsiyonel `language`; kalıcı işlem işi |
| `POST /api/jobs/{id}/cancel` | Bekleyen/çalışan işi kontrol noktalarında iptal et; mevcut adayları koru |
| `POST /api/jobs/{id}/retry` | Dead-letter/pending işi yeniden deneme |
| `POST /api/capture/{client}` | Resmi hook payload'ı normalizasyonu |
| `POST /api/codex/items/{thread_id}` | App Server item ingestion |
| `GET /api/capture-coverage` | Hook ve App Server item örtüşmesi |
| `POST /api/entities/merge` | Alias eşleme; tarihsel assertion değiştirilmez |
| `GET /api/feedback`, `POST .../brain.record_feedback` | Öğrenme kanıtları |
| `POST /api/skills/import`, `/api/skills/{id}/state|compatibility` | Skill lifecycle |
| `GET /api/skills/{id}/export` | Orijinal skill paketi |
| `GET|POST /api/tools`, `POST /api/tools/{id}/state|probe` | Deklaratif araç envanteri |
| `GET /api/export/json|jsonl|markdown` | Taşınabilir kanonik metadata ve içerik |
| `GET|POST /api/backups`, `POST /api/backups/import` | Şifreli snapshot yönetimi |
| `POST /api/backups/{id}/verify|restore`, `GET .../download` | Bütünlük ve kurtarma |
| `POST|GET /api/tokens`, `DELETE /api/tokens/{id}` | Sınırlı model anahtarları |
| `GET /api/audit`, `POST /api/reindex` | Denetim / projection yeniden kurma |
| `GET|POST /api/benchmarks` | Sentetik değerlendirme |

Capture, hook ve App Server ingestion yolları, kullanıcı kaynaklı tanınan doğrudan tercihler için `read` + `propose` yetkisi varsa inceleme adayı oluşturur. `candidates` ve `approval_required` yanıt alanları etkinleştirme anlamına gelmez. ChatGPT import da aynı sınırlı çıkarımı kullanıcı mesajlarına uygular; asistan/belge metinleri kullanıcı tercihine terfi ettirilmez. `Tercihim:` / `Kuralım:` yanında dil, uzunluk, tema ve bazı çalışma kuralları için dar Türkçe kalıplar desteklenir; genel dil anlama iddiası yoktur.

JSON/JSONL canonical export `tool_configs` tablosunu da içerir. Bu owner-only export credential değerlerini saklayan bir kasa değildir; orijinal skill ZIP/binary içerikleri için paket export'u veya şifreli tam yedek kullanılır. `brain.get_skill_file` ortak action üzerinden paket içi UTF-8 dosya okur; `brain.list_capabilities` etkin tool metadata'sını gösterir.

## Arama örneği

```json
{"query":"veritabanı", "scope":"Second Brain", "valid_at":"2026-07-01", "known_at":"2026-10-26", "engine":"fts", "limit":20, "offset":0}
```

Zamanlar UTC'ye normalize edilir. Tarih verilmezse güncel valid/known time kullanılır. ISO tarihi için timezone verilmezse UTC kabul edilir; dashboard yerel saat seçimini UTC'ye çevirir. Limit 1–100, sayfalama offset ile yapılır. Hatalar 403 (izin), 404 (yok) ve 422 (sözleşme) olarak ayrılır.

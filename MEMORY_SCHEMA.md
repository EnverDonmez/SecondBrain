# Kanonik hafıza şeması

Kamuya açık envelope sürümü 1'dir; SQLite migration sürümü bundan bağımsızdır ve artık **7**'dir. `001`–`007` migration'ları sırayla atomik uygulanır. Şema 4 projeksiyon revizyonunu, 5 graf ilişkilerini, 6 kaynak/başlık dizinini, 7 tutarlı özellik anahtarlarını ve koşullu bağlam sayaçlarını ekler. Bilinmeyen daha yeni veritabanı sürümü açılmaz.

Şema 7'de `subject_key/predicate_key` türetilmiş arama/özellik kimliğidir; ham alanlar korunur. `identity_aliases` sahibin açık varlık birleştirmeleridir. `statement_receipts` birebir tekrar edilen beyanların yeni kaynaklarını aynı assertion'a bağlar; kaynak olayı da korunur. `context_clock` tenant/scope/hassasiyet/tür bazında bağlam geçersizleştirmesi içindir. Export alias ve kanıt ilişkilerini içerir; şifreli backup tüm tabloları korur. [ADR 0006](docs/adr/0006-coherent-memory.md).

## Orijinal olay

`id`, `tenant`, `source`, `source_id`, `event_type`, `actor`, `session_id`, `conversation_id`, `parent_id`, `occurred_at`, `ingested_at`, `scope`, `sensitivity`, `text`, `payload`, `metadata`, `attachments`, `content_hash`, `schema_version`.

Olay payload'ı sessizce güncellenmez. Aynı kaynak kimliği farklı payload ile gelirse yeni olay olur. Hash, normalleştirilmiş envelope'un deterministik JSON SHA-256 değeridir; asset kimlikleri hash'e dahil edilmez. `event_assets` ilişki tablosu aynı kaynak olayının farklı export dosyalarında bulunmasını kayıpsız eşler. Bu ilişki bir önceki olay payload'ını değiştirmez.

Orijinal ZIP/PDF/dosya bytes'ları ayrı AES-GCM asset'idir. ChatGPT export'ta olmayan attachment bytes'ları oluşturulmaz; payload'daki pointer korunur. Boş/create_time bulunmayan mesajların kaynak zamanı bilinmiyor olabilir; ingestion zamanı kaynakta mevcutmuş gibi yorumlanmamalıdır.

## Assertion

Türler: `USER_ASSERTED_FACT`, `USER_PREFERENCE`, `OBSERVED_EVENT`, `MODEL_INFERENCE`, `PROJECT_STATE`, `DECISION`, `CORRECTION`, `LESSON`, `PROCEDURE`, `SKILL`, `POLICY`, `EXTERNAL_KNOWLEDGE`.

Kimlik: `id` sürüm kimliği, `logical_id` sürüm ailesi, `version` artan numara. İçerik: `subject`, `predicate`, `value`, `scope`. Kaynak: `source_event_ids`, `supersedes`, `trust`, `confidence`, `risks`, `approved_by`. Zaman: `valid_from/to`, `known_from/to`, `created_at`. Yönetim: `status`, `sensitivity`, `importance`, `tenant`.

Valid ve known aralıkları `[from,to)` biçimindedir; `NULL to` açık uçtur. Correction eski transaction sürümünü kapatır, korunması gereken eski valid aralıklarını yeni transaction sürümleri olarak taşır ve yeni assertion ekler. Kaynak zamanı kaynak olayındadır. Geçmiş known-time sorgusu correction öncesindeki yanlış fakat o tarihte bilinen assertion'ı görebilir.

## Durumlar ve otorite

`RememberFact.assertion` taşıma alanıdır: `candidate` veya `direct_user`; yeni SQL migration gerektirmez. Otomatik kabulde `approved_by` değeri `direct-user:<istemci>` ve audit eylemi `memory.user_statement_accepted` olur. Türetilen `acceptance` alanı direct_user/owner_review/pending_review ayrımını döndürür. Manuel approve hâlâ sahibindir; sıradan açık beyanlar [ADR 0005](docs/adr/0005-direct-user-statements.md) kapsamındadır.

`candidate → active`, `candidate → rejected`, çelişkide `disputed`. Soft hide mevcut transaction görünümünü kapatır; geçmiş kalır. Kalıcı forget fiziksel kayıt/türev temizliği ve tombstone üretir. `confidence=1` dış belgeyi kullanıcı beyanına dönüştürmez. Hassasiyet kaynağın altına düşürülemez; kaynak ile assertion aynı scope'ta olmalıdır.

## Export

JSON: olaylar, hafızalar, asset metadata'sı, skill paket metadata'sı, feedback, tombstone, checkpoint ve event-asset ilişkileri. JSONL tablo/kayıt envelope'u taşır. Markdown insan incelemesi içindir; keyfi talimat gibi yürütülmemesi için içerik girintili yazılır. Binary dosyalar JSON'a base64 olarak doldurulmaz; tam binary round-trip için şifreli backup kullanılır. JSON/Markdown import güvenli aday üretimidir, doğrudan güvenilir canonical restore değildir.

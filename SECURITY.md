# Güvenlik modeli

## Sınır

Yerel tek kullanıcı servisi. Düşmanca çok kiracılı SaaS veya internete açık production gateway olarak denetlenmedi. Loopback üzerinde dahi rastgele yerel süreçlerden gelen istekler bearer token olmadan özel veri alamaz. Host allowlist, origin kontrolü, SameSite/HttpOnly cookie, CSRF header, CSP ve login rate limit uygulanır. Token hash'leri SQLite'ta; owner anahtarı yerel dosyada tutulur.

Model token'ı yalnız read/propose/capture alabilir. Scope allowlist ve sensitivity clearance tüm kanonik retrieval yollarına uygulanır. Graph ve Mem0 sonuçları da kanonik filtreyi kullanır. Aynı tenant içindeki kapsamlar otomatik genişletilmez; farklı tenant kayıtları ortak sorguya girmez. Tek owner'ın tüm yönetim yetkisine sahip olması SaaS tenant provisioning desteği anlamına gelmez.

28 Ekim 2026: kullanıcı, sıradan açık beyanlarının ikinci onay olmadan kaydedilip güncellenmesini istedi. `direct_user` dar kabul yolu yalnız uygun tür, birebir kaynak cümleciği ve tek uygun sürüm şartıyla çalışır. Genel approve/delete/admin izinleri değişmez. Soru/varsayım ve kaynak guard'ları bağımsız yazar/niyet ispatı değildir; istemci kullanıcı diye yanlış etiketlerse genel olarak tespit edilemez. Bu yol güvenilir bağlı istemci varsayımını taşır. POLICY/skill/prosedür ve diğer belirsiz adaylar manuel incelemede kalır. [Sözleşme ve sınırlar](docs/adr/0005-direct-user-statements.md).

## Tehditler ve kontroller

| Tehdit | Kontrol / kalan sınır |
|---|---|
| Memory poisoning / prompt injection | Kaynak otoritesi ayrımı, aday karantina, owner onayı, harici içerikten user-policy terfisine ret |
| Secret exposure | Şüpheli sırlar active memory/embedding'e alınmaz; orijinal kaynak arşivinde bulunabilir |
| Unauthorized write / privilege escalation | Ayrı propose/approve/delete/admin; model kendini onaylayamaz |
| Namespace leakage | SQL before-ranking filtreleri, graph/vector canonical recheck; sentetik izolasyon testleri |
| Replay | Deterministik source envelope hash'i, kalıcı job dedup ve tombstone hash'leri |
| Path traversal / archive bomb | ZIP mutlak/üst dizin/drive/symlink kontrolü; entry/count/expanded byte/ratio sınırları |
| SSRF | Keyfi uzak provider URL'si yok; localhost provider; ortam proxy'si kapalı |
| Malicious skill | Paket kodu otomatik çalıştırılmaz; execution_verified iddiası verilmez |
| Tool output manipulation | Tool/document kaynakları user assertion'dan farklı trust taşır |
| Backup tampering | Scrypt + AES-256-GCM; SQLite/asset bütünlüğü ve silme replay |

Regex taraması kapsamlı bir injection/secret sınıflandırıcısı değildir. Koruma regex'e dayanmaz; açık onay ve kaynak otoritesi sınırı ana mekanizmadır. Kullanıcı bilerek zararlı bir paketi başka bir terminalde çalıştırırsa bu uygulama onun sürecini sandbox'lamaz.

## Şifreleme

Raw assets: AES-256-GCM, 96-bit rastgele nonce, asset ID associated data. Master key `data/master.key` içinde; Unix mod 0600 istenir, Windows üzerinde NTFS parent ACL'leri devrededir. DPAPI/HSM/SQLCipher entegrasyonu yoktur. **SQLite content, FTS ve vector sayıları plaintext'tir.** Yedekler ayrı kullanıcı parolasından Scrypt N=32768,r=8,p=1 ile türetilmiş anahtarla şifrelenir; parola saklanmaz.

## Kaynak ve güvenlik denetimi

Kurulu paket sürümleri `requirements.lock`, lisans dosyaları `third_party/licenses/`, upstream snapshot'lar ve tam SHA'lar `reports/source-registry.json` içindedir. pip-audit sonucu `reports/dependency-audit.json`dadır. “Bilinen açık bulunmadı” kodun açık içermediği veya saldırı testinin eksiksiz olduğu anlamına gelmez. MemOS, Claude-Mem ve diğer araştırma motorları sırf README güven iddiası nedeniyle runtime'a eklenmedi.

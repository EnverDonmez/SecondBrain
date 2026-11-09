# Güvenlik modeli

## Sınır

Yerel tek kullanıcı servisi. Kimlik doğrulama kısıtlı Bearer anahtarı veya iptal edilebilir tarayıcı oturumu ile yapılır. Tarayıcı çerezinde rastgele bir oturum kimliği, SQLite'ta bu kimliğin hash'i ve son kullanma zamanı durur. Çıkış oturumu iptal eder. Host allowlist, origin kontrolü, SameSite/HttpOnly cookie, CSRF başlığı, CSP, giriş deneme sınırı ve akış sırasında HTTP gövde sınırı uygulanır. Sahip anahtarını servis kapalıyken `python -m second_brain rotate-owner-key` ile yenile.

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

Ham dosyalar AES-256-GCM ile şifrelenir. Her dosyanın rastgele 96 bit nonce'u vardır ve dosya kimliği ilişkilendirilmiş veridir. Windows'ta `data/master.key` geçerli Windows kullanıcısına bağlı DPAPI ile korunur. İlk açılışta eski ham anahtar atomik olarak sarılır. Unix'te anahtar dosyası 0600 izinli oluşturulur. **SQLite içeriği, FTS ve vektör değerleri açık metindir.** Taşınabilir yedekler Scrypt ile türetilen ayrı kullanıcı parolasıyla şifrelenir.

## Kaynak ve güvenlik denetimi

Paket sürümleri `requirements.lock` dosyasındadır. Kurulum, seçilen wheel dosyalarını `requirements.hashes.json` içindeki SHA-256 değerleriyle doğrular. Lisanslar `third_party/licenses/` altında, upstream kaynakların tam SHA'ları `reports/source-registry.json` içindedir. CI, bağımlılık denetimi için `pip-audit` çalıştırır.

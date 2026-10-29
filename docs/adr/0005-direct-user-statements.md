# ADR 0005 — Açık kullanıcı beyanı, ikinci bir onay gerektirmez

Tarih: 28 Ekim 2026. Durum: uygulanmış. Önceki bütün kayıtları manuel onaylatma yaklaşımı sıradan açık kullanıcı beyanları için kaldırıldı.

## Amaç

Kullanıcı doğrudan “Artık 4. sınıfım” dediğinde bu beyan, eski “3. sınıf” bilgisini güncellemek için yeterlidir. Sistem aynı değişikliği yeniden onaylatmaz. Anlamı yorumlayan, konu/özellik seçen ve alıntıyı hazırlayan zaten konuşulan AI'dır; veritabanı yeni bir model çalıştırmaz.

## Sözleşme

`brain.remember` içindeki her kayıt için `assertion` alanı vardır:

- `direct_user`: açık kullanıcı beyanı. `actor=user`; `value`, kaynakta birebir geçen tamamlanmış kısa beyan olmalıdır. `USER_ASSERTED_FACT`, `USER_PREFERENCE`, `PROJECT_STATE`, `DECISION` desteklenir.
- `candidate`: varsayılan; çıkarım, belirsiz bilgi ve diğer adaylar incelemede kalır. Eski istemcilerin onay davranışı değişmez.

Örnek bir kullanıcının varsayımsal paketi; gerçek kaynak/kimliklerle değiştirilmelidir:

```json
{
  "source_text": "Artık 4. sınıfım.",
  "actor": "user",
  "scope": "global",
  "facts": [{
    "assertion": "direct_user",
    "memory_type": "USER_ASSERTED_FACT",
    "subject": "user",
    "predicate": "education.year",
    "value": "Artık 4. sınıfım.",
    "topics": ["Profile/Education"]
  }]
}
```

`subject/predicate/scope` aynı özelliğin mevcut kaydıyla tutarlı seçilir; türü de korunur. Tek uygun güncel kayıt varsa sunucu `supersedes` bağlantısını kendisi kurar. Birden fazla hedef, unresolved disputed alternatif, eski/hedefi şaşmış düzeltme veya gizlilik düşürme varsa otomatik seçim yapmaz. Bilinen güncel hedef için `supersedes` verilebilir. `brain.correct_memory` de `assertion=direct_user` seçeneğini destekler; varsayılanı yine adaydır.

## Aktivasyon ve geçmiş

Genel `approve/delete/admin` yetkileri modele verilmez. Sunucu dar kapsamlı kabul yolunda kaynak, tür, izin, kapsam, hassasiyet ve sürüm şartlarını doğrular. `approved_by=direct-user:<istemci>` ve `memory.user_statement_accepted` denetim olayı bu işlemi manuel sahip onayından ayırır. Okuma/arama/bağlamda `acceptance=direct_user` görünür.

Sürüm geçişi mevcut atomik valid/known time mekanizmasını kullanır. Eski kaynak/sürüm silinmez; güncel sorgu yeni değeri, geçmiş sorgu o dönemin değerini bulur. Aynı kaynak-beyan tekrarında tarihsel kayıt da aranır; eski bir isteği yeniden göndermek daha yeni değeri geri almaz. `applied[].current=false` tarihsel tekrarın bugünkü değeri değiştirmediğini belirtir. Model, başarı söylemeden önce `applied`, `approval_required` ve `review` sonucunu kontrol etmelidir.

## Sınırlar

Alıntı, soru/varsayım/gelecek/eksik-negasyon kontrolleri ucuz ve ihtiyatlı guard'lardır; genel dil anlama veya bağımsız yazar doğrulaması değildir. Bağlı AI'nın doğru cümleyi ve doğru özelliği seçmesi hâlâ gerekir. İstemci kullanıcı diye yanlış etiketlerse sunucu bunu genel olarak kanıtlayamaz; kaynak alım yolu ve client-reported niteliği korunur. Güvenilir istemci/kısıtlı erişim modeli devam eder.

`POLICY`, `SKILL`, `PROCEDURE`, model çıkarımı ve harici bilgi bu yolla etkinleşmez. Otomatik kabul edilen bir profil/tercih bilgisi platform talimatı, araç kurma izni veya yürütme yetkisi değildir. Secret/injection karantinası, silme tombstone'ları, scope ve clearance sınırları korunur.

Genel alias eşleştirme, serbest metinden tüm çelişkileri çözme, bilinmeyen geçerlilik tarihini tahmin etme veya her host'un araç çağırmasını zorlama yapılmaz. Host'un yeni araç şeması ve talimatları yüklemesi gerekir; eski oturum önbelleği yeni `assertion` alanını göstermeyebilir.

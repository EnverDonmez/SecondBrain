# Açık kullanıcı beyanıyla otomatik hafıza güncellemesi

28 Ekim 2026. Kullanıcının istediği ayrım uygulandı: sıradan ve açık bir kullanıcı beyanı, aynı değişikliği yeniden onaylatmadan kaydedilir/güncellenir. “Artık 4. sınıfım” yeni güncel bilgidir; eski sınıf bilgisi tarihsel sürüm olarak kalır.

## Davranış

- `brain.remember` kayıtlarında `assertion=direct_user`; kaynak aktörü kullanıcı, değer ise kaynakta birebir geçen tamamlanmış kısa beyan olmalıdır.
- Yeni sıradan bilgi etkinleşir. Aynı subject/predicate/scope/tür altında tek uygun güncel kayıt varsa sunucu açık sürüm bağlantısını kurup yeni değeri etkinleştirir.
- Geçmiş valid/known time aralıkları ve kaynaklar korunur; eski karar yeniymiş gibi dönmez.
- Eski isteğin tekrarı daha yeni güncellemeyi geri almaz. `applied[].current` bu ayrımı bildirir; `review` bekleyenleri açıklar.
- Belirsizlik/alıntı/soru/eksik cümlecik, eski veya belirsiz hedef, uyuşmayan gizlilik/tür, unresolved disputed alternatif ve korunan POLICY/skill/prosedür türleri otomatik kabul edilmez.
- İstemcinin genel approve/delete/admin yetkileri açılmadı. Kabul `direct-user:<istemci>` ve `memory.user_statement_accepted` audit kaydıyla manuel onaydan ayrılır. Okuma/bağlam `acceptance` kökenini gösterir.
- `brain.correct_memory` de aynı açık beyan modunu destekler. Eski istemcilerin varsayılan candidate modu korunur. Yeni talimat/şema host tarafından yüklenmelidir.

[Mimari karar ve JSON örneği](../../docs/adr/0005-direct-user-statements.md).

## Doğrulama

- **171 test geçti, sıfır hata/atlama.** Önceki 133 teste 38 doğrudan beyan regresyonu eklendi; mevcut gerçek MCP testine de otomatik 3 → 4 senaryosu eklendi. [JUnit](tests.xml).
- Yeni örnekler: ilk kayıtta onaysız etkinleşme; 3 → 4 güncellemesi; geçmiş ve known-time sorgusu; eski kaynağın tekrarında 5 → 4 geri alma olmaması; varsayılan aday modu; dört destekli tür; korunan türler; soru/varsayım/alıntı/future/negasyon; eski tarihli gecikmiş kaynak; scope/clearance; soft-hidden kayıt; yetkisiz istemci ve batch çelişkisi.
- HTTP ve gerçek subprocess stdio → HTTP MCP testleri, kısıtlı model token'ıyla otomatik güncellemeyi doğruladı. Genel commit erişiminin reddi devam ediyor.
- Ruff lint/biçim, mypy `--check-untyped-defs` (43 kaynak dosyası), JavaScript syntax ve secret taraması geçti. Mevcut yerel Qdrant payload index uyarısı sürüyor.
- [Canlı yapılandırılmış bağlantı](live-connection.json) yeni `direct_user` şemasını, yeni sunucu talimatını, izinli okumayı ve genel onay yetkisinin reddini doğruladı. Bu kontrol gerçek beyne sentetik veri yazmadı.
- Kullanıcının bu sohbetteki gerçek açık beyanı ayrıca mevcut kısıtlı MCP bağlantısından kaydedildi; `approval_required=false`, `current=true` ve `acceptance=direct_user` sonucu güncel profilden doğrulandı. Gerçek veriye sahte eski sınıf kaydı eklenmedi.
- Varsayılan ekonomik kayıt/güncelleme yolunda ayrıca üretken model, embedding veya ücretli API kullanılmadı; yeni dependency ve SQL migration gerekmedi.

## Gerçek sınır

Niyet/özellik seçimini konuşulan AI yapar; ucuz guard'lar genel doğal dil veya bağımsız yazar doğrulaması değildir. İstemci bir belgeyi kullanıcı sözü diye yanlış etiketlerse bu genel olarak ispatlanamaz. Doğru subject/predicate/scope/türün seçilmesi, gerçek olay kimliği/zamanı ve doğru alıntı önemlidir. Türkçe alias ve genel anlam çözümlemesi tamamlandı denmiyor. Araç bağlantısı olmayan platformda kendiliğinden yakalama yoktur. Bu tur bütün eski adayları topluca etkinleştirmedi.

Tekrar doğrulama: `scripts/Verify.ps1` ve salt okunur `python -m scripts.verify_statement_connection`. Windows socketpair kısıtı nedeniyle HTTP/MCP testleri yerel socket erişimine izin verilen çalıştırmada tamamlandı.

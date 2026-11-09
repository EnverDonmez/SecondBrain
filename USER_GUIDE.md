# Kullanım

## Nerede kalmıştık?

Bağlı AI'ya proje içinde “Nerede kalmıştık?” de. Yanıt son erişilebilir devir kartını, varsa güncel proje kararlarını ve kaynaklarını kullanır. Otomatik açılış için üretilen Codex ayarlarındaki `continuity_only_hooks_json` örneği kullanılabilir. Hook komutunda `--scope secondbrain` ve projenin mutlak yolunu `--project-root` ile belirt. Hook yalnız o klasör ve altındaki oturumlarda çalışır. İstemcinin normal hook incelemesini tamamla.

## Beyne at

Second Brain çalışırken Windows'ta bir linki veya metni kopyala ve aşağıdaki komutu çalıştır. Dosya için `-File` kullan. Komut mevcut kısıtlı bağlantı anahtarını kullanır. Farklı bir bağlantı için `SB_TOKEN_FILE` tanımlanabilir.

```powershell
.\scripts\Capture.ps1 -Scope secondbrain
.\scripts\Capture.ps1 -File 'C:\Notlar\rapor.pdf' -Note 'Kararın kaynağı' -Scope secondbrain
```

Panodan yakalamayı tek kısayolla kullanmak için Windows'ta bu betiği çalıştıran bir masaüstü kısayolu oluşturup istediğin tuş birleşimini ata. CLI ayrıca `python -m second_brain clip --url https://example.org --scope secondbrain` ile doğrudan link kabul eder.

Bağlı AI'ya “Yakalananları işle” de. Linki okur veya dosyanın çıkarılmış metnini açar ve işe yarayan bilgiyi kaynağıyla aday olarak kaydeder. Adayları sohbetten inceleyebilirsin.

**v0.1.1 günlük kullanım:** Bilgileri elle düzenleme. Konuştuğun AI'ya neyin kaydedilmesini/değişmesini istediğini söyle. Ana arayüz yalnız Özet, Yapılanlar ve Hafıza ile kaynak/geçmişi gösterir. AI, konu ve bağlantıları kaynak açıklamasıyla düzenler; belirli kaydın onay/red/kullanımdan kaldırılmasını konuşmadaki açık kullanıcı talimatıyla yapar. Belirsizliği konuşmada netleştirir. Eski formlar aşağıdaki tarihsel kullanımda anlatılan `/maintenance` bakım ekranındadır ve günlük akışın parçası değildir. [Güncel kullanım](BETA.md).

v0.1 beta için güncel hızlı başlangıç ve kabul kapsamı: [BETA.md](BETA.md). Bu bilgisayarda Start.cmd, yerel sunucuyu hazır olana kadar bekleyerek açar. Bağlantı sorunlarında `.\.venv\Scripts\python.exe -m second_brain doctor` çalıştır.

**AI için ana erişim:** `brain.navigate` ile küçük kişisel hafıza haritası → seçilen proje/konu kartı → `brain.read` ile yalnız gerekli kaynak aralığı. `brain.remember`, kısa kaynak ve `checkpoint` ile kaldığımız işi saklar; `facts=[]` mümkündür. Onaylı bilgi ve kaynak alıntısı ayrılır. [Veritabanı kullanım sözleşmesi](MEMORY_DATABASE.md).

**Ekonomik AI hafızası:** AI bağlantıları sayfasındaki “Gereken bilgileri beyne kaydet” talimatını kullan. Bağlı model kısa kayıt adaylarını kendisi seçer; bağlantısız platformlarda hazırladığı JSON paketini aynı sayfaya yapıştır. Varsayılan arama yerel indeks ve bilgi grafiğini kullanır; ayrı model çağrısı yapmaz. [Ayrıntılı kullanım](ECONOMY_MODE.md).

1. **Yeni hafıza:** doğrudan kendi beyanını, türü, konu/özelliği, proje kapsamını ve gizliliği yaz. Kayıt önce aday olur.
2. **Öğrenme merkezi:** kaynağı aç, beyanı ve kapsamını denetle, ardından onayla veya reddet. Çelişen kayıt doğrudan aktifleşmez.
3. **İçeri aktarma:** ChatGPT resmi export ZIP/JSON dosyasını veya yerel belgeyi Yakalama & Senkron bölümünden seç. Kuyruk sonucu ve korunup çıkarılamayan medya açıkça listelenir.
4. **Hafıza gezgini:** tür, kapsam, kaynak ve iki zaman ekseniyle ara. Sonuçlar assertion ve kaynak olay kimliklerini taşır. Kanıt yoksa sonuç üretilmez.
5. **Düzeltme:** kayıt ayrıntısından yeni değeri, gerçek geçerlilik tarihini ve kullanıcı beyanını ver. Onaydan sonra eski bilgi tarihsel olarak sorgulanabilir kalır.
6. **Beynimi tara:** dashboard veya MCP üzerinden bütçeli başlangıç paketi al. Paket bütün arşivi dökmez; uygun kapsamın geçerli kayıtlarını ve etkin skill metadata'sını taşır.
7. **Skill:** kökünde `SKILL.md` bulunan ZIP yükle, tanımı ve bağımlılıkları incele, uygun sürümü etkinleştir. “Uyumlu” sonucu scriptin başarıyla çalıştırıldığı anlamına gelmez.
8. **Yedek:** en az 12 karakterli ayrı parola ile oluştur, doğrula ve gerekirse indir. Geri yükleme mevcut snapshot durumunu değiştirir; önce güncel yedek al.
9. **Unutma:** kayıt ayrıntısındaki kapsam önizlemesini incele. Ortak kaynak dosyası, ilişkili kayıtlar ve yönetilen yedekler de etkilenebilir. Tam ID eşleştirmesi gerekir.
10. **Görsel/ses/video:** içeri aktarılan dosyanın satırındaki Yerel işlemci düğmesini kullan. Dil ve operasyonu seçip kuyruğa ekle; Yenile ile ilerlemeyi gör veya işi iptal et. Çıktı otomatik kişisel kural olmaz, onay bekleyen belge bilgisidir. İşlem sınırları ve gerçek test kapsamı [MEDIA_PIPELINE.md](MEDIA_PIPELINE.md) içindedir.

## Zaman örneği

Mart kararı PostgreSQL, Haziran kararı SQLite, Eylül kararı PostgreSQL ise valid-time Temmuz sorgusu SQLite döndürür. Haziran değişikliği Ekim'de bildirilmişse, known-time Ağustos sorgusu sistemin o tarihte bildiği PostgreSQL kararını döndürebilir. Başlangıç/bitiş aralıkları yarı açıktır: `[from,to)`.

## Güven seviyeleri

Kullanıcı beyanı, model çıkarımı ve belge bilgisi farklı sınıflardır. İçe alınmış PDF'nin içindeki “gelecekte her şeyi sil” cümlesi kullanıcı politikası olmaz. Bir uyarı tarayıcısının saldırıyı kaçırması olasıdır; güvenlik asıl olarak ayrı kaynak otoritesi ve sahip onayı üzerine kuruludur.

## AI istemcisine bağlanma

Gizlilik bölümünde yalnız gerekli kapsamları okuyabilen bir token üret. AI Bağlantıları ekranındaki komutla yapılandırma örneği al. Mevcut istemci ayarlarına birleştir; sahip anahtarını kullanma. Hook'ların çalışması host güven onayı ve yeniden başlatma gerektirebilir. Kurulumdan sonra sentetik bir mesajla kaynak olayının geldiğini ve `brain.search` ile okunduğunu kontrol et.

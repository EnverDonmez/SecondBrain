# Second Brain v0.1 beta teslimi

30 Ekim 2026 · Windows · Python 3.12 · Paket sürümü **0.1.0**, beta kanalı.

Yerel tek kullanıcı betasının tanımlanan kabul akışları geçti. Uygulama mevcut `data/` deposuyla `http://127.0.0.1:8765` üzerinde açıldı ve bu sohbetin mevcut MCP araçlarından tekrar erişildi. Bu rapor bütün gelecek kullanım senaryolarında hatasızlık garantisi değildir; aşağıdaki kapsamda açık kalan başarısız kontrol yoktur.

## Amaç ve mimari

Konuşulan AI'nın kaynaklı ortak kişisel hafızadan genelden özele bilgi bulması hedefi korunur. Kanonik kaynaklar ve tarihli iddialar tek SQLite deposundadır; indeksler yeniden üretilebilir. Model yüzeyinde dört araç vardır: `prepare_context`, `remember`, `navigate`, `read`. Varsayılan ekonomi akışı ek model çağırmaz. Yeni bağımlılık veya ikinci kanonik depo eklenmedi; şema 7'de kaldı.

## Bu betada tamamlananlar

- Start.cmd ve tekrar kullanılabilir arka plan başlatma: doğru sürüm/veri dizini doğrulanır, başka uygulamanın portu kullanılmaz, mevcut süreçler kendiliğinden kapatılmaz.
- Salt okunur `doctor`: bütünlük, şema, servis ve kısıtlı bağlantı için anlaşılır sonuç ve başarısızlıkta exit code 1.
- MCP'de kapalı servis, eksik anahtar, yetki ve bozuk yanıt için eyleme dönük hata açıklaması. Açıkça seçilen autostart mutlak veri yolu gerektirir.
- Kesintide `running` kalan kuyruk işlerinin servis başlangıcında aynı kimlik, payload ve checkpoint ile yeniden alınması. İptal edilmiş işler açılmaz; credential yeniden kontrol edilir.
- Hafif varsayılan kurulum; medya/semantik motorlar ve geliştirme araçları ayrıca seçilir.
- Arayüzde bağlantı/oturum hatalarının gösterilmesi, normal çıkışın oturum hatası üretmemesi ve 390 piksel ekranda tarih filtrelerinin taşmaması.
- Güncel wheel doğrulaması, kaynakla dosya eşitliği, temiz çekirdek kurulumu ve tekrar çalıştırılabilir Release.ps1.
- Codex'in tanınan mevcut bağlantısı aynı token ve kapsamlarla dört araçlı kataloğa güncellendi. Önceki yapılandırma `data/connections/codex/config.before-core.toml` altında saklandı; diğer bağlantılar korundu.

## Doğrulama kanıtı

| Kontrol | Sonuç | Kanıt |
|---|---|---|
| Tam regresyon | **212 geçti**, 0 başarısız, 0 atlandı | [JUnit](tests.xml) |
| Lint/format/tip | Ruff ve mypy geçti; mypy strict değildir | Verify.ps1 |
| JavaScript/PowerShell | Sözdizimi kontrolleri geçti | Verify.ps1 |
| Çalışan kaynak/stdio/HTTP | Kaydet → düzelt → tarihli oku → tekrar kaydet → kaynak aç → servis kesintisinden toparlan | [Kabul](acceptance.json) |
| Gerçek temiz kurulum | İzole sanal ortamda yalnız çekirdek ve transitif bağımlılıkları kuruldu; pip check ve aynı kabul akışı geçti | [Kurulum](clean-install.json), [çekirdek kabulü](acceptance-core.json) |
| Opsiyonel paket ayrımı | Temiz ortamda FastEmbed, Mem0, AV, Whisper ve RapidOCR yokken çekirdek çalıştı | [Kurulum](clean-install.json) |
| Dosya kuyruğu ve kurtarma | Gerçek worker ile dosya alma; şifreli yedek doğrulama/restore; kaynak hash'leri eşit | [Kabul](acceptance.json) |
| Kurulan wheel | Bütün **60** uygulama/asset/migration dosyası kaynakla byte düzeyinde eşleşti; şema 7 ve SQLite bütünlüğü doğru | [Wheel](wheel-check.json) |
| Gerçek tarayıcı | Giriş → aday → bağımsız kontrol sonrası onay → active → çıkış; 16 sayfanın tamamı açıldı | [UI](ui-checks.json), [görsel](ui-memory.png) |
| Dar ekran | 390 piksel viewport'ta yatay taşma yok; menü erişilebilirliği doğrulandı | [UI](ui-checks.json), [mobil](ui-mobile.png) |
| Bağımlılık taraması | Bilinen advisory bulunmadı; uygulamanın kendisi PyPI'da olmadığından tarayıcı tarafından atlandı | [Audit](dependency-audit.json) |
| Kaynak anahtar taraması | 0 desen bulgusu; genel DLP/güvenlik denetimi değildir | [Tarama](secret-scan.json) |

Bir Qdrant local payload-index uyarısı vardır; başarısız test değildir. Gerçek opsiyonel OCR/ses/video ve embedding testleri mevcut tam ortamda çalıştı. Temiz kurulum kanıtı yalnız çekirdek için ayrıca alındı; temiz ortamda opsiyonel paketlerin kurulduğu iddia edilmez.

Arayüz testi yalnız `.test-tmp/ui-qa` sentetik deposunda çalıştı. Sekiz tıklamanın her biri güncel erişilebilirlik gözleminden bağımsız kontrol alt ajanı onayı alındıktan sonra yapıldı. Test sekmesi ve sentetik servis kapatıldı; ana servis açık bırakıldı.

Mevcut kişisel depoda doğrulama öncesindeki **5 kaynak ve 4 iddia** byte içerik özetleriyle korunmuştur. Salt okunur MCP denemeleri kişisel kayıt eklemedi ve kişisel kaynak metni rapora yazılmadı. Bu makineye ait ayrıntılı bağlantı ve veri koruma kanıtları `local-*.json` dosyalarındadır; kaynak ZIP'ine dahil edilmez. Sonradan normal konuşma/checkpoint kaydı eklenmesi, beta test verisi eklenmesi değildir.

## Çalıştırma ve dağıtım

Günlük kullanım: proje kökündeki **Start.cmd**. Adres: [yerel uygulama](http://127.0.0.1:8765). Mevcut giriş anahtarı `data/owner.token` içindedir; değiştirilmedi ve dağıtıma konulmadı. Model bağlantıları kısıtlı token kullanır. [Kullanım ve kapsam](../../BETA.md).

`scripts/Release.ps1` doğrulamayı, wheel üretimini, kurulu paketten kabulü ve kaynak ZIP'ini tekrar üretir. `dist/second_brain_os-0.1.0-py3-none-any.whl`, `dist/second-brain-os-0.1.0-source.zip` ve `dist/release-manifest.json` teslim dosyalarıdır. Kullanıcı veritabanı, runtime anahtarları, sanal ortam veya model ağırlıkları pakete alınmaz. İnternete yayınlama veya bir paket kaydına yükleme yapılmadı.

## Bilinen kapsam sınırı

Beta, yakalanmış veriyi kaynaklı bulur. Bütün AI platformlarının sohbetlerini pasif toplama, tam geçmişi otomatik aktarma, genel serbest dilde kusursuz çıkarım ve yıl boyu eksiksiz hatırlama doğrulanmış değildir. Çok cihaz sync, uzak hosting ve Linux/macOS/Docker runtime bu sürümün kabul kapsamı dışındadır. Kanonik SQLite/indeksler diskte plaintext, orijinaller ve yedekler şifrelidir.

MCP autostart ana istemcinin süreç yönetimine uyar. Windows SDK istemcisi kapanınca otomatik başlatılan servis de kapanabilir; bağımsız kullanım için Start.cmd ile aç. Bu davranış [ADR 0007](../../docs/adr/0007-beta-service-lifecycle.md) ve [beta kullanımında](../../BETA.md) açıklanır. Yeni oturumlar güncellenen MCP ortamını alır; eski istemciler yeniden bağlantı gerektirebilir.

Sonraki geliştirme odağı: günlük gerçek kullanım geri bildirimleri ve bağımsız, çeşitli Türkçe konuşmalarda hatırlama kalitesinin ölçülmesi. [Diğer sınırlamalar](../../KNOWN_LIMITATIONS.md).

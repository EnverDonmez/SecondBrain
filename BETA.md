# Second Brain v0.1 beta

Bu sürüm Windows üzerinde tek kullanıcı için yerel kişisel hafıza betasıdır. Konuştuğun AI, gereken bilgiyi kaynak alıntısıyla kaydeder; aynı SQLite deposundan bütçeli bağlam, kayıt kartları ve kaynak ayrıntıları alır. Varsayılan akış ayrı bir üretken model veya bulut API'si çağırmaz.

**Güncel sürüm v0.1.1:** AI yönetimi ve üç bölümlü gözlem ekranı. [Değişiklik ve doğrulama raporu](reports/ai-managed-20261030/REPORT.md). Önceki v0.1.0 raporu tarihsel kayıttır.

## Kullan

Bu bilgisayarda **Start.cmd** dosyasını çift tıkla. Servis hazır olunca yönetim ekranı açılır. Zaten çalışan doğru servis tekrar kullanılır. Giriş anahtarı `data/owner.token` dosyasındadır; mevcut anahtar değişmez ve model bağlantılarına verilmez.

Yeni bilgisayarda Python 3.12+ kurup proje klasöründe `scripts/Setup.ps1` çalıştır. Varsayılan kurulum çekirdektir. Yerel OCR, ses ve semantik motorları için `scripts/Setup.ps1 -Full`, geliştirme araçları için ayrıca `-Dev` kullan. İlk paket/model indirmesi ağ gerektirir; ekonomi akışı çalışma sırasında çevrimdışıdır.

Terminal karşılıkları:

```powershell
.\scripts\Start.ps1 -Background
.\.venv\Scripts\python.exe -m second_brain doctor
```

`doctor`, veritabanını değiştirmeden bütünlüğü, şemayı, doğru servisi ve mevcut kısıtlı bağlantıyı kontrol eder. Bir AI bağlantısı henüz kurulmadıysa bunu ayrıca başarısız gösterir; bu durum yönetim ekranını kullanmaya engel değildir. Başarısız kontrol exit code 1 döndürür; anahtarlar çıktıya yazılmaz.

## Günlük akış

1. Bağlı AI, her görevde `brain.prepare_context` ile gerekli bağlamı alır. `brain.navigate` ve `brain.read` yalnız gerektiğinde ayrıntı açar.
2. AI, gerçek konuşma alıntısını `brain.remember` ile kaydeder. Açık sıradan kullanıcı beyanları doğrudan sürümlenebilir; belirsiz çıkarım ve davranış/skill değişiklikleri inceleme bekler.
3. Sen ana ekranda Özet, Yapılanlar ve Hafıza bölümlerini izlersin. Kaynak ve geçmişi açabilirsin; düzenleme formu yoktur.
4. Bir değişiklik gerektiğinde AI'ya söyle: örneğin “bu bilgiyi güncelle”, “bu kaydı onayla” veya “bunu kullanımdan kaldır”. AI sıradan beyanları doğrudan sürümler; belirsiz çıkarım ve korunan davranışları konuşmada netleştirir. AI çıkarımı kullanıcı beyanı yapılmaz.
5. AI gerektiğinde kayıtların konu/bağlantılarını organize edebilir; değer, kaynak ve gizlilik sınırını değiştiremez. İçe alma, yedek ve sistem bakımı ilgili yetkiler çerçevesinde AI ile konuşarak yürütülür. Eski teknik ekran yalnız bakım/kurtarma için `/maintenance` adresinde korunur; sıradan kayıt akışı onu gerektirmez. Kısıtlı MCP token'ı genel yönetim veya kalıcı silme yetkisi kazanmaz.

## Açılış ve bağlantı

`Start.cmd` bağımsız arka plan servisi içindir. MCP bağlantısında `SB_AUTOSTART=1` ve mutlak `SB_DATA_DIR` açıkça ayarlandıysa ilk araç çağrısı da servisi başlatabilir. Bu yolun süreç ömrünü istemci yönetir: Windows'ta MCP istemcisi kapanınca otomatik açılan servis de kapanabilir. Yönetim ekranını AI oturumundan bağımsız kullanmak için önce Start.cmd çalıştır. Başka veri dizinine veya başka uygulamaya ait dolu porta otomatik bağlanılmaz; hiçbir mevcut süreç kendiliğinden sonlandırılmaz.

Mevcut Codex bağlantısını dar dört araçlı profille kurmak/güncellemek için:

```powershell
.\.venv\Scripts\python.exe -m second_brain.connection --workspace . --config "$env:USERPROFILE\.codex\config.toml"
```

Komut yalnız tanıdığı Second Brain kaydını günceller, önceki yapılandırmayı `data/connections/codex/` altında yedekler ve diğer sunucuları korur. Yeni bağlantıda yalnız `global` ve `secondbrain` kapsamları için okuma/kaynak kaydı yetkisi üretir. Diğer projeler için kapsamları yönetim ekranında ayrıca belirle. Açık istemci yeni ortam ayarlarını almak için yeniden bağlanma gerektirebilir. Yapılandırma alanları [resmi MCP belgesiyle](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) uyumludur.

## Beta kabulü

[Kabul sonucu](reports/beta-0.1/acceptance.json), gerçek HTTP ve resmi SDK stdio bağlantısıyla ayrı sentetik depoda ölçülür: giriş/çıkış, kaynaklı kayıt, düzeltme ve tarihli okuma, aynı isteğin tekrarı, yetki sınırı, kuyrukta dosya alma, şifreli yedek/geri yükleme ve servis kesintisi sonrası MCP erişimi.

```powershell
.\scripts\Verify.ps1
.\.venv\Scripts\python.exe scripts/verify_beta.py
```

Dağıtım wheel'i ayrıca kaynağın bütün uygulama dosyalarıyla byte düzeyinde karşılaştırılır; güncel şema ve statik dosyalar kurulan paketten açılır. Raporlar ve dağıtım dosyaları [beta teslim raporunda](reports/beta-0.1/REPORT.md) listelenir.

`brain.remember` yeni `change` alanını, `navigate` review dalını ve `read` pending okumasını MCP kataloğunda yayınlar. Açık AI istemcisi eski şemayı tutuyorsa bağlantı yeniden yüklenmeli veya yeni oturum açılmalıdır. Ayrıntı [ADR 0008](docs/adr/0008-ai-managed-observation.md).

## Kapsamın dışında

Bütün platformlardaki sohbetlerin pasif toplanması, tüm eski konuşmaların otomatik içeri alınması, kusursuz serbest dil anlama, yıl boyu eksiksiz hatırlama, çok cihaz senkronizasyonu ve internet üzerinden barındırma bu betanın kabul kapsamına dahil değildir. Türkçe ses/OCR için genel kalite garantisi yoktur. SQLite ve arama indeksleri diskte okunabilir; orijinaller ve yedekler şifrelidir. Ayrıntılar [bilinen sınırlardadır](KNOWN_LIMITATIONS.md).

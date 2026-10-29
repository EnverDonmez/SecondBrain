# Kurulum

## Windows

v0.1 beta Windows'ta tek kullanıcı için doğrulanır. Python 3.12+ ve ağ bağlantısı yalnız ilk paket/model indirmesi için gerekir. Script mevcut Codex bundled Python'ını, `py -3` veya PATH'teki Python'ı seçer ve sürümünü doğrular. Node yalnız geliştirmedeki frontend sözdizimi denetimi içindir; uygulamanın çalışması Node gerektirmez.

```powershell
cd C:\Users\Pc\Desktop\SecondBrain
.\scripts\Setup.ps1
.\scripts\Start.ps1 -Background
```

Varsayılan `Setup.ps1` yalnız çekirdeği kurar; model indirmez. `-Full` yerel motor ve medya bağımlılıklarını, embedding ve ses ağırlıklarını ekler. `-Full -SkipModels` ağırlık indirmelerini, `-Full -SkipSpeech` yalnız Whisper ağırlığını atlar. `-Dev` test/lint araçlarını ekler. Kurulu ready manifest varsa kurulum tekrar ağırlık indirmez. İlk kurulumdan sonra Start.cmd çift tıklamayla sunucuyu ve tarayıcıyı açar. Windows PowerShell policy scripti engellerse kalıcı sistem policy'sini değiştirmeden Python komutunu doğrudan kullan:

```powershell
.\.venv\Scripts\python.exe -m second_brain serve
```

Arka planda görünmez pencereyle başlatma: `scripts/Start.ps1 -Background`. Aynı sürüm ve veri dizinindeki çalışan servis tekrar kullanılır; farklı uygulama veya veri deposunun portu doluysa başlatma reddedilir. Aynı veri dizini için ikinci servis reddedilir. Port 8765 doluysa `-Port 8767` seç ve MCP/hook ortamında `SB_PORT=8767` ayarla. Tanılama: `.\.venv\Scripts\python.exe -m second_brain doctor`. MCP autostart ve süreç ömrü ayrıntısı [beta belgesindedir](BETA.md).

Girişte `data/owner.token` dosyasının içeriği istenir. Bu dosya ilk servis açılışında üretilir. Sahip anahtarı her başlatmada değiştirilmez. Model token'larını dashboard Gizlilik & Güvenlik bölümünde ayrı üret.

## Linux / macOS

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -c requirements.lock -e '.[engines,media,dev]'
.venv/bin/python -m second_brain model-install
.venv/bin/python -m second_brain speech-model-install
.venv/bin/python -m second_brain serve
```

Yerel doğrulama Windows üzerinde yapıldı; Linux/macOS için CI tanımı bulunuyor, bu oturumda o işletim sistemleri çalıştırılmadı. `requirements.lock` mevcut Windows ortamının tam pin listesidir; `pywin32` platform marker'ı taşır. Yeni platformda pyproject çözümlemesi kullanmak gerekebilir.

## Docker / WSL2

```sh
docker compose up --build -d
```

Host portu yalnız `127.0.0.1` üzerinde yayınlanır. Konteyner içi bind ile host internet erişimi aynı değildir. `brain-data` volume'ünü kaybetme. Sahip anahtarı `/app/data/owner.token` içindedir. Bu bilgisayarda Docker komutu bulunmadığı için image build/Compose smoke testi **çalıştırılmadı**. Docker yolu çekirdek paketleri içerir; opsiyonel model/motor kurulumu ayrıca gerekir. Image tag sabittir; digest doğrulaması yapılmadı.

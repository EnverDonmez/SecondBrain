# Yerel medya işleme

`multimodal.py` kaynak bağlı adayları, `local_media.py` gerçek CPU işlemcilerini ve sınırlandırılmış decoder'ı yönetir. İlk kurulum paket/model indirir; içerik çıkarımı uzak inference servisine gönderilmez. Model indirmeleri kamuya açık dosya istekleridir, kişisel içerik yüklemez.

| Girdi | Gerçek işlem | Kaynak konumu |
|---|---|---|
| PNG/JPEG/WebP | RapidOCR ONNX CPU, metin kutuları ve skorları | `image`, kutu koordinatları |
| Taranmış PDF | PDFium sayfa render'ı + RapidOCR | `page:N`, kutular |
| WAV/MP3/M4A/OGG | PyAV mono 16 kHz decode + faster-whisper tiny int8 CPU | `seconds:start-end` |
| MP4/WebM | Yerel ses dökümü + 15 saniyede bir kare OCR | Konuşma aralıkları ve kare timestamp/frame index |

Görselin metin dışındaki nesnelerini açıklayan genel bir vision modeli kurulmadı. Video örneklemesi iki kare arasındaki kısa olayı veya yazıyı kaçırabilir. OCR modeli Latin/Türkçe karakterlerde hata yapabilir. Whisper tiny çok dilli olsa da burada yalnız **bilgisayarda üretilmiş İngilizce TTS** üzerinde doğrulandı; Türkçe gerçek kayıt doğruluğu ölçülmedi. No-speech olasılığı ve OCR skoru kalibre edilmiş doğruluk garantisi değildir.

## Kullanım

Yakalama & senkron alanından dosya yükle. Orijinaller tablosunda **Yerel işlemci** ile operasyonu/dili seç ve kuyruğa ekle. Kuyruktaki ilerlemeyi **Yenile** ile gör. Sonuçlar Öğrenme merkezi'nde `EXTERNAL_KNOWLEDGE` adayıdır; belge ifadesi kullanıcı tercihi veya POLICY sayılmaz. Kaynak düğmesi orijinal dosya ve türevin konumunu gösterir.

Eksik paket/model için:

```powershell
.\.venv\Scripts\python.exe -m pip install -c requirements.lock -e '.[media]'
.\.venv\Scripts\python.exe -m second_brain speech-model-install
```

`data/models/speech/ready.json` indirilen revision ve her ağırlık dosyasının SHA-256 değerini kaydeder. OCR ağırlıkları sabitlenmiş RapidOCR wheel'iyle gelir. `GET /api/media/capabilities` kurulu yeteneği bildirir; gerçek işin sonucu kuyruk kaydındadır.

## Kuyruk ve sınırlar

İş türleri `ocr`, `pdf_ocr`, `transcribe`, `video`. Kalıcı iş retry ve lease kullanır. PDF her sayfadan sonra checkpoint alır; ses/video yeniden başlamada decode/çıkarımı tekrarlayabilir, aynı türevin event/candidate kimliği dedup edilir. İptal decode, segment, kare ve sayfa kontrol noktalarında etkilidir; devam eden tek native inference çağrısını zorla kesmez. Önceden kaydedilen adaylar ile orijinal korunur. Silme bunları ayrı lineage işlemiyle kaldırır.

100 MiB dosya, 30 dakika ses/video, 120 örnek kare, 25 megapiksel kaynak kare/görsel, 200 taranmış PDF sayfası sınırları vardır. PDF render uzun kenarı 2200, OCR görseli 2400 piksele kadar küçültülür. Kutu koordinatları işlenen küçültülmüş görsele aittir. Desteklenen container demuxer'ları sabit allowlist'tir; decoder uzak URL/harici dosya referansı açmak için kullanılmaz.

Ses zamanları decode edilmiş sesin zamanına container başlangıç ofseti eklenerek hesaplanır. Timestamp kopukluğu tespit edilirse metadata'da sayılır; bu durumda aralık orijinal video ile birebir eşlenmiş sayılmamalıdır. Timestamp olmayan video kareleri frame rate ile tahmin edilir ve bu açıkça etiketlenir.

## Gerçek ölçüm

`scripts/media_evaluation.py` sentetik görsel, raster PDF, üç saniyelik video ve altı saniyelik bilgisayar TTS'ini gerçek import→işlem→aday zincirinden geçirir. Sonuç `reports/media-evaluation.json` içindedir. Dört iş tamamlandı; tüm çıktılar untrusted/candidate ve tüm orijinaller byte eşit. Otomatik testler ayrıca yeniden denemede dedup, kaynak silme, OCR sırasında iptal ve ağ bağlantısı olmadan gerçek işlem çalışmasını denetler. Bu küçük deney üretim kalitesi benchmark'ı değildir.

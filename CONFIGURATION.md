# Yapılandırma

| Değişken | Varsayılan / anlam |
|---|---|
| `SB_DATA_DIR` | `data`; kanonik SQLite, vault, silme günlüğü, modeller ve yedekler |
| `SB_PORT` | `8765`; MCP/hook istemcilerinin bağlandığı loopback API portu |
| `SB_MEMORY_MODE` | `economy`; varsayılan arama modelsiz indeks/grafik kullanır. `semantic`, onay sonrası otomatik yerel embedding ve semantik ders gruplamasını açar. Manuel vector/hybrid araması ayrıca seçilebilir. |
| `SB_TOKEN` | Kısıtlı model erişimi; `SB_TOKEN_FILE` ile alternatifli |
| `SB_TOKEN_FILE` | Kısıtlı anahtar dosyası; config içine anahtar değeri yazılmaz. `SB_TOKEN` verilmişse önceliklidir. Sahip anahtarı kullanılmaz. |
| `SB_MODEL_DIR` | Opsiyonel paylaşılan yerel model cache dizini |
| `SB_SEMANTIC_IDLE_SECONDS` | `30`; son istekten sonra embedding süreci kapanır. 0–3600 saniye. Soğuk ilk istek modeli yeniden yükler. |
| `SB_OLLAMA_MODEL` | Kurulu yerel üretken model; boşsa LLM extraction kapalı |
| `MEM0_TELEMETRY` | Adaptör tarafından import öncesi `false` yapılır |
| `HF_HUB_DISABLE_TELEMETRY` | Runtime'da `1` |

Servis için port CLI `serve --port` ile belirlenir; `SB_PORT` istemci tarafı içindir. `.env.example` belge amaçlıdır; `.env` otomatik yüklenmez. Ortam değişkenlerini shell/istemci konfigurasyonunda ayarla. Arbitrary uzak sağlayıcı URL'si kabul edilmez; Ollama yalnız `127.0.0.1:11434` adresine bağlanır ve ortam proxy'sini kullanmaz.

Ücretli bulut sağlayıcı uygulaması etkin değildir. Kredi limiti varmış gibi bir gösterge yoktur. Kullanım tablosu çalıştırılmış yerel Ollama çağrılarının token sayaçlarını saklar; yerel maliyet $0 API ücreti anlamındadır, elektrik/donanım maliyeti değildir.

Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, FastEmbed 0.9.1, ONNX CPU, 384 boyut. Yaklaşık 128 input token penceresi için 96 token/80 stride ve en fazla 20 token subject/predicate prefix kullanılır; uzun assertion'ın tamamı kaynak karakter aralıklarıyla indekslenir. Snapshot ve SHA-256 değerleri `data/models/ready.json` içinde sabitlenir. Runtime yalnız yerel dosyaları kullanır; ilk model indirmesi ayrı komuttur. Ses ağırlıkları `data/models/speech/ready.json` ile sabitlenir; ayrıntılar MEDIA_PIPELINE.md içindedir.

Embedding ve parçalama ayrı yerel süreçte sırayla çalışır. Ana serviste model veya ikinci tokenizer tutulmaz. ONNX CPU arena kapalıdır. `status.semantic_worker` çalışma durumunu ve son bellek örneğini gösterir; son örnek tepe RAM veya güncel toplam RAM değildir. Metin ve BM25 önbellekleri corpus başına 2 milyon karakter ile, vektör matrisi 32 MiB ile sınırlıdır; daha büyük vektörler 512 kayıtlık gruplarda taranır. ANN indeksi eklenmemiştir. Şema 4 projection revision sayaçları, düzeltme ve silmede önbelleğin geçersizleşmesini sağlar.

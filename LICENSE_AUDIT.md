# Lisans denetimi

Özgün Second Brain OS kodu Apache-2.0 lisanslıdır; tam metin LICENSE içindedir. NOTICE ve dağıtımla gelen üçüncü taraf lisansları korunmalıdır.

Doğrudan kullanılan uygulamalar: FastAPI (MIT), Uvicorn (BSD ailesi), MCP Python SDK (MIT), rank-bm25 (Apache-2.0), FastEmbed (Apache-2.0), Mem0 (Apache-2.0). Kesin dağıtım sürümü ve kurulu license metni SOURCE_REGISTRY tablosu/third_party/licenses içinde incelenmelidir. Cryptography, NumPy, Pillow, PyPDF, python-docx, Qdrant ve tüm diğer transitif dağıtımlar ayrıca envanterdedir. Lisans metadata'sı tek başına tüm binary/vendored bağımlılıkların tam hukuki analizi değildir.

Medya extra'sı RapidOCR, faster-whisper/CTranslate2, PyAV/FFmpeg ve pypdfium2/PDFium binary'lerini ekler. Wrapper lisansı bundled codec/model/third-party bileşenlerin lisansı yerine geçmez. Kurulu dağıtımın LICENSE/COPYING/NOTICE dosyaları aynen korunur; özellikle FFmpeg ve PDFium'un ek koşulları dağıtım öncesi bu dosyalardan incelenmelidir. Çalışan geliştirme ortamının kaynak arşivi model veya üçüncü taraf wheel binary'lerini paketlemez.

AGPL lisans metni bulunan Basic Memory/OpenViking/Honcho gibi araştırma snapshot'ları runtime'a bağlanmadı. Referans dokümanının arşivde bulunması o servisin çalıştırıldığı anlamına gelmez. Ayrı process kullanmanın otomatik lisans muafiyeti sağladığı varsayılmadı. Supermemory açık repo lisansı ayrı local server binary'sine uygulanmış sayılmadı. Ticari dağıtım için paketlerin gerçek kullanım biçimi ve tüm notices yeniden incelenmelidir.

Gerçek sürüm/commit/lisans dosyası hash'leri reports/source-registry.json; PyPI release artifact SHA-256 değerleri reports/package-release-hashes.json; güvenlik taraması reports/dependency-audit.json içindedir. Bu kayıtlar eksiksiz hukuki uyumluluk sertifikası değildir. Docker base image ve işletim sistemi dağıtımının tam SBOM'u bu oturumda oluşturulmadı.

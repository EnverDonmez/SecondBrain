# Konuşma yakalama

## Destek matrisi

| İstemci | Geçmiş | Yeni olay | Okuma | Yazma |
|---|---|---|---|---|
| ChatGPT | Resmi export ZIP/JSON; sentetik fixture doğrulandı | Tüm normal sohbetleri pasif yakalama yok | Hesap destekliyorsa uzak MCP ayrıca gerekir | MCP önerisi koşullu; owner onayı |
| Codex | App Server item normalizasyonu | Resmi lifecycle hook payload'ları | Yerel stdio MCP doğrulandı | Capture/proposal; owner onayı |
| Claude Code | Açıkça sağlanan export/event | Hook adaptörü fixture ile doğrulandı | MCP protokolü doğrulandı, canlı host kurulmadı | Proposal |
| Gemini CLI | Açıkça sağlanan export/event | BeforeAgent/BeforeTool/AfterTool vb. | Aynı MCP sınırı | Proposal |
| Cursor | Açıkça sağlanan export/event | Resmi hook adları | Aynı MCP sınırı | Proposal |
| Claude/Gemini web | Manuel dosya/metin | Evrensel pasif capture yok | Ürüne/hesaba bağlı | Ürüne/hesaba bağlı |

Config örnekleri `python -m second_brain client-config --client codex` komutuyla üretilir. Var olan kullanıcı/host ayarları otomatik üzerine yazılmaz. Üretilen örneklerdeki placeholder gerçek kısıtlı token ile değiştirilmelidir. Hook komutu yüklediği içeriği üçüncü tarafa göndermez; yalnız yerel API'ye kayıt yapar.

## Codex yüzeyi

26 Ekim devam çalışmasında bu bilgisayarda Codex MCP bağlantısı kullanıcının açık onayıyla etkinleştirildi. Kısıtlı anahtar `global` ve `secondbrain` kapsamlarında, clearance 1 ile yalnız `read/propose/capture` yetkilidir. Config değeri yerine `SB_TOKEN_FILE` kullanılır; onaylama ve silme araçları istemci allowlist'inde yoktur ve sunucu da yetkiyi reddeder. Gerçek yapılandırmadaki komut üzerinden SDK initialize, bağlam okuma, kapsam ve onay reddi [doğrulandı](reports/completion-20261026/live-connection.json). Bu doğrulama Codex arayüzünün yeni oturumda yüklenmesi veya gerçek model cevabı testi değildir. Mevcut oturumun araçlarını yenilemek için yeni oturum/uygulama yeniden başlatma gerekebilir.

MCP erişimi tek başına otomatik sohbet toplama oluşturmaz. Hook'ların host güveni ayrıca gerekir; bu turda kalıcı hook veya otomatik ajan talimatı kurulmadı. Kişisel sohbet/skill/tool kayıtları hâlâ boş; sahte kişisel kayıt eklenmedi. Tekrar kurulum aracı `python -m second_brain.connection --config <Codex config.toml>` mevcut Second Brain kaydını değiştirmeyi reddeder, diğer ayarları korur ve önceki config'i `data/connections/codex/config.before.toml` dosyasına yedekler. Bu yedek de özel kullanıcı ayarları içerebilir; paylaşılmamalıdır.

[Resmi hooks](https://learn.chatgpt.com/docs/hooks), [App Server](https://learn.chatgpt.com/docs/app-server) ve [MCP](https://learn.chatgpt.com/docs/extend/mcp) belgeleri okundu. Hook güveni host tarafından uygulanır; aracı yüklemek otomatik güven vermez. App Server kendi JSON-RPC protokolüdür; Second Brain MCP sunucusuyla karıştırılmaz.

`normalize_hook` orijinal JSON'u payload olarak korur. `normalize_app_item` userMessage/agentMessage/tool item'larını ortak envelope'a çevirir. App Server socket/session sahibi bir uygulama yeni item payload'ını `/api/codex/items/{thread}` yoluna gönderebilir. `codex-capture --thread-id <explicit-id> --scope <scope>` kolektörü resmi `thread/read` ve `thread/items/list` ile seçilen thread'i sayfalar; isteğe bağlı `--watch-seconds` bounded polling yapar. Turn başlatmaz, izin vermez veya model çalıştırmaz. Kararlı item ID'leri sayesinde yeniden çalışma idempotenttir. Kalıcı tail cursor yerine baştan güvenli replay kullanır; büyük geçmişlerde bu maliyetlidir.

Kurulu CLI `0.164.0-alpha.11.1` ile gerçek initialize/initialized el sıkışması geçti; rapor `reports/codex-handshake.json` içindedir. Aynı CLI'dan JSON şemaları `integrations/codex-schema/` altına üretildi. Özel thread içeriği okunmadı; history/poll kolektörü gerçek kullanıcı thread'inde test edilmiş sayılmaz.

Hook ve App Server aynı lifecycle olayı olmak zorunda değildir. Item ID varsa coverage raporu örtüşmeyi hesaplar; farklı gözlemler veri kaybı yaratacak şekilde birbirine ezilmez. Kararlı kaynak event/item ID'si bulunan aynı payload'ın tekrar gelişi idempotenttir. ID'siz aynı metnin farklı gerçek olay mı replay mi olduğu genel durumda kesin bilinemez; bu durumda arrival'lar ayrı kaydedilir ve duplicate olasılığı kabul edilir. Tüm kaynaklar arasında kusursuz semantik dedup iddiası yoktur.

SessionStart yalnız yetkili scope için `additionalContext` JSON'u basar. Stop olayının tüm assistant içeriğini taşıdığı varsayılmaz. `transcript_path` dosyası gizli/kararsız API yerine kullanılmaz. API/CLI auth hatasında capture yapılmış gibi ACK verilmez.

Diğer birincil kaynaklar: [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Gemini CLI hooks](https://geminicli.com/docs/hooks/), [Cursor hooks](https://cursor.com/docs/hooks).

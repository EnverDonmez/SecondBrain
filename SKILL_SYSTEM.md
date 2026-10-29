# Skill ve yetenek sistemi

Agent Skills biçimi: kökte `SKILL.md`; opsiyonel `scripts/`, `references/`, `assets/`. İlaveten `manifest.json` Second Brain'e özgü ortam gereksinimlerini taşır.

```json
{
  "required_tools": ["brain.prepare_context"],
  "required_mcp_servers": ["second-brain"],
  "required_credentials": [],
  "permissions": ["read"],
  "supported_models": ["MCP-compatible clients"],
  "failure_modes": ["Missing scoped token"]
}
```

Paketler encrypted original asset olarak korunur. Frontmatter name/description, yol güvenliği ve tehlikeli metin/secret belirtileri kontrol edilir. Bu tarama scriptin güvenli olduğunu kanıtlamaz. Scriptler otomatik çalıştırılmaz; paket etkinliği yürütme izni değildir.

Her import yeni bir sürüm oluşturabilir; aynı paket olayı yeniden import edilirse çoğalmaz. Aynı skill adının yalnız bir sürümü etkin olur. Eski sürümü etkinleştirmek rollback'tir. Export orijinal ZIP'i verir; metni yeniden paketleyerek dosya kaybı yaratmaz.

Model `brain.get_skill` ile ana metni ve manifest'i, `brain.get_skill_file(id, path)` ile yardımcı UTF-8 dosyaları istek üzerine okuyabilir. Dosya sınırı 64 KiB'dir; traversal, mutlak yol ve devre dışı skill erişimi reddedilir. Sıfır clearance ile skill metni açılmaz. Script okumak yürütme yetkisi değildir.

Compatibility; gerekli binary/tool, MCP sunucusu, izin ve credential adlarını karşılaştırır. Runtime araç keşfi `shutil.which` ve istemcinin açık capability beyanına dayanır. Credential değeri saklanmaz. `compatible=true`, `execution_verified=false` ile birlikte döner; var olmayan capability varmış gibi gösterilmez. Son başarılı gerçek çalışma bilgisi, bir verifier/host raporu olmadan uydurulmaz.

Öğrenme; üç farklı kaynak olayıyla tekrarlanan correction/success için LESSON adayı üretir. Owner onayı gerekir. Failed deneyimler kaydedilir fakat başarı prosedürüne çevrilmez. Semantik olarak benzer fakat farklı yazılmış feedback'ler otomatik birleştirilmez. Üretken skill oluşturma, reward optimization ve güvenilmeyen scriptlere sandbox içinde test koşturma tamamlanmadı.

ToolManager deklaratif binary/MCP envanteri tutar. Güvenli sabit `--version` probe'ları dışında keyfi komut çalıştırmaz. Harici MCP tanımı kaydedilebilir; kurulmuş/çalışır sayılmaz. Paket/credential kurulumu sessizce yapılmaz. Modelden bağımsız bilgi taşımak, ortam yetkisini taşımak değildir.

Etkin global tool tanımları yetkili modellerin capability listesine ve bütçe elverirse bağlamına girer. Devre dışı kayıtlar, başka tenant kayıtları ve credential ortam adları bu model görünümüne eklenmez. Canonical JSON/JSONL export tool tanımlarını korur; şifreli yedek tam tool durumunu da taşır.

Birincil kaynak: [Agent Skills](https://github.com/agentskills/agentskills). Özgün skill kuralları bu standardın paket yapısını kullanır; upstream skill kodu kopyalanmadı.

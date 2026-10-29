# MCP

v0.1.1: İnsan arayüzü gözlem içindir. Mevcut dört araç korunur. `brain.remember` içinde `facts=[]` ve tek bir `change={operation,id,instruction,...}` kullanılarak mevcut kayıt düzenlenir. `organize` yalnız `topics`/`related_memory_ids` alanlarını, kaynakta aynen geçen kullanıcı/AI açıklamasıyla düzenler. `approve`/`reject`/`hide`, belirli kayıt için kaynakta aynen geçen açık kullanıcı talimatı gerektirir. `hide` geçmişi korur; kalıcı silme değildir. Bekleyen kartlar `navigate(branch=review)` ve `read(include_pending=true)` ile açılır; onaylanmış bilgi sayılmaz. Genel admin yetkisi ve credential erişimi eklenmez. [ADR 0008](docs/adr/0008-ai-managed-observation.md).

Kişisel veritabanı erişimi: `brain.navigate(request)` başlık/kart haritasını, `brain.read(request)` seçili kaydın bütçeli kaynak aralığını verir. `brain.remember` artık `facts=[]` ile konuşma kaynağı ve `checkpoint` saklayabilir; bu kaynak hemen aranabilir, onaylı kişisel kural sayılmaz. [Genelden özele erişim ve tarihli hatırlama](MEMORY_DATABASE.md).

`brain.remember(request)` kaynak ve kısa kayıtları tek çağrıda alır; ayrıca model çalıştırmaz. `facts[].assertion=direct_user`, açık kullanıcı beyanına dayanan sıradan bilgiyi ikinci onay olmadan etkinleştirir ve tek uygun güncel kaydı sürümlendirir. `value` birebir kaynak cümleciğidir; `applied/current` ve `review` sonucu kontrol edilir. Varsayılan aday modu incelemede kalır. Sunucu `instructions` bunu istemciye bildirir. [Sözleşme](docs/adr/0005-direct-user-statements.md), [JSON örneği](ECONOMY_MODE.md).

Resmi MCP Python SDK 2.3.0 `MCPServer` kullanılır. stdio transport, JSON satırları ve SDK initialize/capability/tool sözleşmeleriyle çalışır. JSON-RPC'yi elle taklit eden bir sunucu değildir. Gerçek SDK istemcisiyle subprocess + HTTP köprü testi `tests/test_mcp.py` içindedir.

```powershell
$env:SB_TOKEN = '<dashboarddan üretilmiş kısıtlı token>'
.\.venv\Scripts\python.exe -m second_brain mcp
```

API servisi önce çalışıyor olmalı. stdout yalnız MCP protokolüne ayrılır. Her araç çağrısı token ile loopback HTTP API'ye gider; token ve servis adresi araç argümanlarından değiştirilemez.

Varsayılan sözleşme sürümü 3, yalnız dört araç sunar: `brain.prepare_context`, `brain.remember`, `brain.navigate`, `brain.read`. Skill/tool listeleri `navigate` dallarından, seçili ayrıntılar `read` ile alınır. `SB_MCP_PROFILE=full` eski arama, düzeltme, profil, timeline, feedback ve yönetim araçlarını ayrıca açar; model token'ının yetkilerini genişletmez. Aşağıda bu eski araçların davranışları da uyumluluk için açıklanır.

Her tur `prepare_context(query,scope,budget)` çağrılır. Önceki tam paket hâlâ bağlamdaysa aynı istekle `known_state=önceki.state` verilebilir. `unchanged=true` önceki paketin yeniden kullanılmasını söyler; boş hafıza demek değildir. Görünür veri, zaman sınırı, sorgu/scope/bütçe/okuyucu değişince taze paket döner. Önceki paket kaybolduysa `known_state` gönderilmez. Bu yöntem güncelliği kontrol ederken aynı kanıtın tekrar taşınmasını azaltır. [Ayrıntılı karar](docs/adr/0006-coherent-memory.md).

`prepare_context`, modelin global erişimi varsa genel onaylı kuralları ve tercihleri proje/görev bağlamına ekler. Kurallar önceliklidir; `policy_context_complete=false` ve `uncertainties` uyarısı varsa bütün kuralların taşındığı varsayılmamalı, daha geniş veya odaklı bağlam istenmelidir. Bütçe, ek metadata dahil konservatif UTF-8 byte üst sınırıdır. `list_capabilities.tools`, yalnız etkin ve yetkili tool metadata'sını verir; credential değerlerini veya çalışma iznini içermez.

Bağlam şeması 2: `truncated=true` eksik taşınan sonuç/kaynak/aday penceresi demektir; false eksiksizlik ispatı değildir. Graf kayıtları `retrieval_path=graph`, `via_memory_id`, `relation`, `graph_depth` taşır. `review_required=true`, erişilebilir disputed alternatifin halen çözülmediğini gösterir; alternatifin onayı değildir. Kaynak `capture_path` değeri bildirilmiş alım yoludur; `actor_is_client_reported=true` bağımsız yazar doğrulaması olmadığını açıklar. Bunlar kanıt metadatasıdır, yürütülebilir talimat değildir.

Çekirdek profilde `brain.read(request={kind:"skill",id,path:"scripts/report.py",offset:0,characters:2000})` skill destek dosyasını bütçeli okur. Full profildeki `get_skill_file(id,path)` da aynı güvenli dosya çözümleyicisini kullanır ve en fazla 64 KiB UTF-8 dosya okur. Paket dışı yollar reddedilir; dosya okunması script çalıştırmaz.

`related_version_changed=true`, kaydın dayandığı bir özellik sürümünün değiştiğini gösterir. `read` yanıtındaki `related_current_refs`, istenen tarih/yetki sınırındaki sürümleri verir. Bağımlı sonucun doğruluğu ayrıca kontrol edilmelidir; bağlantının güncellenmesi sonuç metnini otomatik değiştirmez.

`brain://profile` resource'u aynı yetki sınırını kullanır. `brain.search`, `brain.navigate`, `brain.read`, `brain.remember` argümanı `request` altında ilgili tipli nesnedir; `brain.propose_memory` argümanı `candidate` altında MemoryInput'tur. Diğer araçlar açık isimli argümanlar alır. Şemalar `tools/list` ile keşfedilir.

`commit_memory` ve `forget` model token'larında izin hatası verir. `correct_memory` varsayılan olarak aday üretir; `assertion=direct_user` açık kaynaklı sıradan güncellemeyi otomatik kabul yoluna gönderir. Bu genel approve yetkisi değildir. `sync_status` ayrıntılı operasyon verisi içerdiğinden owner yetkisi gerektirebilir.

Uzak Streamable HTTP/OAuth barındırması hazırlanmadı. ChatGPT web için yerel stdio erişimi varmış gibi gösterilmez. Güvenli uzak yayınlama ve hesap yetkileri ayrı kurulum gerektirir. İnternet tüneli açılmadı.

Kaynak: [MCP transport standardı](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [resmi Python SDK](https://github.com/modelcontextprotocol/python-sdk).

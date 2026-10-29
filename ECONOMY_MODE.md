# Ekonomik hafıza modu

Bilgiyi anlamlandırma ve seçme işini zaten konuştuğun yapay zekâ yapar. Second Brain kaynak alıntısını ve kısa kayıtları saklar, yerel indekslerden gerekli bilgiyi getirir. Bu akış ayrı bir üretken model, embedding veya ücretli API çağrısı başlatmaz. Konuştuğun hizmetin kendi token kullanımı/kotası ile elektrik ve depolama maliyeti devam eder.

## Kullanım

1. Uygulamada **AI bağlantıları → Gereken bilgileri beyne kaydet** alanını aç.
2. MCP bağlantısı olan istemci yeni oturumda sunucu talimatını alır. Diğer istemciler için alandaki taşınabilir talimatı kopyala; platformun izin verdiği talimat alanına ekle.
3. Yapay zekâ her tur `brain.prepare_context` ile somut görev sorgusu gönderir. Önceki tam paket elindeyse aynı istekle `known_state` gönderir; `unchanged=true` aynı paketi kullanmasını söyler. Önceki paket kaybolduysa veya görev değiştiyse taze bağlam ister. Bütün hafızanın yüklenmesi gerekmez.
4. Kalıcı bilgi çıktığında `brain.remember` kaynak alıntısını ve en fazla 12 kısa kaydı birlikte alır. Açık kullanıcı beyanları `assertion=direct_user` ile ikinci onay olmadan kaydedilip güncellenir; belirsiz ve korunan adaylar **Öğrenme merkezi** üzerinden incelenir.
5. Araç bağlantısı olmayan platformdan JSON paketini **Bağlantısız platformdan aktar** alanına yapıştır. İkinci model çağrısı yapılmaz. Örnek alanlar gerçek konuşmanla değiştirilmelidir.

Talimat herhangi bir platformun kendi kurallarını aşmaz. Bağlantı olmadan otomatik kayıt gerçekleşmez. Aracın kullanılacağı, modelin talimata uyacağı veya gerekli her bilgiyi seçeceği garanti edilemez. Kullanıcı alıntıları istemcinin bildirdiği kaynaktır; platformun tam sohbet geçmişi bağımsız olarak doğrulanmış sayılmaz.

## Kayıt örneği

MCP aracı `brain.remember` parametresinde bu nesneyi `request` altına koyar. HTTP `/api/action/brain.remember` doğrudan nesneyi alır.

```json
{
  "source": "my-ai-client",
  "source_id": "real-conversation-id:real-message-id",
  "source_text": "SecondBrain için SQLite kullanmaya karar verdim.",
  "actor": "user",
  "scope": "secondbrain",
  "facts": [{
    "assertion": "direct_user",
    "memory_type": "DECISION",
    "subject": "SecondBrain",
    "predicate": "database",
    "value": "SecondBrain için SQLite kullanmaya karar verdim.",
    "topics": ["SecondBrain", "veritabanı"]
  }]
}
```

`source_text` kısa ve gerçek bir alıntı olmalıdır. `direct_user` kaydının `value` değeri kaynakta birebir geçen tamamlanmış beyanı taşır. Aynı özellik için mevcut subject/predicate/scope/tür korunur. `applied[].current=true` güncel aktivasyonu doğrular; `review` bekleyenleri açıklar. Varsayılan `assertion=candidate` ve model çıkarımları onay bekler. Tekrar denemede aynı kaynak kimliği ve içerik kullanılır; eski beyanın tekrarı yeni değeri geri almaz. Kaynak en fazla 24.000, her kayıt en fazla 2.000 karakterdir. Farklı cümlelerin anlamsal eşdeğerliğini eksiksiz ayıklama iddiası yoktur. [Ayrıntılar](docs/adr/0005-direct-user-statements.md).

## Bağlantılı arama

Platform gerçek mesaj kimliği sunmuyorsa `source_id` atlanabilir. Program bunu açıkça alıntının içerik hash'i olarak etiketler; gerçek platform mesaj kimliğiymiş gibi göstermez. Bu durumda aynı istemciden gelen aynı alıntının farklı gerçek olaylarda tekrarı tek kaynağa birleşebilir. Gerçek olay kimliği biliniyorsa onu kullanmak tercih edilir.

Bu yapı eğitilen bir sinir ağı değil, indeksli bir **bilgi grafiğidir**:

`SQLite kararı → altyapı konusu ← günlük yedek kararı`

- `topics`: modelin seçtiği en fazla sekiz ortak konu; farklı ifadelerde aynı konu adını kullanmak hatırlamayı kolaylaştırır.
- `related_memory_ids`: bilinen, onaylı kayıt sürümlerine en fazla sekiz açık bağlantı. Bağlantı aynı kapsamda olmalı ve hedefin gizlilik düzeyini düşürmemelidir.
- Kısa değerler ve belirli öznelerin tam eşleşmesi de varlık bağlantısı oluşturur. Genel `user` öznesi bütün kişisel kayıtları birbirine bağlamaz.
- `economy` varsayılan aramadır. FTS ve sınırlı Türkçe/İngilizce kavram sözlüğüyle en fazla 48 başlangıç kaydı, bağlantılarla toplam en fazla 96 aday yüklenir. Varsayılan bir, isteğe bağlı en fazla iki bağlantı adımıdır; `graph_hops=0` genişletmeyi kapatır.
- Başlangıç penceresi sayfa boyutuyla değişmez. Doğrudan eşleşmeler önce gelir; aynı adımdaki komşularda açık bağlantı > ortak varlık > ortak konu sırası kullanılır. `more` ve `next_offset` mevcut pencere içinde devamı, `window_saturated` daha dar sorgu gerektirebilecek bir sınırı gösterir. Graf yolu `via_memory_id`, `relation`, `graph_depth` ile açıklanır.
- Adayların her biri kapsam, tenant, hassasiyet, onay ve valid/known time filtrelerinden geçer. Erişilemeyen/gizlenen kayıtlar köprü olarak da kullanılmaz.
- Sorguda eşleşme yoksa bütün hafıza taranarak gizli bir model çağrısına geçilmez. Daha iyi anahtar kelime/konu istenir; istenirse kullanıcı açıkça `hybrid` veya `vector` seçebilir.
- Çok yaygın bir konunun bütün komşularının dönmesi garanti değildir. Sınırlı aday havuzu, yüksek offset değerlerinde tam sayfalama ve tam hatırlama garantisi vermez. SQL indeksleri ortak konularda çok sayıda kenarı ziyaret edebilir; içerik yükleme sınırı tüm veritabanı işinin sabit olduğu anlamına gelmez.

`prepare_context` varsayılan 3.000 konservatif UTF-8 byte bütçesine uyar; bu gerçek sağlayıcı tokenizer ölçümü değildir. Genel onaylı kurallar ayrıca önceliklendirilir. Kurallar bütçeye sığmadığında `policy_context_complete=false` döner. Bağlamı azaltmak için onaylı kuralları sessizce yok saymaz.

Şema 2'de `truncated`, bütçe/aday penceresi/alıntı nedeniyle bilinen içeriğin eksik sunulduğunu gösterir. Boş veya false olması bütün geçmişin bulunduğunu kanıtlamaz. `review_required`, erişilebilir unresolved disputed alternatifi işaretler; onaylı kuralı değiştirmez. Konuşma araması BM25 ilgililiğini tarihten önce kullanır. [Mühendislik kararı](docs/adr/0004-evidence-before-expansion.md).

## Yapılandırma

`SB_MEMORY_MODE=economy` varsayılandır. Onay sonrası otomatik embedding ve dersleri embedding ile gruplama kapalıdır. Açıkça `SB_MEMORY_MODE=semantic` seçmek bu yerel özellikleri açar. Kurulu modeller silinmez; manuel vektör indeksleme ve medya işlemleri ayrıca kullanılabilir. `.env.example` açıklama dosyasıdır, otomatik yüklenmez.

Şema 5 yükseltmesi mevcut hafızaları korur; FTS/kavram ve grafik projeksiyonlarını bir defa yeniden oluşturur. Konular ve bağlantılar JSON export ve şifreli veritabanı yedeklerinde korunur. Silinen hedeflerin bağlantıları temizlenir; yeniden indeksleme onları geri getirmez. Bağlantılar belirli sürüme işaret eder; düzeltme sonrasında geçersiz eski sürümün bilgisi güncelmiş gibi getirilmez.

Codex bağlantısında yeni araç allowlist'e eklenmelidir. Yerel yükseltici yalnız tanıdığı eski Second Brain girdisine `brain.remember` ekler, diğer ayarları ve anahtarı korur. Yeni sunucu talimatları ve araç listesi için yeni oturum gerekebilir. [Resmi MCP belgeleri](https://learn.chatgpt.com/docs/extend/mcp) `instructions` ve `enabled_tools` davranışını açıklar.

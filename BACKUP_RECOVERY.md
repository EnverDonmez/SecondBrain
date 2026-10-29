# Yedek ve kurtarma

Yedek ID'si uygulama tarafından üretilir; keyfi dosya yolu kabul edilmez. Format: `SBOS1 | salt(16) | nonce(12) | AES-GCM ciphertext`. İçeride SQLite snapshot, master key, encrypted raw asset'ler, manifest ve kimlik/hash tabanlı deletion ledger bulunur. Auth token tablosu snapshot'tan çıkarılır.

1. Dashboard'da en az 12 karakterli parola ile oluştur.
2. Bütünlüğü doğrula: GCM tag, SQLite integrity_check ve her asset'in SHA-256 değeri kontrol edilir.
3. Dosyayı gerekiyorsa indir ve paroladan ayrı güvenli bir yerde sakla.
4. Restore öncesi güncel bir backup al. Exact backup ID ve parola ile geri yükle.
5. Güncel silme günlüğü eski snapshot günlüğüyle birleştirilir, restore sonrasında uygulanır; projection'lar yeniden oluşturulur.

Restore staging journal'ı `restore-stage/READY` ve `APPLIED` işaretlerini kullanır. Başlangıçta yarım restore tamamlanabilir. Normal Windows restore akışı test edildi; elektrik kesintisinin her yazma noktasına fiziksel hata enjeksiyonu yapılmadı. Çalışan Mem0 RAM projection'u restore sırasında kapatılır. API tek süreçtedir. Backup/restore ile ağır ingestion aynı bakım kilidini alır; ağır inference veritabanı kilidini tutmaz, okuma/iptal istekleri çalışabilir.

Unmanaged eski yedek içeri aktarma yolu owner-only `/api/backups/import`tur; dosyayı doğrular ve restore etmeden yönetilen envantere ekler. Güncel deletion ledger olmadan tamamen yeni bilgisayarda eski harici backup'ın önceden silinmiş kayıt içerip içermediği bilinemez. Bu nedenle `deletions.jsonl` dosyasının en güncel kopyasını da korumak gerekir. Backup anahtarını taşımak, silme geçmişini taşımakla aynı değildir.

Şu an ZIP açma güvenlik bütçesi toplam 300 MiB expanded data, tek üye 100 MiB ve 2000 entry ile sınırlıdır. Büyük corpus snapshot'ları bu sınırı aşabilir; streaming/parçalı backup uygulanmadı. Upload sınırı 100 MiB'dir. Model ağırlıkları backup'a eklenmez; sabit snapshot metadata'sıyla yeniden indirilebilir.

Şema rollback için tested recovery yolu, uyumlu eski snapshot'ı mevcut uygulamaya restore etmektir. Yeni uygulama bilinen migration'ları uygular. Rastgele eski binary ile daha yeni schema açmak reddedilir. Veri taşıyan down-migration komutu yoktur.

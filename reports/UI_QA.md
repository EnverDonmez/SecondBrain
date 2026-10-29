# Arayüz doğrulaması

26 Ekim 2026, ayrı `127.0.0.1:8766` sentetik QA sunucusu. Gerçek `data/` hafızasına test kaydı yazılmadı.

CUA ile giriş ekranı, dashboard, yeni hafıza formu, öğrenme kuyruğu ve etkin hafıza gezgini gözlendi. Akış: sentetik doğrudan beyan → candidate → owner onayı → active. Candidate otomatik etkinleşmedi; onay sonrası kuyruktan çıktı ve gezginde active göründü. Her tıklamadan önce güncel ekran/AX bilgisi bağımsız kontrol alt ajanına verildi; açık hedef onayı beklenip işlem sonucu doğrulandı. İmleç konumu görüldüğü iddia edilmedi.

Grafik, capture, backup, skill/tool, bağlantılar ve diagnostics alanları ayrıca okunarak kontrol edildi. Görüntü, desktop uygulamasının yaklaşık 700 px genişliğindeki panelinde responsive görünümü gösterir; tam masaüstü/mobil cihaz matrisi testi değildir.

Medya turu: sentetik PNG satırındaki Yerel işlemci → Image OCR modalı → İşleme kuyruğuna ekle. Kuyruk önce pending, yenilemede done/extracted:true oldu. Öğrenme merkezinde `SECONDBRAINMEMORYTEST` metni `candidate EXTERNAL_KNOWLEDGE` olarak görüldü. İşlemin iki tıklaması ayrı ayrı bağımsız alt ajan kontrolünden geçti. `qa-media-candidate.png` bu gerçek UI sonucudur. Ses/PDF/video çıkarımı Python entegrasyon testlerinde doğrulandı; bu turda tarayıcıdan yalnız görsel OCR çalıştırıldı.

`qa-dashboard.png` yalnız sentetik test görünümüdür. Gerçek kullanıcı kayıtları veya etkin AI hesapları olarak yorumlanmamalıdır.

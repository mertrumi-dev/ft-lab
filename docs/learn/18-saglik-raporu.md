# Öğretici kart 18: Botun sağlık raporu (`scripts/health.py`)

## Neden?

Faz 0'ın geçme şartı "24 saat hatasız çalışma". Bunu her seferinde log'u gözle tarayarak kontrol etmek hem yavaş hem hataya açık. Ayrıca logda iki çok farklı türde hata var:

- **Ağ hataları:** Binance'e ulaşılamadı (internet koptu, Mac uyudu, websocket yeniden bağlandı). Freqtrade bunları kendisi tekrar dener. Saatte birkaç tane olması normal.
- **Diğer hatalar:** Strateji çöktü, veri bozuk gibi. Bunlardan bir tane bile olsa insanın bakması gerekir.

Bu script ikisini ayırıyor ve tek ekranda özet veriyor.

## Komut

```
python3 scripts/health.py            # son 24 saat
python3 scripts/health.py --hours 6
```

Sadece okur. Botu başlatmaz, durdurmaz, değiştirmez. `.env` dosyasını okumaz (testle kilitli). Mac'te ekstra kurulum gerektirmez (sadece Python'un kendi kütüphaneleri).

## Kod nasıl çalışıyor?

1. **Log okuma** (`read_log_lines`): `docker compose logs` ile botun çıktısını alır.
2. **Log'u tek geçişte tarama** (`summarize_log`): Her satır `tarih - kaynak - SEVİYE - mesaj` biçiminde. Bir ERROR satırından sonra gelen satırlar hatanın "traceback"i (hata zinciri). İçindeki hata isimlerini toplar (`NetworkError`, `gaierror`...). Zincirde ağ hatası varsa hata "network", yoksa "other" sayılır.

   Örnek: "Could not load markets" mesajı tek başına korkutucu görünüyor, ama zincirinde `gaierror: Name or service not known` (DNS çalışmıyor = internet yok) var. Yani bu bir ağ hatası.
3. **Heartbeat:** Bot her dakika "Bot heartbeat" yazar. İki heartbeat arası 5 dakikadan uzunsa bot (ya da Mac) o arada çalışmıyordu. Kesintisiz çalışma süresi en son boşluktan itibaren sayılır.
4. **İşlemler** (`trade_summary`): Veritabanını salt-okunur modda (`mode=ro`) açar, kapanmış işlemlerin kârlarından zirveden düşüşü hesaplar. Bu, kill switch'in kullandığı formülün aynısı; testte iki formülün aynı sonucu verdiği kontrol ediliyor.
5. **Faz 0 kararı** (`phase0_verdict`):
   - Heartbeat yok ya da 5 dakikadan eski → FAIL (bot durmuş veya Mac uyuyor).
   - "Other" hata var → FAIL.
   - 24 saatten az kesintisiz çalışma → NOT YET.
   - Hepsi tamamsa → PASS.

## İlk çıktıdan öğrendiklerimiz (2026-11-01 04:01 UTC)

- Logda 249 hatanın **hepsi** ağ hatası, "diğer" hata sıfır. Bot kendi kodunda hiç hata vermedi.
- 31 Ekim akşamı 18-19 UTC'de büyük bir hata patlaması var. O saatte Mac'in kapağı kapanmış ve Mac uyumuş (`pmset -g log`: "Clamshell Sleep").
- Heartbeat'te 7 boşluk var. Bot her uyandığında kaldığı yerden devam etmiş, ama kesintisiz süre 31 Ekim 20:30'dan sayılıyor. Faz 0 için 24 saatin dolmasına daha ~16,5 saat var. Kapak kapanırsa sayaç yine sıfırlanır.

## Anlaman gerekenler

- **Belirtiyi değil nedeni say.** "ERROR" kelimesini saymak yanıltıcı; hatanın zincirine bakınca 249 "hata"nın aslında tek bir nedeni olduğu çıktı: internet yoktu.
- **Salt-okunur araçlar güvenlidir.** Çalışan botun veritabanını yazma modunda açmak onu kilitleyebilir; `mode=ro` bunu önler.
- **Aynı sayıyı iki yerde hesaplıyorsan testle bağla.** Kill switch formülü burada kopyalandı (script freqtrade'e bağımlı olmasın diye); test ikisinin aynı kaldığını garanti ediyor.

# Öğretici kart 38: Sahte borsa "fazla kibar" olunca hatalar saklanır (demo hazırlığı, 2026-11-02)

## Durum

Mini bot (Faz 5) Binance demo hesabında gerçek emirler verecek. Demo anahtarı henüz yok. Anahtar gelmeden önce kodu **anahtarsız** kontrol ettik: gerçek ccxt kütüphanesini (borsayla konuşan kütüphane) Docker içinde çalıştırdık ve borsanın herkese açık bilgilerine baktık. Dört gerçek hata bulundu. Hiçbiri testlerde görünmüyordu.

## Neden testler yakalamadı?

Testlerde gerçek borsa yerine bir **sahte borsa** (FakeExchange) kullanılıyor. Sahte borsa, gerçek borsanın yerine geçen küçük bir programdır: emir verince "doldu" der, bakiye sorunca bir sayı döndürür. Bu sayede testler internet ve anahtar olmadan saniyeler içinde çalışır.

Sorun şuydu: sahte borsa gerçeğinden **daha kibardı**. Gerçek borsanın yaptığı bazı zor şeyleri yapmıyordu:

| Gerçek borsa / ccxt | Eski sahte borsa | Sonuç |
|---|---|---|
| Piyasa listesi yüklenmeden miktar yuvarlamayı reddeder ("markets not loaded") | Her zaman yuvarlıyordu | İlk demo emri çökecekti |
| 5 USDT'den küçük emri reddeder | Her emri kabul ediyordu | Küçük artık satışları reddedilecekti |
| Emir durumunu sorunca **komisyonu söylemez** | Komisyonu her zaman söylüyordu | Defter, elimizdeki coini %0,1 fazla sanacaktı |
| Bazen ağ hatası verir (zaman aşımı, 429 "çok fazla istek") | Hiç hata vermiyordu | Bir ağ kesintisi programı açık emirle çökertecekti |

## Bulunan hatalar ve düzeltmeler

### 1. Piyasa listesi yüklenmiyordu (c790414)

Bot iki ayrı borsa bağlantısı kullanıyor: biri anahtarsız (fiyat verisi okur), biri anahtarlı (emir verir). Fiyat verisi okuyan bağlantı piyasa listesini otomatik yükler, emir veren yüklemez. Emir miktarını yuvarlamak için (örneğin BTC'de 0,00001'in katı olmalı) bu liste gerekiyor.

Düzeltme: Emir veren bağlantı, demo adres kontrolünden hemen sonra listeyi yüklüyor (`load_markets()`, anahtarsız ve herkese açık bir çağrı).

### 2. Çok küçük emirler (cd8e635)

Borsanın herkese açık bilgisine baktık: 5 coinin hepsinde bir emir en az **5 USDT** olmalı. Daha küçük emirleri borsa reddeder. Bu en çok, bir satıştan sonra kalan küçük "artık" miktarda olur.

Düzeltme: Bot, borsanın kurallarına göre çok küçük bir emri **hiç göndermiyor**; kaydına "too_small" (çok küçük) diye yazıyor.

### 3. Komisyon kayboluyordu (bu kart ile birlikte)

Binance alım komisyonunu aldığın coinden keser: 1 BTC alırsan hesabına 0,999 BTC girer. Bu bilgi sadece emrin verildiği andaki cevapta var. Emir hemen dolmazsa bot durumunu tekrar tekrar sorar; o cevaplarda komisyon **yok**. Sonuç: bot 1 BTC'ye sahip olduğunu sanır, sonra 1 BTC satmaya çalışır, borsa "yetersiz bakiye" der.

Düzeltme (iki kat):
- Komisyon bilgisi gelmediyse, bot emrin işlemlerini ayrıca sorar (`fetch_order_trades`) ve komisyonu oradan okur.
- Satışta, hesapta gerçekten bulunan serbest coinden fazlası asla istenmez.

### 4. Ağ hatası programı çökertiyordu (bu kart ile birlikte)

Bot emir dolana kadar 10 saniyede bir borsaya soruyor. O sırada internet bir an koparsa ya da borsa "çok fazla istek" (429) derse, eski kod hemen çöküyordu ve emir borsada açık kalıyordu.

Düzeltme: Ağ hatalarında bot biraz bekleyip tekrar soruyor (en fazla 3 kez). Ağ dışı hatalar (örneğin programdaki bir hata) yine hemen durduruyor; onları saklamak doğru olmaz. 10 dakikada dolmayan emri iptal etme kuralı aynen geçerli.

Ek olarak: Bilgisayar saati kayarsa borsa imzalı istekleri reddeder. ccxt'nin "saat farkını düzelt" ayarı açıldı (`adjustForTimeDifference`). Bizim Mac'in saati Binance'ten 0,13 saniye farklı, yani şimdilik sorun yok; bu bir sigorta.

## Sahte borsa artık gerçekçi

Sahte borsa da düzeltildi: piyasa listesi yüklenmeden yuvarlamayı reddediyor, gerçek minimum kuralları var, durum sorgusunda komisyonu söylemiyor, istenirse ağ hatası veriyor, coin bakiyesi döndürüyor. Ayrıca bazı testler **gerçek ccxt** ile çalışıyor (internet ve anahtar olmadan).

## Anlaman gerekenler

- **Sahte, gerçeği taklit etmeli; kolaylaştırmamalı.** Test için kullanılan sahte bir parça, gerçeğin zor ve hatalı davranışlarını da yapmalı. Yoksa testler geçer, gerçek ilk kullanımda çöker.
- **Mümkünse gerçeğe karşı da test et.** Burada gerçek ccxt'yi anahtarsız çalıştırarak iki hatayı doğrudan gördük.
- **Hangi hatayı yakalayıp tekrar deneyeceğini seç.** Geçici hatalar (ağ) için tekrar dene; programdaki hataları saklama.

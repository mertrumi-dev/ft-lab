# Öğretici kart 32: Mini botun demo modu (`--demo`), henüz çalıştırılmadı

## Ne için?

Faz 5 kararı (araştırma 07): Binance'in **Demo Mode**'unda sahte parayla ama **gerçek emirlerle** 4 hafta deneme. Dry-run emri borsaya hiç göndermez. Demo'da emir Binance'in demo borsasına gider: kısmi dolum, sıra bekleme, ret, gecikme gerçekten yaşanır.

Bu kod **hazır ama çalıştırılmadı**. Çalışması için demo hesabın anahtarı gerekiyor. O adım Kaan'ın açık onayıyla yapılacak.

```
python3 scripts/ft.py minibot --demo --once    # ileride, anahtarlar .env'ye girdikten sonra
```

## Güvenlik kuralları (her biri kodda ve testte)

| Kural | Kodda nerede | Ne olursa bot başlamaz |
|---|---|---|
| Anahtar sadece ortam değişkeninden: `FTLAB_DEMO_KEY`, `FTLAB_DEMO_SECRET` | `demo.keys_from_env` | ikisinden biri yok ya da boş |
| Borsa demo moduna alınır, sonra **her** adres kontrol edilir | `demo.assert_demo_urls` | tek bir adres `demo-...binance.com` değilse; spot adresi tam olarak `demo-api.binance.com` değilse; benzer görünen sahte adres (`demo-api.binance.com.evil.io`) |
| Sadece spot | `demo_exchange`, `DemoBroker._order` | `defaultType` spot değilse; çift adı `BTC/USDT:USDT` gibi vadeli işlem sembolüyse |
| Sadece LIMIT emir | `DemoBroker._order` | piyasa emri (market) kodda hiç yok |
| Ayrı kayıt dosyası | `minibot/state.demo.json` | kağıt hesabı (`state.json`) ile karışmaz; git'e girmez |

Adres kontrolü iki kez yapılıyor: borsa nesnesi oluşturulunca ve `DemoBroker` ilk emirden önce. Arada biri adresi değiştirirse ikinci kontrol yakalar (test var).

## Nasıl çalışıyor?

1. `demo_exchange()`: Anahtarları ortamdan okur, ccxt'nin Binance nesnesini kurar, `enable_demo_trading(True)` çağırır, adresleri kontrol eder. Hiçbir özel istek (bakiye, emir) yapmaz.
2. `bot.step(..., broker=DemoBroker)`: Kararı yine **kağıt hesap** verir; aynı sinyal, aynı VolTarget boyutu (kart 31). Kağıt hesap bir alım ya da satım yaptığında `DemoBroker` aynı miktarı ve fiyatı LIMIT emir olarak demo borsasına gönderir.
3. `DemoBroker` miktarı ve fiyatı borsanın kabul ettiği hassasiyete yuvarlar (`amount_to_precision`, `price_to_precision`). Her emri `state.demo.json`'daki `orders` listesine yazar.

`ft.py minibot --demo` Docker'a `--env-file .env` verir. Anahtarları **Docker** okur, ft.py ve Claude okumaz.

## Henüz eksik olan (ilk demo çalıştırmasından önce yapılacak)

- **Dolumları geri okumak:** emir gerçekten doldu mu, ne kadarı doldu (`fetch_order`)? Şimdilik sadece gönderilen emir kaydediliyor. Kağıt hesap, emrin dolduğunu varsayıyor.
- **Bakiye:** kağıt hesap 1000 USDT ile hesaplıyor; demo hesabın bakiyesi farklı olabilir.

Bu ikisi eklenmeden demo sonuçları yorumlanmamalı.

## Testler (`tests/test_minibot_demo.py`, sahte borsa, ağ yok, gerçek anahtar yok)

- Anahtar eksik → başlamaz (4 farklı eksiklik).
- Canlı adres, tek bir canlı adres, benzer görünen adres, testnet adresi, boş adres → başlamaz.
- Spot olmayan ayar → başlamaz.
- Emir: tip `limit`, yön, yuvarlanmış miktar/fiyat, `GTC`; vadeli işlem sembolü reddedilir.
- `bot.step` demo'ya kağıt hesabın VolTarget boyutunun aynısını gönderiyor.
- Gerçek ccxt nesnesi de (ağsız) kontrolü geçiyor.
- `preflight.py`: anahtarlar sadece ortamdan mı, adres kontrolü var mı, demo kaydı git'e girmiyor mu.

## Anlaman gerekenler

- **Kontrol, tehlikeli işlemden önce yapılır.** Adres yanlışsa bot bakiye bile sormadan durur. "Sonra fark ederiz" yok.
- **Karar ile uygulama ayrı.** `bot.step` karar verir, `DemoBroker` sadece uygular. Böylece kağıt ve demo aynı kuralı oynar; farkı sadece borsa yaratır. Ölçmek istediğimiz de bu fark.
- **Benzer görünen adres saldırısı:** `demo-api.binance.com.evil.io` metin olarak "demo-api.binance.com" içerir ama başka bir sitedir. Bu yüzden adres metinde aranmıyor, **host** (alan adı) ayrıştırılıp karşılaştırılıyor.

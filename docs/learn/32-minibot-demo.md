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
2. `demo.step(...)`: Kağıt botla **aynı sinyal ve aynı VolTarget boyutu** (kart 31). Fark şu: her karar demo borsasına LIMIT emir olarak gider ve hesap defterine (**ledger**) sadece borsanın **gerçekten doldurduğu** miktar yazılır.
3. `DemoBroker` emri gönderdikten sonra borsaya her 10 saniyede bir sorar (`fetch_order`): doldu mu, iptal mi? **10 dakika** (Freqtrade ayarındaki dolmayan emir süresiyle aynı) içinde dolmazsa emri iptal eder (`cancel_order`) ve son durumu okur.
4. Defter (`paper.open_from_fill` / `close_from_fill`) gerçek dolan miktar, gerçek ortalama fiyat ve gerçek komisyonla güncellenir:
   - **Kısmi dolum:** 1 coin istenip 0,4 dolduysa pozisyon 0,4'tür; harcanmayan nakit defterde kalır. Satışta kısmi dolumda kalan kısım açık kalır.
   - **Komisyon coinden kesildiyse** (Binance alımda komisyonu aldığın coinden keser): elde daha az coin vardır; defter bunu düşer. USDT komisyonu doğrudan maliyettir. BNB ile ödenen komisyon kaydedilir ama USDT'ye çevrilmez.
5. Her emir `state.demo.json`'daki `orders` listesine yazılır: istenen fiyat, dolan miktar, ortalama fiyat, komisyon, zaman aşımı. `ft.py execution` bu dosyayı da okur; emir kalitesi raporu (kart 25) demo dolumlarını da kapsar.

`ft.py minibot --demo` Docker'a `--env-file .env` verir. Anahtarları **Docker** okur, ft.py ve Claude okumaz.

## Risk neden demo bakiyesinden hesaplanmıyor?

Demo hesapta 10.000 ya da 100.000 sahte USDT olabilir. Pozisyon o bakiyeden hesaplansaydı her işlem çok büyür ve sonuçlar bizim 1000 USDT'lik planımızla karşılaştırılamazdı.

- Defter **1000 USDT** ile başlar (`RESEARCH_EQUITY`) ve sadece gerçek dolumlarla değişir.
- Pozisyon = defter sermayesi × %1 / %8 (en fazla %25) × VolTarget katsayısı, **ve** demo hesaptaki serbest USDT'yi geçemez. Büyük bakiye pozisyonu büyütemez, küçük bakiye ise sınırlar.
- Kill switch defterin gerçekleşmiş kârına/zararına bakar. Yani demo emirlerinin gerçek sonuçlarını ölçer.

## Tekrar oynatma (replay) kontrolü: demo döngüsü = backtest edilen kural mı?

`python3 scripts/ft.py replay --slice fresh|validation`: Sahte bir borsa (`ReplayExchange`), indirilmiş gerçek 1 saatlik mumları saat saat veriyor. `demo.step` sanki Binance'teymiş gibi çalışıyor. LIMIT emir, bir sonraki mumun aralığı fiyata değerse doluyor. Sonuç Freqtrade'in TrendEmaVolTarget backtest'iyle (kill switch kapalı) işlem işlem karşılaştırılıyor.

İlk ölçüm 79 fazla işlem gösterdi. Nedenleri tek tek bulundu ve mini bot Freqtrade'in **zaten uyguladığı** kurallara eşitlendi (yeni kural yok):

| Fark | Kanıt | Düzeltme |
|---|---|---|
| En fazla 3 açık işlem yoktu | 79 fazlanın 75'i: o saatte Freqtrade'de 3 işlem açıktı | `paper.MAX_OPEN_TRADES = 3` |
| 2 saat bekleme (CooldownPeriod) yoktu | 3 fazla işlem | `paper.after_close` → `cooldown`; kilit bitiş saatini de kapsar |
| 3 stop / 24 saat → 12 saat ara (StoplossGuard) yoktu | kural eşitliği | `guard_until` |
| Aynı saatte satış ve alış varsa Freqtrade önce satar | 2025-07-22: ETH satıldı, BTC girdi | her saatte önce çıkışlar, sonra girişler |
| Stop, stop fiyatında LIMIT idi; fiyat altına düşünce dolmuyordu | bir ETH stop'u 2 gün geç doldu | stop = son kapanışın %1 altında LIMIT (hemen dolar, ama sınırsız fiyata değil) |

Sonuç (2026-11-01):
- **fresh:** 17/17 işlem aynı saatte girip aynı saatte çıktı.
- **validation:** 217/217 giriş aynı saatte. 7 çıkış farkı: 5 stop 1 saat sonra (mini bot düşük fiyatı ancak mum kapanınca görür; backtest mumun içinde stop fiyatından çıkar) ve 2 işlem dönem sonunda açık (backtest dönem sonunda zorla kapatır).
- Pozisyon boyutu farkı ortanca %1-2. Freqtrade sermayenin %99'u üzerinden hesaplar (tradable_balance_ratio).
- Kâr/zarar farkı: fresh 0,39 USDT; validation +11,65 USDT (%4). Bunun +6,49'u boyut farkından, +5,15'i 1 saat geç stop'tan geliyor. Geç stop bu sefer şans eseri iyi çıktı (fiyat sıçradı); gerçek bir çöküşte kötü olabilir.

Yavaş test: `FTLAB_SLOW=1 python3 scripts/ft.py test tests/test_replay.py` (normalde atlanır).

## Hâlâ bilinenler (ilk demo çalıştırmasından önce bilinmeli)

- Stop, saatlik turda kontrol ediliyor: düşük fiyat ancak mum kapanınca görülüyor, yani stop en fazla ~1 saat gecikebilir. Backtest'te bu gecikme yok.

- Emir beklerken (en fazla 10 dakika) bot diğer coinlere geçmez. Saatte bir çalışan bot için sorun değil, ama 5 coin üst üste beklerse tur uzar.
- BNB ile ödenen komisyon USDT'ye çevrilmiyor; demo hesapta "BNB ile komisyon öde" kapalı tutulmalı.

## Testler (`tests/test_minibot_demo.py`, sahte borsa, ağ yok, gerçek anahtar yok)

- Anahtar eksik → başlamaz (4 farklı eksiklik).
- Canlı adres, tek bir canlı adres, benzer görünen adres, testnet adresi, boş adres → başlamaz.
- Spot olmayan ayar → başlamaz.
- Emir: tip `limit`, yön, yuvarlanmış miktar/fiyat, `GTC`; vadeli işlem sembolü reddedilir.
- `demo.step` VolTarget boyutunu gönderiyor ve dolumu deftere yazıyor.
- Kısmi dolum + zaman aşımı → iptal, deftere sadece dolan kısım; hiç dolmayan emir → iptal, defter değişmiyor.
- Komisyon coinden kesilince pozisyon küçülüyor.
- Büyük demo bakiyesi pozisyonu büyütmüyor; küçük bakiye sınırlıyor.
- Kısmi satışta kalan pozisyon açık kalıyor; kill switch defterden ölçüyor.
- `execution.py` demo kayıtlarını okuyor.
- Gerçek ccxt nesnesi de (ağsız) kontrolü geçiyor.
- `preflight.py`: anahtarlar sadece ortamdan mı, adres kontrolü var mı, demo kaydı git'e girmiyor mu.

## Anlaman gerekenler

- **Kontrol, tehlikeli işlemden önce yapılır.** Adres yanlışsa bot bakiye bile sormadan durur. "Sonra fark ederiz" yok.
- **Karar ile uygulama ayrı.** `demo.step` kararı kağıt botla aynı fonksiyonlarla verir (`signals.signal`, `signals.vol_scale`, `paper.stake_for`), `DemoBroker` sadece uygular ve sonucu okur. Böylece kağıt ve demo aynı kuralı oynar; farkı sadece borsa yaratır. Ölçmek istediğimiz de bu fark.
- **"Gönderildi" ≠ "doldu".** Defter emri gönderdiğimizde değil, borsa doldurduğunu söylediğinde değişir. Kısmi dolum ve iptal bu yüzden doğru sayılır.
- **Benzer görünen adres saldırısı:** `demo-api.binance.com.evil.io` metin olarak "demo-api.binance.com" içerir ama başka bir sitedir. Bu yüzden adres metinde aranmıyor, **host** (alan adı) ayrıştırılıp karşılaştırılıyor.

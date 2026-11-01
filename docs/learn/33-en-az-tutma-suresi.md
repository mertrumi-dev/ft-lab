# Öğretici kart 33: En az tutma süresi (T106, MinHold24)

## Sorun: kısa işlemler para kaybettiriyor

Her işlem iki kez komisyon öder: alırken %0,15, satarken %0,15. Yani gidiş-dönüş **%0,30**. Bot ne kadar çok kısa işlem yaparsa bu maliyet o kadar birikir.

`python3 scripts/ft.py durations` mevcut backtest sonuçlarını tutma süresine göre ayırır (yeni test koşmaz). VolTarget, train dilimi (2021-01 → 2024-06), 5 coin:

| Tutma süresi | İşlem | Kazanan | Kâr/zarar (USDT) | Komisyon |
|---|---|---|---|---|
| 6 saatten kısa | 54 | %0 | -191 | 24 |
| 6-24 saat | 144 | %0 | -702 | 73 |
| 1-3 gün | 245 | %13 | -812 | 128 |
| 3-7 gün | 153 | %83 | +1039 | 76 |
| 1-2 hafta | 38 | %100 | +1385 | 21 |
| 2 haftadan uzun | 4 | %100 | +410 | 2 |

1 günden kısa süren **198 işlemin hiçbiri kazanmadı** (-893 USDT). Kâr, birkaç gün süren trendlerden geliyor. Yeni coin grubunda (alt2024b) da aynı desen var: komisyon, kaybın üçte ikisi.

**Dikkat: bu tablo sonuca göre ayrılmış (taraflı).** Kötü giden bir işlem zaten çabuk biter: EMA kesişmesi hemen geri döner ya da stop çalışır. Yani "kısa işlemler hep kaybediyor" büyük ölçüde "kaybeden işlemler kısa sürüyor" demek. Bu tablo, **daha uzun tutsaydık kazanırdık** sonucunu kanıtlamaz. Bunu sadece kuralı gerçekten deneyen backtest cevaplar (aşağıda).

## Fikir: sinyalle satış için en az 1 gün bekle

`TrendEmaVolTargetMinHold24` (`user_data/strategies/sizing.py`):

1. İşlem **24 mumdan (1 gün)** gençse, "EMA20 aşağı kesti" satış sinyali **reddedilir** (`confirm_trade_exit` → `False`).
2. 24 mum dolunca, EMA20 hâlâ EMA50'nin altındaysa bot çıkar (`custom_exit` → `"ema_below_after_minhold"`). Neden gerekli: kesişme bir kez olur. Reddedilen sinyal geri gelmez, bu yüzden "hâlâ altında mı" diye durumu kontrol ediyoruz.
3. **-%8 stop asla beklemez.** Stop, R1 risk kuralı: bir işlem en fazla sermayenin %1'ini kaybettirebilir. Bekleme sadece sinyal çıkışı için.

24 neden: doğal bir birim (1 gün), sonuca bakılarak seçilmedi. Önce ön kayıt yapıldı (journal + trials.csv T106), sonra test.

## Neden stop beklemiyor?

En az tutma süresi, "fiyat biraz geri döndü, belki trend devam eder" diye sabretmek demek. Ama fiyat sert düşüyorsa (-%8) bu artık sabır değil, kayıp. Sinyal çıkışı ile stop farklı işler yapıyor:

| | Sinyal çıkışı | Stop |
|---|---|---|
| Ne zaman | trend dönüşü (EMA kesişmesi) | fiyat girişin %8 altında |
| Amaç | kârı korumak / trendin bittiğini kabul etmek | büyük kaybı sınırlamak |
| Bekleyebilir mi | evet (bu deneme) | **hayır** (risk kuralı) |

## Ölçüt (sonuçtan önce yazıldı)

VolTarget ile karşılaştırma, kill switch kapalı, komisyon %0,15:
- train (5 coin) Calmar daha yüksek, **ve**
- yeni coinlerde (alt2024b) Calmar daha yüksek ve düşüş daha büyük değil, **ve**
- 2018-2020'de (early) Calmar en az VolTarget'in %90'ı,
- her birinde en az 50 işlem; ünlü botlar aynı tabloda.

## Anlaman gerekenler

- **Maliyeti işlem sayısı belirler.** Kural doğru olsa bile çok sık işlem komisyonda erir.
- **Kod hangi olayı yakalar, hangisini kaçırır?** Kesişme tek bir anda olur. Onu reddedersen geri gelmez; bu yüzden "durum" (hâlâ altında mı) kontrolü eklendi.
- **Güvenlik kuralları denemelerle gevşetilmez.** Stop her denemede aynen kalır; deneme sadece güvenlik dışındaki kısmı değiştirir.

## Sonuç (2026-11-01): BAŞARISIZ

| | VolTarget | MinHold24 |
|---|---|---|
| Train (5 coin) Calmar / düşüş | 1,86 / %13,2 | **1,50** / %14,9 |
| Yeni coinler (alt2024b) | -0,46 / %14,6 | -0,35 / **%14,7** |
| 2018-2020 (early) | 2,46 / %9,6 | **1,75** / %10,5 |
| Komisyon (train) | 323,6 USDT | 296,8 USDT |
| Komisyonsuz kâr (train) | +1.451,9 | +1.297,8 |

Komisyon azaldı ama kazanç daha çok azaldı. Kötü giden işlemleri 1 gün daha tutmak, kayıplarını büyüttü. Yukarıdaki "kısa işlemler hep kaybediyor" tablosu bu yüzden yanıltıcıydı: işlem kötü gittiği için kısa sürüyordu, kısa sürdüğü için kötü gitmiyordu. **Sebep ile sonucu karıştırmamak için kuralı gerçekten denemek gerekir.**

# Öğretici kart 31: Mini bot artık VolTarget kuralıyla çalışıyor

## Ne değişti?

Bu akşamdan sonra Freqtrade botu TrendEma yerine **TrendEmaVolTarget** ile çalışacak. Kendi yazdığımız mini bot (`minibot/`, kart 16) aynı kuralı oynasın diye pozisyon boyutu ona da eklendi:

```
pozisyon = normal pozisyon × min(1, %60 / coinin yıllık oynaklığı)
```

- **Normal pozisyon:** sermaye × %1 / %8 (stop'a çarparsa en fazla %1 kayıp), en fazla sermayenin %25'i. Bu kısım aynı.
- **Oynaklık:** son 720 saatlik (30 gün) getirinin standart sapması × √(8760). 8760 = bir yıldaki saat sayısı.
- Katsayı en fazla 1. Sakin coinde normal boyut, oynak coinde daha küçük boyut. Asla büyütmez, risk kuralları (R2, R4) korunur.

Çalıştırma:

```
.venv/bin/python -m minibot.bot --once                 # VolTarget (varsayılan)
.venv/bin/python -m minibot.bot --once --rule trendema # eski hali, hep normal boyut
```

## Kod nerede?

| Yer | Görevi |
|---|---|
| `signals.realized_vol(closes)` | Son 721 kapanıştan 720 log getiri; örneklem standart sapması (n−1'e böler, pandas'ın `std()`'si gibi) × √8760. Yeterli veri yoksa NaN. |
| `signals.vol_scale(vol)` | min(1, 0,60 / vol). NaN gelirse 1 (TrendEma gibi davranır). |
| `paper.stake_for(acc, prices, scale)` | Normal pozisyonu katsayıyla çarpar, sonra elde olan nakitle sınırlar. |
| `bot.step(..., rule=...)` | Alım sinyalinde, kural `voltarget` ise katsayıyı hesaplayıp `paper.buy`'a verir. |

Mini bot artık her coin için son **1000** mumu istiyor (eskiden 500). Oynaklık 721 kapanış istiyor; Binance tek çağrıda en fazla 1000 veriyor.

## Eşlik testi (parity)

`tests/test_minibot.py::test_voltarget_parity_with_the_freqtrade_strategy` aynı mum verisini iki koda verir:

1. Freqtrade stratejisi: `populate_indicators` → `populate_entry_trend` → `populate_exit_trend`, sonra `custom_stake_amount`.
2. Mini bot: `signals.signal`, `signals.realized_vol`, `paper.stake_for`.

Her saat için alım/satım sinyali aynı olmalı. Her alımda ve her 50 saatte bir de pozisyon tutarı aynı olmalı. Veri bilerek iki parçalı: önce sakin (katsayı 1), sonra oynak (katsayı < 0,8). Böylece iki durum da kontrol ediliyor.

## Anlaman gerekenler

- **Aynı kural, iki ayrı kod:** Biri kütüphane (Freqtrade + pandas), biri düz Python. Eşlik testi ikisinin aynı kararı verdiğini kanıtlar. Biri değişip diğeri unutulursa test kırılır.
- **Atlanan test geçmiş sayılmaz:** İlk denemede bir test "alım sinyali bulunamadı" diye atlandı (SKIPPED). Rastgele veri yerine, sinyal üreten pencereyi kesin olarak seçen bir yöntemle düzeltildi.
- **Standart sapmada n−1:** pandas `std()` örneklem formülünü kullanır. Python'da da aynısı `statistics.stdev`; `pstdev` (n'e böler) farklı sonuç verirdi.

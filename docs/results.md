# Sonuçlar

Her satırın komutu ve tam timerange'i yazılı. Sayılar süslenmez.

## 2026-10-31 · Train dilimi · 5 strateji (deneme #1-5)

Komut (Kaan'ın Mac'i):
```
python3 scripts/ft.py backtest --slice train --strategy all
python3 scripts/ft.py report --slice train
```
`--timerange 20210101-20240613`, `--fee 0.0015` (her yön), `--enable-protections`, başlangıç 1000 USDT, 5 pair (BTC, ETH, SOL, BNB, XRP / USDT).

| Strateji | İşlem | Getiri | Yıllık (CAGR) | En büyük düşüş | Calmar | Kazanma % | Profit factor | Karar |
|---|---|---|---|---|---|---|---|---|
| **Al-tut** (eşit ağırlık) | - | +2426,5% | +155,4% | 92,1% | 1,69 | - | - | referans |
| **TrendEma** | 638 | +254,3% | +44,3% | 14,8% | 2,99 | 31% | 1,63 | PASS |
| TrendEma4h | 87 | +103,1% | +22,8% | 20,1% | 1,13 | 26% | 1,97 | FAIL (Calmar) |
| TrendBreakout | 321 | +93,5% | +21,1% | 20,5% | 1,03 | 32% | 1,42 | FAIL (Calmar) |
| TrendEmaAtr | 758 | +42,7% | +10,9% | 17,3% | 0,63 | 34% | 1,15 | FAIL (Calmar) |
| TrendEmaAtrTrail | 731 | +43,1% | +10,9% | 17,6% | 0,62 | 35% | 1,15 | FAIL (Calmar) |

### Yorum

- **TrendEma train'de başarı kuralını geçti:** Calmar 2,99 > al-tut 1,69; düşüş %14,8 < al-tut'un yarısı (%46); 638 işlem.
- **Ham getiride al-tut çok önde** (+2426% vs +254%). Bu dönem kriptonun en büyük yükselişini (2021) içeriyor; özellikle SOL ~100 kat arttı. Ama al-tut bir noktada %92 düşüş yaşattı: 1000 USDT ~80 USDT'ye inmiş olurdu.
- **ATR stop fikri bu haliyle başarısız.** 1 saatlik mumda 2,5×ATR çok dar (~%2-3); bot normal dalgalanmada stop olup trende tekrar giriyor. Fikir çöpe değil ama bu parametrelerle değil.
- **4h ve kırılım** daha az ve daha seçici işlem yaptı ama getiri/düşüş oranı daha kötü.

### Dikkat (sayıların sınırları)

- Strateji düşüşü Freqtrade'in **kapanmış işlemler** üzerinden hesapladığı hesap düşüşü; açık işlemin işlem içindeki geçici düşüşü sayılmıyor. Al-tut düşüşü saatlik fiyattan. Yani stratejinin gerçek düşüşü bir miktar daha yüksek olabilir. Faz 3'te saatlik bakiye eğrisiyle yeniden ölçülecek.
- Kazanma oranı %31: işlemlerin 3'te 2'si zararla kapanıyor, kâr az sayıda büyük kazançtan geliyor. Trend takibinde normal ama psikolojik olarak zor.
- Bu **train** sonucu. Asıl soru validation diliminde de tutup tutmadığı.

Deneme sayacı: train 5 strateji (1 çalıştırma). Validation 0. Test 0.

## 2026-10-31 · Validation dilimi · TrendEma (validation bakışı #1)

Komut: `python3 scripts/ft.py backtest --slice validation --strategy TrendEma` + `report --slice validation`
`--timerange 20240613-20250807`, `--fee 0.0015`, `--enable-protections`.

| Strateji | İşlem | Getiri | Yıllık | En büyük düşüş | Calmar | Kazanma % | PF | Karar |
|---|---|---|---|---|---|---|---|---|
| Al-tut | - | +122,6% | +100,9% | 47,8% | 2,11 | - | - | referans |
| TrendEma | 217 | +31,4% | +26,8% | 14,1% | 1,90 | 33% | 1,62 | FAIL (Calmar) |

### Yorum

- **Kıl payı geçemedi:** Calmar 1,90 vs al-tut 2,11. Düşüş ve işlem sayısı şartları geçiyor.
- **İyi işaret:** Profit factor (kazanılan / kaybedilen para) train'de 1,63, burada 1,62. Kural yeni dönemde de aynı "kalitede" çalışıyor; ezberlemiş gibi görünmüyor.
- **Sorun:** Bu dönemde al-tut daha az acılı geçti (düşüş %48, train'de %92), bu yüzden bizim "az acı" avantajımız küçüldü.
- Kural: train'de geçip validation'da geçemeyen strateji canlıya geçmez. TrendEma canlıda sahte parayla çalışmaya devam ediyor (zararı yok), ama "kazanan" ilan edilmedi.

Deneme sayacı: train 5, validation 1, test 0.

## 2026-10-31 · Train dilimi · Tur 2 (deneme #6-9)

Komut: `python3 scripts/ft.py backtest --slice train --strategy TrendEma TrendEmaAtrWide TrendEmaSlow TrendEmaMulti TrendEmaBtc` + `report --slice train`
`--timerange 20210101-20240613`, `--fee 0.0015`, `--enable-protections`. (TrendEma tekrar çalıştı, sonuç aynı: 2,99.)

| Strateji | İşlem | Getiri | Yıllık | En büyük düşüş | Calmar | Kazanma % | PF | Karar |
|---|---|---|---|---|---|---|---|---|
| Al-tut | - | +2426,5% | +155,4% | 92,1% | 1,69 | - | - | referans |
| TrendEma | 638 | +254,3% | +44,3% | 14,8% | 2,99 | 31% | 1,63 | PASS |
| TrendEmaSlow | 215 | +227,6% | +41,1% | 14,5% | 2,83 | 30% | 2,08 | PASS |
| TrendEmaBtc | 523 | +104,2% | +23,0% | 13,0% | 1,76 | 31% | 1,52 | PASS (kıl payı) |
| TrendEmaMulti | 165 | +167,0% | +32,9% | 20,3% | 1,62 | 22% | 1,87 | FAIL (Calmar) |
| TrendEmaAtrWide | 502 | +119,3% | +25,6% | 20,1% | 1,27 | 31% | 1,33 | FAIL (Calmar) |

### Yorum

- **Hiçbiri ana kuralı (TrendEma) geçemedi.**
- **TrendEmaSlow en yakın aday:** Calmar 2,83 (ana kural 2,99). İşlem sayısı 3'te 1'e indi (215 vs 638). Profit factor (kazanılan para / kaybedilen para) çok daha yüksek: 2,08 vs 1,63. Yani daha az ama daha kaliteli işlem yapıyor, daha az komisyon ödüyor.
- **BTC filtresi** düşüşü azalttı (%13,0) ama kazancın yarısını da kesti. Al-tut'u kıl payı geçiyor, zayıf.
- **ATR stop'u genişletmek** (2,5× → 5×) Calmar'ı 0,63'ten 1,27'ye çıkardı ama yetmedi. 1 saatlik grafikte ATR stop fikri şimdilik bırakıldı.

Karar: validation'a sadece TrendEmaSlow girecek (validation bakışı #2). Diğerleri elendi.

Deneme sayacı: train 9, validation 1, test 0.

## 2026-11-01 · Validation dilimi · TrendEmaSlow (validation bakışı #2)

Komut: `python3 scripts/ft.py backtest --slice validation --strategy TrendEmaSlow` + `report --slice validation`
`--timerange 20240613-20250807`, `--fee 0.0015`, `--enable-protections`.

| Strateji | İşlem | Getiri | Yıllık | En büyük düşüş | Calmar | Kazanma % | PF | Karar |
|---|---|---|---|---|---|---|---|---|
| Al-tut | - | +122,6% | +100,9% | 47,8% | 2,11 | - | - | referans |
| **TrendEmaSlow** | 71 | +38,0% | +32,3% | 9,7% | **3,32** | 32% | 2,07 | **PASS** |
| TrendEma (#1'den) | 217 | +31,4% | +26,8% | 14,1% | 1,90 | 33% | 1,62 | FAIL |

### Yorum

- **İlk kez bir strateji hem train'de hem validation'da başarı kuralını geçti.**
- **Tutarlılık güçlü işaret:** PF train'de 2,08, validation'da 2,07. Kural yeni dönemde aynı kalitede çalıştı.
- **Dikkat 1:** 71 işlem. 50 sınırının üstünde ama az. Tek bir şanslı işlem sonucu çok etkileyebilir.
- **Dikkat 2:** Düşüş kapanmış işlemlerden hesaplanıyor (iyimser). Faz 3'te saatlik bakiye ile yeniden ölçülecek.
- **Dikkat 3:** Slow, validation #1'i gördükten sonra yazılan 4 fikirden biri. Hafif "seçim şansı" payı var; bu yüzden sayı sağlamlığı (komşu sayılar) testi yapılıyor.

Sıradaki: sayı sağlamlığı (sadece train'de), sonra TrendEmaSlow dry-run'a geçer. Final sınavı (test) Faz 3 bitince, bir kere.

Deneme sayacı: train 9, validation 2, test 0.

## 2026-11-01 · Train dilimi · TrendEmaSlow sayı sağlamlığı (deneme #10-15)

Komut: `python3 scripts/ft.py backtest --slice train --strategy TrendEmaSlow SlowFast40 SlowFast60 SlowSlow150 SlowSlow250 SlowTrend450 SlowTrend750` + `report --slice train`
`--timerange 20210101-20240613`, `--fee 0.0015`, `--enable-protections`. (TrendEmaSlow startup 1500 ile yeniden: sonuç aynı, 2,83.)

| Strateji (hızlı/yavaş/trend) | İşlem | Getiri | Düşüş | Calmar | PF | Karar |
|---|---|---|---|---|---|---|
| Al-tut | - | +2426,5% | 92,1% | 1,69 | - | referans |
| SlowTrend450 (50/200/**450**) | 244 | +314,2% | 13,8% | 3,69 | 2,24 | PASS |
| SlowSlow250 (50/**250**/600) | 189 | +265,3% | 15,1% | 3,02 | 2,31 | PASS |
| SlowFast60 (**60**/200/600) | 200 | +240,9% | 14,4% | 2,96 | 2,11 | PASS |
| **TrendEmaSlow (50/200/600)** | 215 | +227,6% | 14,5% | 2,83 | 2,08 | PASS |
| SlowFast40 (**40**/200/600) | 249 | +199,8% | 16,6% | 2,25 | 1,95 | PASS |
| SlowTrend750 (50/200/**750**) | 201 | +197,8% | 20,1% | 1,85 | 2,02 | PASS |
| SlowSlow150 (50/**150**/600) | 160 | +119,0% | 20,4% | 1,25 | 1,76 | FAIL |

### Yorum

- **Büyük ölçüde sağlam:** 6 komşunun 5'i başarı kuralını geçti; hepsi kârlı, PF hepsinde 1,76 veya üstü. Asıl strateji ortada bir yerde, "tek şanslı nokta" değil.
- **Zayıf taraf:** yavaş ortalamayı 150'ye indirmek Calmar'ı 1,25'e düşürdü. Yani kural "çok hızlı" tarafa kayınca bozuluyor; yavaş taraf daha güvenli. Trend 750 de zayıfladı (1,85).
- **Seçim yapmıyoruz:** SlowTrend450 en iyisi ama ona geçmek ezberleme olur. TrendEmaSlow (50/200/600) kalıyor.

Deneme sayacı: train 15, validation 2, test 0.

## 2026-11-01 · Train · Sağlamlık: başka coinler + 2 kat komisyon

### A) 2021'in büyük coinleri (`--universe wide`, 14 coin; EOS verisi yok, atlandı)

Komut: `python3 scripts/ft.py backtest --slice train --universe wide --strategy TrendEma TrendEmaSlow` + `report --slice train --universe wide`
`--timerange 20210101-20240613`, `--fee 0.0015`, `--enable-protections`.

| Strateji | İşlem | Getiri | Yıllık | Düşüş | Calmar | PF | Karar |
|---|---|---|---|---|---|---|---|
| Al-tut (14 coin) | - | +256,3% | +44,6% | 90,6% | 0,49 | - | referans |
| TrendEma | 149 | +181,8% | +35,0% | 20,1% | 1,75 | 2,09 | PASS |
| TrendEmaSlow | 98 | +115,2% | +24,9% | 20,6% | 1,21 | 1,86 | PASS |

- İkisi de hiç görmedikleri coinlerde al-tut'u açık farkla geçti (Calmar 1,75 ve 1,21 vs 0,49). Kural, coin seçme şansına dayanmıyor gibi.
- **Şüphe:** iki düşüş de %20'nin hemen üstünde ve işlem sayısı düşük. Bu, kill switch'in (%20 düşüşte alımı durdurma) tetiklendiğini ve botun dönemin bir kısmında hiç işlem yapmadığını gösterebilir. Kanıt için rapora "son işlem tarihi" sütunu eklendi. Kontrol edilecek.
- Aynı şüphe tur 1-2'de düşüşü %20,1-20,6 çıkan FAIL'ler için de geçerli (TrendEma4h, TrendBreakout, TrendEmaAtrWide, TrendEmaMulti, SlowSlow150, SlowTrend750).

### B) 2 kat komisyon (`--fee-stress`, her yön %0,3), ana 5 coin

Komut: `python3 scripts/ft.py backtest --slice train --fee-stress --strategy TrendEma TrendEmaSlow` + `report --slice train --fee-stress`

| Strateji | İşlem | Getiri | Yıllık | Düşüş | Calmar | PF | Karar | (normal komisyonda Calmar) |
|---|---|---|---|---|---|---|---|---|
| Al-tut | - | +2422,7% | +155,3% | 92,1% | 1,69 | - | referans | 1,69 |
| TrendEmaSlow | 215 | +202,7% | +37,9% | 17,4% | 2,18 | 1,93 | PASS | 2,83 |
| TrendEma | 638 | +179,9% | +34,8% | 17,6% | 1,97 | 1,45 | PASS | 2,99 |

- İkisi de 2 kat komisyonda ayakta. Slow daha az etkilendi (az işlem yaptığı için): Calmar 2,83 → 2,18; TrendEma 2,99 → 1,97.

Deneme sayacı (sağlamlık çalıştırmaları seçim için kullanılmadı): train 15 + 4 sağlamlık, validation 2, test 0.

## 2026-11-01 · Önemli düzeltme: kill switch backtest'leri yarıda kesti

`report` ile "Last trade" sütunu eklendi (komut: `ft.py report --slice train` ve `--universe wide`). Düşüşü ~%20 olan sonuçlarda son işlem tarihi dönem sonundan çok önce:
- 14 coin: TrendEma son işlem 2021-07-12, TrendEmaSlow 2022-02-18.
- 5 coin: TrendEmaMulti 2022-06-07, TrendBreakout 2022-06-10, TrendEma4h 2023-03-03, SlowSlow150 2023-05-01, TrendEmaAtrWide 2023-09-27.

Sonuç: bu satırlar "kural 3,5 yılda nasıl" değil "ilk %20 düşüşe kadar nasıl" ölçüyor. 14 coin PASS'i ve bu FAIL'ler **kesin değil**. TrendEma, TrendEmaSlow ve sayı komşularının çoğu (5 coin) dönem sonuna kadar işlem yaptı; onların sonuçları geçerli.

Çözüm: araştırma backtest'i için `--no-kill-switch` (bkz. risk-rules.md). Yeniden ölçülecek.

## 2026-11-01 · Train · Kill switch KAPALI yeniden ölçüm (araştırma)

Komut: `python3 scripts/ft.py backtest --slice train --no-kill-switch --strategy all` ve `... --universe wide --strategy TrendEma TrendEmaSlow`, sonra `report --slice train --no-kill-switch [--universe wide]`
`--timerange 20210101-20240613`, `--fee 0.0015`, `--enable-protections`, `research-no-kill-switch.json`.

### A) Ana 5 coin

| Strateji | İşlem | Getiri | Düşüş | Calmar | PF | Karar | (kill switch açıkken) |
|---|---|---|---|---|---|---|---|
| Al-tut | - | +2426,5% | 92,1% | 1,69 | - | referans | |
| TrendEma | 638 | +254,3% | 14,8% | 2,99 | 1,63 | PASS | aynı |
| TrendEmaSlow | 215 | +227,6% | 14,5% | 2,83 | 2,08 | PASS | aynı |
| TrendEmaMulti | 410 | +339,4% | 23,2% | 2,31 | 1,87 | PASS | 1,62 FAIL |
| TrendEmaAtrWide | 662 | +195,1% | 20,5% | 1,79 | 1,40 | PASS | 1,27 FAIL |
| TrendEmaBtc | 523 | +104,2% | 13,0% | 1,76 | 1,52 | PASS | aynı |
| TrendEma4h | 162 | +204,3% | 23,6% | 1,61 | 2,24 | FAIL | 1,13 |
| TrendBreakout | 753 | +163,3% | 21,9% | 1,48 | 1,37 | FAIL | 1,03 |
| TrendEmaAtr / AtrTrail | ~750 | +43% | ~17% | 0,63 | 1,15 | FAIL | aynı |

### B) 2021'in 14 coini (wide)

| Strateji | İşlem | Getiri | Düşüş | Calmar | PF | Karar | (kill switch açıkken) |
|---|---|---|---|---|---|---|---|
| Al-tut | - | +256,3% | 90,6% | 0,49 | - | referans | |
| TrendEma | 949 | +156,5% | 37,7% | 0,83 | 1,20 | PASS (zayıf) | 1,75 (Temmuz 2021'de durmuştu) |
| TrendEmaSlow | 322 | +72,3% | 41,8% | 0,41 | 1,23 | **FAIL** | 1,21 (Şubat 2022'de durmuştu) |

### Yorum (dürüst)

- **Ana 5 coinde TrendEma ve Slow hiç kill switch'e çarpmamış; sonuçları geçerli.**
- **Multi, kill switch olmadan güçlü** (Calmar 2,31) ama düşüşü %23: canlıda kill switch onu durdururdu.
- **Başka coinlerde tablo kötüleşiyor:** iki kuralın da düşüşü ~%40, PF ~1,2. Slow al-tut'u bile geçemiyor. Kill switch açıkken görünen "PASS", botun 2022 çöküşünü tesadüfen nakitte geçirmesinden geliyordu.
- **Anlamı:** Slow'un üstünlüğü büyük ölçüde ana 5 coine özgü olabilir. Hiçbir kural henüz "her yerde sağlam" değil. Altcoinlerde 2022 düşüşü EMA200 filtresine rağmen kuralı çok yaralıyor.
- **Karar:** Dry-run'da TrendEmaSlow'a geçiş **ertelendi**; TrendEma (zaten çalışıyor) kalıyor. Kanıt iki taraflı: Slow validation'da daha iyi, TrendEma başka coinlerde daha iyi.

Deneme sayacı: train 15 (+ 4 sağlamlık + 11 kill-switch'siz yeniden ölçüm), validation 2, test 0. Wide dilimi artık "görüldü": buna bakıp yeni kural yazarsak wide da ezberlenmeye başlar.

## 2026-11-01 · Train · 14 coin · BTC filtresi (kill switch kapalı, deneme: wide #3)

Komut: `python3 scripts/ft.py backtest --slice train --no-kill-switch --universe wide --strategy TrendEmaBtc` + `report --slice train --no-kill-switch --universe wide`
`--timerange 20210101-20240613`, `--fee 0.0015`, `--enable-protections`.

| Strateji | İşlem | Getiri | Yıllık | Düşüş | Calmar | PF | Karar |
|---|---|---|---|---|---|---|---|
| Al-tut (14 coin) | - | +256,3% | +44,6% | 90,6% | 0,49 | - | referans |
| TrendEmaBtc | 677 | +82,2% | +19,0% | 21,0% | 0,90 | 1,27 | PASS (zayıf) |
| TrendEma | 949 | +156,5% | +31,4% | 37,7% | 0,83 | 1,20 | PASS (zayıf) |
| TrendEmaSlow | 322 | +72,3% | +17,1% | 41,8% | 0,41 | 1,23 | FAIL |

### Yorum

- **Hipotez doğrulandı, ama bedeli var.** BTC filtresi zayıf coinlerde düşüşü %37,7'den %21,0'a indirdi (neredeyse yarıya). Ama kazanç da yarıya indi (+156% → +82%).
- Ana 5 coinde aynı filtre Calmar'ı 2,99'dan 1,76'ya düşürmüştü. Yani güçlü coinlerde filtre fazla temkinli, zayıf coinlerde işe yarıyor.
- Hiçbir kural 14 coinde güçlü değil (Calmar < 1, PF ~1,2). Kuralın gerçek avantajı güçlü coinlerde.
- Karar: canlı kural değişmiyor (TrendEma). Yeni kural denemesine ara; şimdi yıl yıl analiz (hangi piyasa havasında kazanıp kaybediyor).

## 2026-11-01 · Train · Yıl yıl (eski sonuçların kırılımı, yeni deneme değil)

Komut (Remote Control ile Kaan'ın Mac'inde): `python3 scripts/ft.py report --slice train --by-year --strategy TrendEma TrendEmaSlow TrendEmaBtc` ve aynısı `--no-kill-switch --universe wide`. `--timerange 20210101-20240613`, `--fee 0.0015`. Strateji düşüşü sadece kapanmış işlemlerden (iyimser).

### Ana 5 coin

| Yıl | Al-tut | TrendEma | TrendEmaSlow | TrendEmaBtc |
|---|---|---|---|---|
| 2021 | +2582,2% (DD 60,7%) | +177,1% (9,8%) | +151,3% (8,9%) | +70,8% (10,3%) |
| 2022 | -87,7% (88,9%) | -1,5% (8,6%) | -3,6% (7,8%) | -7,9% (11,4%) |
| 2023 | +386,4% (36,0%) | +23,5% (8,7%) | +21,4% (6,7%) | +21,8% (9,3%) |
| 2024 (Haz'a kadar) | +54,4% (37,3%) | +5,1% (6,9%) | +11,4% (7,0%) | +6,6% (5,9%) |

### 14 coin (kill switch kapalı)

| Yıl | Al-tut | TrendEma | TrendEmaSlow | TrendEmaBtc |
|---|---|---|---|---|
| 2021 | +435,5% (73,9%) | +179,3% (22,4%) | +124,4% (16,8%) | +47,9% (13,1%) |
| 2022 | -66,9% (72,9%) | -15,7% (22,6%) | -19,6% (26,3%) | -7,6% (16,5%) |
| 2023 | +51,9% (36,8%) | +20,0% (13,6%) | -1,4% (14,4%) | +32,7% (8,8%) |
| 2024 | +30,5% (40,2%) | -9,2% (15,9%) | -3,1% (6,0%) | +0,5% (12,3%) |

### Yorum

- **Botun değeri çöküş yılında:** 2022'de al-tut -%88, TrendEma -%1,5.
- **Yükselişte al-tut'un çok gerisinde.** Kazancın büyük kısmı 2021'den. 2023-24'te al-tut'un küçük bir kesri.
- Muhtemel neden: %1 risk kuralı yüzünden paranın çoğu nakitte. Ölçmek için "ortalama yatırım oranı" ve saatlik (açık işlem dahil) düşüş ekleniyor.
- 14 coinde BTC filtresi 2022'yi -%7,6 ile en iyi geçiren kural.

## 2026-11-01 · Dürüst ölçüm: saatlik düşüş (açık işlemler dahil) ile yeniden rapor

Komut (RC, Kaan'ın Mac'i): `ft.py report --slice train`, `--no-kill-switch`, `--no-kill-switch --universe wide`, `report --slice validation`. Aynı backtest sonuçları; sadece ölçüm değişti (scripts/equity.py).

| Strateji | Dilim | Düşüş (kapanmış → saatlik) | Calmar (eski → yeni) | Paranın coinde olan kısmı | Karar |
|---|---|---|---|---|---|
| TrendEma | train | 14,8% → 16,5% | 2,99 → **2,69** | %16 | PASS |
| TrendEmaSlow | train | 14,5% → 22,6% | 2,83 → **1,82** | %15 | PASS |
| TrendEma | validation | 14,1% → 17,3% | 1,90 → **1,55** | %16 | FAIL (al-tut 2,11) |
| **TrendEmaSlow** | **validation** | 9,7% → 20,0% | 3,32 → **1,62** | %16 | **FAIL** (al-tut 2,11) |
| TrendEma | wide (kill kapalı) | 37,7% → 41,4% | 0,83 → 0,76 | %20 | PASS (zayıf) |
| TrendEmaBtc | wide (kill kapalı) | 21,0% → 25,6% | 0,90 → 0,74 | %15 | PASS (zayıf) |

### Yorum (dürüst)

- **TrendEmaSlow'un validation PASS'i ölçüm hatasıydı.** Slow uzun işlemde kalıyor; işlem açıkken yaşanan düşüşler eski ölçümde görünmüyordu. Saatlik ölçümde %20 düşüş, Calmar 1,62 → al-tut'un (2,11) altında.
- **Şu an hiçbir strateji train + validation'ı birlikte geçmiyor.** En iyi aday hâlâ TrendEma (train 2,69).
- **Paranın ortalama sadece %15-20'si coinde.** Yükselişte al-tut'un çok gerisinde kalmanın ana sebebi bu. Bu %1 risk kuralının sonucu; kural değişikliği Kaan'ın kararı.
- Ölçüm artık al-tut ile aynı cetvel. Bundan sonraki tüm kararlar buna göre.

## 2026-11-01 · Train · Tur 3: ADX ve uzun trend filtresi (kill switch kapalı, saatlik düşüş) (deneme train #16-17, wide #4-5)

Komut (RC): `ft.py backtest --slice train --no-kill-switch --strategy TrendEma TrendEmaAdx TrendEmaLongTrend` ve `--universe wide --strategy TrendEmaAdx TrendEmaLongTrend`; `report ... --by-year`. `--timerange 20210101-20240613`, `--fee 0.0015`.

| Strateji | 5 coin Calmar | 5 coin düşüş | 14 coin Calmar | 14 coin düşüş | Coinde |
|---|---|---|---|---|---|
| Al-tut | 1,69 | 92,1% | 0,49 | 90,6% | %100 |
| **TrendEma** | **2,69** | 16,5% | 0,76 | 41,4% | %16-20 |
| TrendEmaLongTrend | 2,25 | 16,2% | **0,98** | 34,7% | %11-15 |
| TrendEmaAdx | 1,28 (FAIL) | 15,5% | 0,84 | 40,5% | %11-16 |

- **İkisi de 5 coinde TrendEma'yı geçemedi.** Filtreler giriş sayısını azaltıp parayı daha çok nakitte tutuyor: düşüş pek azalmıyor, kazanç azalıyor.
- Uzun trend filtresi 14 zayıf coinde en iyisi (0,98, düşüş %41 → %35), ama 5 coinde kazancı kesiyor (2023: +%7,6 vs +%23,5).
- ADX 2022'de tek pozitif kural (+%3,7) ama yükseliş yıllarında çok geride.
- **Desen:** Giriş filtresi eklemek güçlü coinlerde hep kazancı kesiyor. Asıl kaldıraç (sözün gelişi) giriş değil, paranın ne kadarının coinde olduğu (%16). Bu risk kuralı → Kaan'ın kararı bekleniyor.

## 2026-11-01 · Train · %2 risk araştırması (TrendEmaRisk2, sadece backtest)

Komut (RC): `ft.py backtest --slice train [--no-kill-switch] --strategy TrendEmaRisk2`; `report --slice train [--no-kill-switch] --strategy TrendEma TrendEmaRisk2`. `--timerange 20210101-20240613`, `--fee 0.0015`.

| | Getiri | Yıllık | Düşüş (saatlik) | Calmar | Coinde | Not |
|---|---|---|---|---|---|---|
| TrendEma (%1) | +254,3% | +44,3% | 16,5% | 2,69 | %16 | |
| TrendEmaRisk2, kill switch kapalı | +876,4% | +93,6% | 30,6% | 3,06 | %30 | gerçek bot %20'de dururdu |
| TrendEmaRisk2, kill switch açık | +471,7% | +65,8% | 24,6% | 2,68 | %10 | 2022-01-21'de durdu |

- Riski 2 katına çıkarmak kazancı ve düşüşü birlikte büyütüyor; risk başına kalite (Calmar) neredeyse aynı.
- %20 kill switch ile birlikte %2 risk uyumsuz: bot Ocak 2022'de kalıcı duruyor.
- **Karar: canlı risk %1 kalıyor.** Daha fazla getiri, kuralın kendisini iyileştirerek aranacak, riski büyüterek değil.

## Araştırma notu: "Catching Crypto Trends" (Zarattini, Pagani, Barbon, 2025)

Kaynak: https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/ (makale PDF'i ve https://abarbon.com/papers/catching-crypto-trends özeti).
- Günlük mum, Donchian kırılımı; 9 farklı pencere (5-360 gün) eşit ağırlıklı topluluk (ensemble); çıkış: kanal ortasında, sadece yukarı kayan stop.
- Pozisyon: oynaklık hedefleme (yıllık %25 hedef, 90 günlük oynaklıkla), makalede %200'e kadar (bizde kaldıraç yok → tavan %100).
- Coin seçimi: her ay hacme göre ilk 20 (1 yıldan eski, stablecoin değil), hayatta kalan yanılgısından arındırılmış veri.
- Sonuç (makale, Tablo 4, %0,1 komisyon): ilk 20 coin portföyü yıllık %18, Sharpe 1,57, en büyük düşüş %11 (2015-2025). Backtest; bağımsız doğrulama yok.
- Bizim için çıkarım: (1) tek pencere yerine çok pencereli topluluk, (2) günlük mum, (3) oynaklığa göre pozisyon, (4) hacme göre aylık coin seçimi. Sıradaki deneme bunlardan.

## 2026-11-01 · Train · Tur 4: TrendDonchianEnsemble (günlük, 9 süre oylaması, oynaklık hedefleme)

Komut (RC): `ft.py backtest --slice train [--no-kill-switch] [--universe wide] --strategy TrendDonchianEnsemble` + `report`. `--timerange 20210101-20240613`, `--fee 0.0015`, `--timeframe 1d`.

| | İşlem | Getiri | Yıllık | Düşüş | Calmar | PF | Coinde | Karar |
|---|---|---|---|---|---|---|---|---|
| 5 coin | 104 | +31,5% | +8,3% | 14,1%* | 0,59 | **4,99** | %3 | FAIL |
| 14 coin (kill kapalı) | 160 | +3,8% | +1,1% | 7,9%* | 0,14 | 1,38 | %2 | FAIL |

\* Bu düşüş eski saatlik yöntemle hesaplandı. Eski yöntem pozisyon büyütme/küçültme olan işlemlerde yanlış (son adedi tüm süreye uyguluyor). Düzeltildi: `equity.build_curve` artık her emirden (order) hesaplıyor. Yeniden raporlanacak.

- **Kalite çok yüksek (PF 4,99) ama paranın sadece %3'ü coinde.** Sebep: %1 risk bütçesi (%12,5) × oy oranı × oynaklık ölçeği (~0,3) → coin başına ~%2-3. Bizim -%8 sabit stop zaten riski sınırladığı için oynaklık ölçeği pozisyonu ikinci kez küçültüyor.
- Sıradaki deneme (tek değişiklik): `TrendDonchianEnsembleFull` = oynaklık ölçeği yok, büyüklük = bütçe × oy oranı.

## 2026-11-01 · Train · Tur 4b ve 3b (kill switch kapalı, emirlerden kesin saatlik düşüş)

Komut (RC): `ft.py backtest --slice train --no-kill-switch [--universe wide] --strategy TrendDonchianEnsembleFull` (+ Mac dalında TrendEmaFng, TrendEmaCalm); `report ...`. `--timerange 20210101-20240613`, `--fee 0.0015`.

| Strateji | 5 coin Calmar | 5 coin düşüş | PF | Coinde | 14 coin Calmar | Karar |
|---|---|---|---|---|---|---|
| Al-tut | 1,69 | 92,1% | - | %100 | 0,49 | referans |
| **TrendEma** | **2,70** | 16,4% | 1,63 | %17 | 0,76 | PASS (en iyi) |
| TrendEmaLongTrend | 2,25 | 16,1% | 1,72 | %12 | **0,98** | PASS |
| TrendEmaCalm (oynaklık filtresi) | 1,95 | 17,1% | - | - | 0,74 | PASS, TrendEma'dan kötü |
| TrendEmaFng (korku-açgözlülük ≥75'te alma) | 1,48 | 14,4% | - | - | 0,27 | FAIL |
| TrendDonchianEnsembleFull | 1,46 | 15,8% | 4,18 | %13 | 0,30 | FAIL |
| TrendDonchianEnsemble | 0,50 | 16,4% | 4,99 | %6 | 0,14 | FAIL |

- Korku-açgözlülük filtresi en iyi trend günlerini (2021'deki aşırı açgözlülük) kaçırıyor: 2021'de +%60 vs TrendEma +%177. Trend takibine zararlı.
- Günlük oylama kuralı işlem kalitesinde çok iyi (PF 4-5) ama yükseliş yıllarında az kazanıyor; 2023'te +%2,5.
- Validation (kesin ölçüm): TrendEma 1,55, TrendEmaSlow 1,62, al-tut 2,11: ikisi de FAIL.

**Ara sonuç (22 train denemesi sonra):** 5 ana coinde TrendEma'yı geçen kural bulunamadı. Giriş filtresi eklemek hep paranın coinde olan kısmını ve kazancı düşürüyor.

## 2026-11-01 · Train · Tur 5: çıkış denemeleri (kill switch kapalı)

Komut (RC): `ft.py backtest --slice train --no-kill-switch [--universe wide] --strategy TrendEmaHold`, ayrıca Mac'te TrendEmaExitPrice (kapanış EMA50 altı). `--timerange 20210101-20240613`, `--fee 0.0015`.

| Strateji | 5 coin Calmar | Düşüş | Getiri | 14 coin Calmar | Karar |
|---|---|---|---|---|---|
| TrendEma | 2,70 | 16,4% | +254% | 0,76 | en iyi |
| TrendEmaHold (EMA200 altında sat) | 1,76 | 26,6% | +277% | 0,72 (DD 49%) | FAIL |
| TrendEmaExitPrice (EMA50 altında sat) | 0,57 | 15,6% | +34% | -0,03 | FAIL |

- Geç çıkmak biraz daha kazanç getiriyor ama 2022'de çok geri veriyor (-%13 vs -%1,5). Erken çıkmak trend kazancını öldürüyor. Mevcut çıkış (EMA20/50 kesişimi) ikisinin arasında, en iyi denge.
- **24 train denemesinden sonra TrendEma (EMA20/50 + EMA200 filtresi) hâlâ en iyi.** Kural aramayı durdurup TrendEma'nın sağlamlığını ölçmeye geçiyoruz (sayı komşuları, Monte Carlo).

## 2026-11-01 · Train · TrendEma sağlamlık: sayı komşuları + Monte Carlo

Komut (RC): `ft.py backtest --slice train --no-kill-switch --strategy EmaFast15 EmaFast25 EmaSlow40 EmaSlow60 EmaTrend150 EmaTrend250`; `report ...`; `ft.py montecarlo --slice train --no-kill-switch [--universe wide] --strategy ...`. `--timerange 20210101-20240613`, `--fee 0.0015`.

### Sayı komşuları (5 coin)

| Komşu (hızlı/yavaş/trend) | Calmar | Düşüş | Karar |
|---|---|---|---|
| EmaSlow60 (20/**60**/200) | 2,83 | 14,1% | PASS |
| EmaFast25 (**25**/50/200) | 2,78 | 15,2% | PASS |
| **TrendEma (20/50/200)** | **2,70** | 16,4% | PASS |
| EmaTrend250 (20/50/**250**) | 2,35 | 17,0% | PASS |
| EmaTrend150 (20/50/**150**) | 1,65 | 23,6% | FAIL |
| EmaSlow40 (20/**40**/200) | 1,42 | 17,5% | FAIL |
| EmaFast15 (**15**/50/200) | 1,07 | 20,3% | FAIL |

- 6 komşudan 4'ü PASS. **Daha yavaş yöne oynatınca sağlam, daha hızlı yöne oynatınca çöküyor** (TrendEmaSlow komşularıyla aynı desen). TrendEma "uçurumun kenarına" yakın ama düz bölgenin içinde. Kural değişmiyor (en iyi komşuya geçmek ezberleme olur); not: ileride ayar gerekirse yön "daha yavaş".

### Monte Carlo (2000 tekrar, kapanmış işlem düşüşü)

| Strateji / evren | Tipik düşüş | %95 kötü senaryo | En kötü | Kötü şansta yıllık | Zarar olasılığı | Kill switch olasılığı |
|---|---|---|---|---|---|---|
| TrendEma / 5 coin | 10,6% | 17,3% | 28,3% | +19,6% | 0,1% | **1,9%** |
| TrendEmaLongTrend / 5 coin | 9,8% | 16,5% | 26,3% | +14,7% | 0,1% | 1,3% |
| TrendEmaSlow / 5 coin | 11,1% | 19,3% | 33,4% | +11,6% | 0,3% | 3,9% |
| TrendEma / 14 coin | 24,8% | 41,5% | 60,9% | +0,4% | 4,8% | **77,8%** |
| TrendEmaLongTrend / 14 coin | 19,9% | 34,1% | 55,3% | +2,9% | 2,8% | 49,5% |

- **5 ana coinde TrendEma sağlam:** işlem sırası şanssız gitse bile %95 ihtimalle düşüş %17'nin altında, zarar olasılığı %0,1.
- **Zayıf coinlerde uygun değil:** kill switch %78 ihtimalle tetiklenir. Karar: bot sadece büyük, likit coinlerde çalışır; coin listesini genişletmek için ayrı kanıt gerekir.

## 2026-11-01 · Train · Faz 2: düşüşte alım (DipRsi) ve haftalık DCA

Komutlar (Mac, main d1bfbad / b4915a9, `--timerange 20210101-20240613`, fee %0,15):
`ft.py backtest --slice train --no-kill-switch [--universe wide] --strategy DipRsi DipRsi4h`, `ft.py report ... --by-year`, `ft.py benchmark --slice train [--universe wide]`

| 5 coin (kill switch kapalı) | İşlem | Getiri | CAGR | Saatlik DD | Calmar | Kazanma | PF | Coinde | Karar |
|---|---|---|---|---|---|---|---|---|---|
| Al-tut | - | +2426,5% | +155,4% | 92,1% | 1,69 | - | - | 100% | referans |
| DCA (haftalık) | - | +171,7% | +33,7% | 64,3% | 0,52 | - | - | artan | referans |
| TrendEma | 638 | +254,3% | +44,3% | 16,4% | 2,70 | 31% | 1,63 | 17% | PASS |
| DipRsi4h | 705 | -31,3% | -10,3% | 33,3% | -0,31 | 60% | 0,74 | 6% | FAIL |
| DipRsi | 2884 | -71,7% | -30,7% | 73,7% | -0,42 | 54% | 0,73 | 7% | FAIL |

| 14 coin | İşlem | Getiri | Saatlik DD | Calmar | Karar |
|---|---|---|---|---|---|
| Al-tut | - | +256,3% | 90,6% | 0,49 | referans |
| DCA | - | +15,3% | 52,7% | 0,08 | referans |
| TrendEma | 949 | +156,5% | 41,3% | 0,76 | PASS (DD > %20) |
| DipRsi4h | 1142 | -28,6% | 43,0% | -0,22 | FAIL |
| DipRsi | 5105 | -91,3% | 92,9% | -0,55 | FAIL |

Yıl yıl (5 coin): DipRsi her yıl zararda (-32,8 / -27,6 / -31,3 / -15,4%), DipRsi4h de her yıl zararda (-12,1 / -11,4 / -7,9 / -4,2%).

Yorum: Kazanma oranı yüksek (%54-61) ama PF < 1. Küçük kazançlar, büyük kayıplar, ve binlerce işlemde komisyon. Connors RSI(2) kuralı kriptoda bu haliyle çalışmıyor. DCA, al-tut'un riskini azaltıyor ama Calmar'da TrendEma'nın çok gerisinde.

## 2026-11-01 · Train · Faz 3: walk-forward (yeni backtest yok)

Komut (Mac, main 4dd3efa, `--timerange 20210101-20240613`, 5 coin, kill switch kapalı): `ft.py walkforward --slice train --no-kill-switch [--strategy ...]`.
Seçim için önceki 12 ay kullanıldı, sonraki 6 ayda işlem yapıldı. Örneklem dışı dönem 2022-01 ile 2024-06 arası. Düşüş sadece kapanmış işlemlerden ölçüldü.

| Aday grubu | "En iyiyi seç" | Sabit TrendEma |
|---|---|---|
| TrendEma + 6 komşu | +%18,7, DD %11,6, Calmar 0,63 (437 işlem) | +%28,2, DD %8,7, Calmar 1,23 (437 işlem) |
| 7 farklı kural (Slow, LongTrend, Multi, Calm, Hold, Atr, TrendEma) | +%25,0, DD %13,6, Calmar 0,70 (342 işlem) | aynı |

Pencere seçimleri:
- Komşular: TrendEma, EmaSlow60, EmaSlow60, TrendEma, EmaTrend150.
- Kurallar: LongTrend, LongTrend, Atr, TrendEma, Multi.

Yorum: Geçen yılın kazananını seçmek, sabit kurala göre hem daha az kazandırıyor hem de daha çok düşürüyor. Sayı ayarlamak ve kural değiştirmek değer katmıyor. Sabit TrendEma'da kalınacak, hyperopt yapılmayacak.

## 2026-11-01 · Train · Ünlü bot türleri ile karşılaştırma (Kaan'ın isteği)

Komut (Mac, main f1fe2e4, `--timerange 20210101-20240613`, fee %0,15, düşüş saatlik ölçüldü): `ft.py bots --slice train --no-kill-switch [--universe wide] --strategy TrendEma`

| 5 coin | İşlem | Getiri | CAGR | DD | Calmar |
|---|---|---|---|---|---|
| Al-tut | - | +2426,5% | +155,4% | 92,1% | 1,69 |
| Haftalık DCA | - | +171,7% | +33,7% | 64,3% | 0,52 |
| Grid bot (Pionex tarzı) | 5553 tur | +163,0% | +32,4% | 24,5% | 1,32 |
| DCA bot (3Commas tarzı) | 2679 anlaşma | +113,7% | +24,7% | 30,1% | 0,82 |
| **TrendEma** | 638 | +254,6% | +44,4% | 16,4% | **2,70** |

| 14 coin | İşlem | Getiri | DD | Calmar |
|---|---|---|---|---|
| Al-tut | - | +256,3% | 90,6% | 0,49 |
| Haftalık DCA | - | +15,3% | 52,7% | 0,08 |
| Grid bot | 13975 | +91,6% | 25,5% | **0,81** |
| DCA bot | 6899 | +51,6% | 32,3% | 0,40 |
| TrendEma | 949 | +156,7% | 41,3% | 0,76 |

Coin başına kontrol: grid düşüşü %20-39 (BTC %39, SOL %19,7). Portföyün düşüşü daha düşük çıkıyor, çünkü coinlerin dipleri farklı aylara denk geliyor. Grid bot kârını yeniden yatırmıyor; kâr nakitte birikiyor, riskte sadece başlangıç parası kalıyor (SOL: 2021 sonunda 4,6x, 2022'de %97 çöküşte düşüş %20). Bu bir hata değil, grid botların gerçek özelliği.

Yorum: 5 büyük coinde TrendEma bütün bot türlerini Calmar'da geçiyor. 14 coinde grid bot az farkla önde (0,81'e 0,76). Grid bot ve DCA bot ayarları varsayılanlardır, ayarlanmadı.

## 2026-11-01 · Train · Komisyon stresi (%0,3) ve TrendEma %50 + Grid %50

Komut: `ft.py bots --slice train --no-kill-switch [--fee-stress] --strategy TrendEma` (`--timerange 20210101-20240613`, 5 coin, main 3e6b98b)

| Bot | Calmar fee %0,15 | Calmar fee %0,30 | DD %0,15 |
|---|---|---|---|
| Al-tut | 1,69 | 1,69 | 92,1% |
| Haftalık DCA | 0,52 | 0,52 | 64,3% |
| Grid bot | 1,32 | 0,97 | 24,5% |
| DCA bot | 0,82 | 0,70 | 30,1% |
| **TrendEma** | **2,70** | **1,82** | 16,4% |
| TrendEma %50 + Grid %50 | 1,99 | 1,38 | 19,5% |

Komisyon iki katına çıkınca da TrendEma bütün bot türlerini geçiyor ve al-tut'u geçen tek bot o. Birleşik deneme (TrendEma %50 + Grid %50) iki parçasının arasında kalıyor, TrendEma'nın tek başına sonucunu geçmiyor. FAIL, elendi. Yıl yıl: grid 2022'de -%20, TrendEma -%1,5.

## 2026-11-01 · Train · TrendEma işlem analizi (yeni deneme değil)

Komut: `ft.py analyze --slice train --no-kill-switch --strategy TrendEma` (`--timerange 20210101-20240613`, 638 işlem)

| Satış nedeni | İşlem | Kazanma | Ortalama | Toplam USDT |
|---|---|---|---|---|
| ema_cross_down | 613 | 32,6% | +2,20% | +3135,6 |
| stop_loss | 24 | 0% | -8,27% | -582,5 |
| force_exit | 1 | 0% | -2,40% | -10,6 |

| Tutma süresi | İşlem | Kazanma | Toplam USDT |
|---|---|---|---|
| 6 saatten az | 54 | 0% | -460,9 |
| 6 saat - 1 gün | 144 | 0% | -1514,8 |
| 1-3 gün | 245 | 12,7% | -1731,6 |
| 3-7 gün | 153 | 83,0% | +2379,0 |
| 1-2 hafta | 38 | 100% | +2931,8 |
| 2 haftadan fazla | 4 | 100% | +939,1 |

Coin bazında: SOL +1216,7, BNB +753,0, XRP +329,4, ETH +296,6, BTC -53,0 USDT.

En iyi %10'luk işlem dilimi toplam kârın %201'ini yapıyor; kalan işlemler toplamda zararda.

Yorum: Tipik trend takibi. Kârın tamamı birkaç uzun yükselişten geliyor. Zarar, girişten kısa süre sonra EMA'ların geri kesişmesinden (whipsaw, testere hareketi) doğuyor. Dikkat: tutma süresi sonuçtan etkileniyor, çünkü kaybeden işlemler kaybettikleri için erken kapanıyor. BTC'yi çıkarmak geçmişe bakarak coin seçmek olur, yapılmayacak.

Tur 7 hipotezleri (Kaan devam deyince):
1. Çıkış onayı: kesişme N mum sürerse sat.
2. Giriş onayı: EMA50'nin eğimi pozitif olsun.

## 2026-11-01 · Train · Tur 7: testere düzeltmeleri + NFI X8

Komut: `ft.py backtest --slice train --no-kill-switch [--universe wide] --strategy ...` ve `report ... --by-year` (`--timerange 20210101-20240613`, main b568667; EntryConfirm ilk olarak Mac'teki yerel dalda koşuldu, main'e aynı kural olarak yazıldı)

| 5 coin | İşlem | Getiri | Saatlik DD | Calmar | PF | 14 coin Calmar |
|---|---|---|---|---|---|---|
| Al-tut | - | +2426,5% | 92,1% | 1,69 | - | 0,49 |
| TrendEma | 638 | +254,3% | 16,4% | 2,70 | 1,63 | 0,76 |
| **TrendEmaEntryConfirm** (giriş 3 mum onaylı) | 625 | +272,2% | 15,3% | **3,03** | 1,67 | **0,92** |
| TrendEmaExitConfirm (çıkış 3 mum onaylı) | 621 | +207,3% | 19,1% | 2,01 | 1,53 | 0,72 |
| TrendEmaSlope (EMA50 yükseliyorsa) | 129 | +46,8% | 6,3% | 1,86 | 2,48 | -0,00 |
| NFI X8 (ünlü bot, 5m, 5 açık işlem) | 116 | +64,8% | 10,3% | 1,52 | 9,68 | - |

Yıl yıl, EntryConfirm vs TrendEma: 2021 +%180,8 / +%177,1; 2022 -%2,7 / -%1,5; 2023 +%27,8 / +%23,5; 2024 +%6,6 / +%5,1.

NFI notu: Kazanma oranı %97. Bunun sebebi stop olmaması ve zarardaki işleme ek alım yapması; kaybeden işlemleri ortalama 35 gün tutuyor. Kârının 2/3'ü 2021'den geliyor; 2022-2024 arasında sadece 28 işlem yapmış (50'den az, istatistik olarak zayıf). Bize katılabilecek bir fikir bulunamadı: avantajı stop'suz ek alım mekanizmasına bağlı, bu da risk kurallarımıza (R1, R2) aykırı.

Karar: EntryConfirm umut verici, ama fikir train analizinden çıktı. Validation'dan önce sayı sağlamlığına (2 ve 4 mum) ve 2 kat komisyon testine girecek.

### EntryConfirm sağlamlık (train, kill switch kapalı)

Komutlar: `report`, `report --fee-stress`, `montecarlo`, `bots` (main 8e6e634)

| Bekleme (mum) | Calmar | DD |
|---|---|---|
| 1 (TrendEma) | 2,70 | 16,4% |
| 2 (EntryConfirm2) | 2,60 | 15,7% |
| **3 (EntryConfirm)** | **3,03** | 15,3% |
| 4 (EntryConfirm4) | 2,14 | 20,4% |

- 2 kat komisyonla: EntryConfirm 2,05, TrendEma 1,81.
- Monte Carlo: DD %95'lik dilimi 16,8% (TrendEma 17,3%), P(DD ≥ %20) %1,8 (TrendEma %1,9).

Karar: Komşular düz bir plato değil, tek bir sivri tepe (2 ve 4 mum TrendEma'dan kötü). Bu yüzden +0,33'lük farkın büyük kısmı muhtemelen gürültü (şans). EntryConfirm validation'a gönderilmiyor; TrendEma'da kalınıyor. Böylece bir validation bakışı boşa harcanmamış oluyor.

## 2026-11-01 · Train · Tur 8: TrendEmaPyramid (kazanana bir kez ekle)

Komut: `ft.py backtest/report --slice train --no-kill-switch [--universe wide] --by-year` (`--timerange 20210101-20240613`, main ef49741)

| | İşlem | Getiri | CAGR | Saatlik DD | Calmar | Kazanma | Coinde | Karar |
|---|---|---|---|---|---|---|---|---|
| Al-tut (5 coin) | - | +2426,5% | +155,4% | 92,1% | 1,69 | - | 100% | referans |
| TrendEma | 638 | +254,3% | +44,3% | 16,4% | 2,70 | 31% | 17% | PASS |
| **TrendEmaPyramid** | 641 | **+614,6%** | +76,8% | 20,9% | **3,69** | 22% | 24% | PASS |
| 14 coin: TrendEma | 949 | +156,5% | | 41,3% | 0,76 | | | PASS |
| 14 coin: Pyramid | 972 | +303,4% | | 56,4% | 0,88 | | | FAIL (DD ≥ al-tut'un yarısı) |

Yıl yıl (5 coin), Pyramid / TrendEma: 2021 +%423,9 / +%177,1; 2022 -%8,2 / -%1,5; 2023 +%38,3 / +%23,5; 2024 +%7,4 / +%5,1.

- İşlemlerin %36,7'sinde ekleme yapıldı (235 / 641).
- Yukarı çekilen stop 64 kez tetiklendi: -2881 USDT. Bunlar +%4'e çıkıp sonra geri düşen işlemler.
- %2 risk denemesi (Risk2) 3,06 Calmar ve %30,6 düşüş vermişti. Piramit daha az düşüşle daha yüksek Calmar veriyor; yani "kazanana eklemek", "her işlemi büyütmek"ten daha iyi.

Sıradaki: sağlamlık testleri. +%3 / +%6 komşuları, 2 kat komisyon, Monte Carlo, ve %25 tavan / %1 risk kurallarının gerçekten tutulup tutulmadığının kontrolü.

### Pyramid sağlamlık (train)

| Ekleme eşiği | Calmar | DD |
|---|---|---|
| +%3 (Pyramid3) | 3,21 | 22,9% |
| **+%4** | **3,69** | 20,9% |
| +%6 (Pyramid6) | 3,14 | 23,2% |
| TrendEma (ekleme yok) | 2,70 | 16,4% |

- **Komşular:** İkisi de TrendEma'yı açık farkla geçiyor. Sonuç sivri bir tepe değil, düz bir plato; yani tek bir sayıya bağlı şans değil.
- **2 kat komisyon:** Pyramid 2,41, TrendEma 1,81.
- **Monte Carlo:** DD için %95'lik sınır 28,1% (TrendEma 17,3%). **P(DD ≥ %20) = %30,5** (TrendEma %1,9). Yani canlıda kill switch'in tetiklenme ihtimali yaklaşık 3'te 1.
- **Risk kuralı kontrolü (641 işlem):**
  - Tek işlem/sermaye en fazla 0,2475 (≤ 0,25 ✔).
  - En kötü işlem sermayenin -%1,14'ü. Bunun %1'i aşan kısmı, iki giriş ve bir çıkışın komisyonu. -%1,3'ü aşan işlem yok ✔.

Karar: Validation sınavına giriyor. Bu 3. validation bakışı. Ayrıca kill switch açık sonuç da raporlanacak.

## 2026-11-01 · VALIDATION #3 · TrendEmaPyramid

Komut: `ft.py backtest --slice validation [--no-kill-switch] --strategy TrendEma TrendEmaPyramid`, `report --by-year`, `bots`. Dönem `--timerange 20240613-20250807`, main 131fb59.

| Bot | İşlem | Getiri | Saatlik DD | Calmar | PF | Karar |
|---|---|---|---|---|---|---|
| Al-tut | - | +122,6% | 47,8% | 2,11 | - | referans |
| Haftalık DCA | - | +60,6% | 36,5% | 1,40 | - | |
| Grid bot | 1955 | +56,7% | 24,3% | 1,97 | - | |
| DCA bot | 1020 | +41,3% | 19,9% | 1,76 | - | |
| TrendEma %50 + Grid %50 | 2172 | +44,1% | 18,5% | 2,02 | - | |
| TrendEma | 217 | +31,4% | 17,3% | 1,55 | 1,62 | FAIL |
| **TrendEmaPyramid** | 218 | **+60,2%** | 24,1% | **2,10** | 1,80 | **FAIL, kıl payı** |

- Pyramid iki şartı da çok az farkla kaçırıyor: Calmar 2,10'a 2,11 ve düşüş 24,1% (sınır, al-tut'un yarısı olan 23,9%).
- Kill switch açık ve kapalı sonuçlar aynı. Train'de kill switch açıkken sonuç da aynı çıktı (3,69), yani gerçek işlem sırasında kill switch hiç tetiklenmedi.
- PF train'de 1,60, validation'da 1,80. Validation'da düşmemesi, aşırı uydurma belirtisi olmadığını gösteriyor.
- Yıl yıl: 2024 (Haziran-Aralık) +%58,1; 2025 (Ocak-Ağustos) +%1,4.

Karar: Kural kuraldır. Pyramid validation'ı GEÇEMEDİ; canlıya/dry-run'a geçmiyor. Yine de bugüne kadarki en iyi adayımız: validation'da TrendEma'dan açık farkla iyi (1,55 → 2,10) ve al-tut ile neredeyse berabere. Dry-run TrendEma'da kalıyor. Validation 3 kez kullanıldı ve artık yıpranmaya başladı.

## 2026-11-01 · Train · Tur 9: TrendEmaPyramidBtc (ekleme sadece BTC EMA200 üstündeyken)

Komut: `ft.py backtest/report/montecarlo --slice train --no-kill-switch [--universe wide] --by-year` (`--timerange 20210101-20240613`, main 008bea6)

| | Calmar | Saatlik DD | 2022 | MC P(DD ≥ %20) | 14 coin Calmar (DD) |
|---|---|---|---|---|---|
| TrendEma | 2,70 | 16,4% | -1,5% | 1,9% | 0,76 (41,3%) |
| TrendEmaPyramid | 3,69 | 20,9% | -8,2% | 30,5% | 0,88 (56,4%) FAIL |
| **TrendEmaPyramidBtc** | **4,16** | **19,4%** | -3,6% | 20,4% | 0,87 (57,5%) FAIL |

- Ekleme yapılan işlem sayısı 235'ten 216'ya düştü.
- Yukarı çekilen stop'un tetiklenme sayısı 64'ten 46'ya düştü.
- BTC filtresi atlanan eklemelerin çoğunda kötü eklemeleri engellemiş.
- Monte Carlo'da en kötü senaryo düşüşü %46,5.

Dürüstlük notu: Bu, validation'a baktıktan sonra Pyramid üzerine eklenen ikinci değişiklik. Bu yüzden validation #4'ten önce sağlamlık testi şart: BTC EMA 150/250 ve ekleme eşiği +%3/+%6 komşuları, ayrıca 2 kat komisyon.

### PyramidBtc sağlamlık (train)

| Komşu | Calmar | DD |
|---|---|---|
| BTC EMA150 | 3,96 | 19,7% |
| **BTC EMA200 + %4 (aday)** | **4,16** | 19,4% |
| BTC EMA250 | 4,00 | 20,0% |
| Ekleme eşiği +%3 | 3,24 | 23,2% |
| Ekleme eşiği +%6 | 3,78 | 20,1% |

- Komşuların hepsi TrendEma'yı (2,70) geçiyor. Sonuçlar birbirine yakın, yani tek bir şanslı ayara bağlı değil (plato).
- 2 kat komisyonla: PyramidBtc 2,99, Pyramid 2,41, TrendEma 1,81.
- Karar: validation #4'e giriyor.

## 2026-11-01 · VALIDATION #4 · TrendEmaPyramidBtc: İLK PASS

Komut: `ft.py backtest --slice validation [--no-kill-switch] --strategy TrendEmaPyramidBtc`, `report --by-year`, `bots` (`--timerange 20240613-20250807`, main 195b3c5)

| Bot | İşlem | Getiri | Saatlik DD | Calmar | PF | Karar |
|---|---|---|---|---|---|---|
| Al-tut | - | +122,6% | 47,8% | 2,11 | - | referans |
| Grid bot | 1955 | +56,7% | 24,3% | 1,97 | - | |
| TrendEma | 217 | +31,4% | 17,3% | 1,55 | 1,62 | FAIL |
| TrendEmaPyramid | 218 | +60,2% | 24,1% | 2,10 | 1,80 | FAIL |
| **TrendEmaPyramidBtc** | 218 | **+63,9%** | **23,1%** | **2,32** | 1,87 | **PASS** |

- Pay az: Calmar 0,21 üstte, DD sınırın 0,8 puan altında.
- Kill switch açık ve kapalı sonuçlar aynı.
- PF train'de 1,66, validation'da 1,87.

Dürüstlük notu: Validation'a 4. bakış. Bu kural, 3. bakışta Pyramid'in kıl payı kaldığını gördükten sonra eklenen bir değişiklik. Yani validation bu kural için kısmen "kullanılmış" durumda. Bağımsız kalan kontroller şunlar: test dilimi (tek seferlik final sınavı) ve dry-run'da ileriye dönük çalışma.

## 2026-11-01 · FİNAL TESTİ (test dilimi, tek seferlik) · TrendEma ve TrendEmaPyramidBtc

Komut: `ft.py backtest --slice test --final-test --strategy TrendEma TrendEmaPyramidBtc`, `report --slice test --by-year`. Dönem `--timerange 20250807-20261001`, kill switch açık (canlıdaki gibi), main 2bfb719.

| | İşlem | Getiri | Saatlik DD | Kazanma | PF | Son işlem | Karar |
|---|---|---|---|---|---|---|---|
| Al-tut | - | -27,0% | 63,7% | - | - | - | referans |
| TrendEma | 121 | -20,1% | 21,4% | 19% | 0,30 | 2026-04-12 | FAIL, kill switch tetiklendi |
| TrendEmaPyramidBtc | 99 | -20,4% | 22,0% | 8% | 0,26 | 2026-03-02 | FAIL, kill switch tetiklendi |

Sonuç: İki kural da final sınavında kaldı. Train ve validation'da PF 1,6-1,9 idi, burada 0,26-0,30. Yani üstünlük yeni dönemde ortadan kalktı. Kıl payı değil, büyük bir kırılma.

Olumlu tek taraf: Kill switch görevini yaptı. Kayıp yaklaşık %20'de durdu; al-tut ise %64 düştü.

Not: Getiri negatif olunca Calmar karşılaştırması anlamını yitiriyor (-0,82 / -0,38). Karar Calmar'a değil, kuralın para kaybetmesine ve PF'nin çökmesine dayanıyor.

Kural gereği bu sonuca bakarak hiçbir şey ayarlanmayacak. Test dilimi bu iki kural için artık kullanıldı.

### Final test dönemi: ünlü bot türleri (aynı dönem, bir kez)

| Bot | Getiri | DD |
|---|---|---|
| Al-tut | -27,0% | 63,7% |
| Haftalık DCA | **+3,4%** | 31,2% |
| Grid bot | -26,4% | 52,1% |
| DCA bot | -5,3% | 37,6% |
| TrendEma | -20,1% | 21,4% |
| TrendEma %50 + Grid %50 | -23,3% | 34,9% |
| TrendEmaPyramidBtc | -20,4% | 22,0% |

- Düşen piyasada aktif botların hepsi para kaybetti; sadece haftalık DCA hafif kârda.
- Bizim kurallarımızın düşüşü en küçük olanlar (kill switch sayesinde).
- Ama bizim kurallar paranın ortalama sadece %6'sını coinde tutmasına rağmen al-tut'a yakın kaybetti: çok sayıda başarısız kırılım işlemi (kazanma oranı %8-19).

## 2026-11-01 · Train + Validation · Tur 10: TrendSmaDaily (günlük SMA200)

Komut: `ft.py backtest --slice train|validation --no-kill-switch [--universe wide] --strategy TrendSmaDaily`, `report`, `bots`, `analyze` (main 41e91cd)

| | İşlem | Getiri | Saatlik DD | Calmar | PF | Karar |
|---|---|---|---|---|---|---|
| Train, 5 coin | 61 | +430,3% | 53,7% | 1,16 | 6,42 | FAIL |
| Train, 14 coin | 158 | -5,5% | 74,1% | -0,02 | 0,96 | FAIL |
| Validation, 5 coin (ilk bakış) | 65 | -18,0% | 26,6% | -0,60 | 0,41 | FAIL |

Neden kaldı:
- -%8 stop, 61 işlemin 26'sında devreye girdi. Günlük grafikteki normal dalgalanma, "SMA200'ün altında kapanış" çıkışından önce stop'u tetikliyor.
- Train kârının çoğu, dönem sonunda hâlâ açık olan 3 işlemden geliyor (+2765 USDT).

Faber'in kuralı sıkı bir stop olmadan tasarlanmış. Bizim %1 risk / -%8 stop kurallarımızla birleşince başka ve daha kötü bir kurala dönüşüyor. Elendi.

## İleriye dönük kontrol #1 (fresh, 2026-11-01)

`ft.py backtest --slice fresh` (kill switch açık) + `ft.py bots --slice fresh`, `--timerange 20261001-20261101`, fee 0.0015. Sadece yargı için; kurallar bu veriye bakılarak değiştirilmez.

| Coin grubu | Al-tut | TrendEma | PyramidBtc | LongTrend | Haftalık DCA | Grid | DCA bot |
|---|---|---|---|---|---|---|---|
| core (5) | -13,5% (DD 17,3%) | -3,3% (DD 3,8%, 17 işlem) | -3,3% (aynı, ekleme olmadı) | -3,1% (16 işlem) | -10,0% | -3,9% | -3,3% |
| wide (14) | -19,6% (DD 24,8%) | -10,7% (36 işlem) | -14,4% | -7,5% (25 işlem) | | | |

50'den az işlem: istatistiksel olarak anlamsız. Okuma: düşen ayda kurallar çoğunlukla nakitte kaldı, ama açılan işlemlerin neredeyse hepsi zararla kapandı (testere).

### Ünlü botlar dahil tam tablo (fresh, 5 coin, 2026-11-01)

`ft.py download --fine` + `ft.py backtest --slice fresh --strategy NostalgiaForInfinityX8` + `ft.py bots --slice fresh --strategy TrendEma TrendEmaBtcRisingGap NostalgiaForInfinityX8` (main be5c0e7), `--timerange 20261001-20261101`, fee 0.0015, kill switch açık.

| Bot | İşlem | Getiri | Saatlik DD |
|---|---|---|---|
| Al-tut | - | -13,5% | 17,3% |
| Haftalık DCA | - | -10,0% | 12,0% |
| Grid (Pionex tarzı) | 83 | -3,9% | 6,1% |
| DCA bot (3Commas tarzı) | 13 | -3,3% | 4,5% |
| Rotasyon (haftalık) | 14 | -12,4% | 14,1% |
| TrendEma | 17 | -3,4% | 3,8% |
| TrendEma %50 + Grid %50 | 100 | -3,6% | 4,5% |
| TrendEmaBtcRisingGap (aday) | 9 | -2,0% | 2,2% |
| NostalgiaForInfinity X8 | 1 | +0,1% | 0,2% |

NFI ayın neredeyse tamamında nakitte kaldı (1 işlem, 2 saat 55 dk, +0,98 USDT, dönem sonunda açık işlem yok). Tek işlem istatistiksel olarak hiçbir şey söylemez (Calmar 4,93 anlamsız). Train'deki davranışıyla tutarlı: çok seçici, paranın ortalama %2'si coinde.

## 2026-11-01 · Train · Üçüncü coin grubu alt2023 (hiç bakılmamış)

Komut: `ft.py download --universe alt2023`, `ft.py backtest --slice train --no-kill-switch --universe alt2023 --strategy TrendEma TrendEmaBtcRising TrendEmaBtcRisingGap TrendEmaLongTrend`, `ft.py bots ...` (main 83a1d7e). Liste (`scripts/universe.py` ALT_2023) testten önce sabitlendi: Ocak 2023'te piyasa değerine göre ilk ~30'daki coinler, stabil coinler ve core/wide hariç. MATIC ve FTM'nin Binance verisi yok → 14 coin.

Pencere: APE 2022-03-17'de listelendi. Adil karşılaştırma için bütün satırlar aynı pencerede: **2022-03-17 → 2024-06-13**. Bu tarihten önce kapanan işlemlerin kârı başlangıç sermayesine katılıyor, getiri pencere başındaki gerçek sermaye üzerinden hesaplanıyor (kontrol edildi: Gap +24,5% eğri / +24,3% gerçekleşmiş; TrendEma -13,2% / -10,8%).

| Bot | İşlem | Getiri | Saatlik DD | Calmar | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|
| Al-tut | - | -53,5% | 82,8% | -0,35 | -69,0% | +51,7% | -2,0% |
| Haftalık DCA | - | +22,1% | 41,3% | 0,23 | -15,4% | +47,3% | -3,1% |
| Grid (Pionex tarzı) | 15647 | -9,2% | 16,7% | -0,25 | -11,6% | +2,6% | +0,0% |
| DCA bot (3Commas tarzı) | 9150 | -5,1% | 24,2% | -0,10 | -16,1% | +6,9% | +5,8% |
| Rotasyon (haftalık) | 289 | -26,8% | 66,5% | -0,20 | -43,4% | +66,1% | -24,2% |
| TrendEma | 959 | -13,2% | 32,0% | -0,19 | -18,5% | +18,3% | -10,6% |
| TrendEmaLongTrend | 686 | -2,2% | 26,2% | -0,04 | -9,2% | +14,0% | -6,2% |
| TrendEmaBtcRising | 563 | +17,8% | 17,5% | 0,43 | -6,7% | +29,3% | -3,1% |
| **TrendEmaBtcRisingGap** | 507 | **+24,5%** | **16,7%** | **0,61** | -3,3% | +32,5% | -3,6% |

Monte Carlo (2000 karıştırma, kapanmış işlem DD): TrendEma P(DD≥20%) %67, Gap %4,2.

Okuma: Aday (Gap), hiç bakılmamış üçüncü grupta da TrendEma'yı ve bütün ünlü bot tiplerini geçiyor; düşüşü en küçükler arasında. Bilinen yanlılık: 2023'te seçilen coinler 2022 çöküşünden sağ çıkmış coinler.

## 2026-11-01 · Validation (yeni coin gruplarında ilk bakış) + fresh alt2023

Komut: `ft.py backtest --slice validation --universe wide|alt2023 --strategy TrendEma TrendEmaBtcRisingGap` (kill switch açık), `ft.py bots ...`; fresh: `--slice fresh --universe alt2023`. Bu gruplarda validation'a ilk kez bakıldı.

| Grup / dilim | Al-tut | Haftalık DCA | Grid | DCA bot | TrendEma | **Gap (aday)** |
|---|---|---|---|---|---|---|
| wide, validation (Calmar) | 0,62 | 0,43 | 0,71 | **0,78** | 0,71 | 0,66 |
| alt2023, validation (Calmar) | -0,20 | 0,00 | 0,02 | **0,11** | 0,01 | -0,11 |
| alt2023, fresh Ekim 2026 (getiri) | -21,1% | -17,1% | -12,9% | -6,7% | -7,2% | **-4,8%** (25 işlem) |

Okuma (dürüst): Aday, train'de üç coin grubunun üçünde de TrendEma'yı geçmişti; ama **validation döneminde (Haz 2024 – Ağu 2025) yeni gruplarda geçemedi**. wide'da TrendEma ve DCA bot'un biraz gerisinde, alt2023'te hafif zararda. Adayın üstünlüğü büyük ölçüde 2022 ayı piyasasında koruma sağlamasından geliyordu; 2024-25'in yükselen-sonra-yatay piyasasında bir katkısı görünmüyor. Ekim 2026 taze veride yine en az kaybeden (işlem sayısı az).

## 2026-11-01 · NFI X8 validation (5 coin, kıyas için)

`ft.py backtest --slice validation --strategy NostalgiaForInfinityX8` (5m, kill switch açık) + `ft.py bots --slice validation --strategy TrendEma NostalgiaForInfinityX8`, `--timerange 20240613-20250807`.

| Bot | İşlem | Getiri | Saatlik DD | Calmar |
|---|---|---|---|---|
| Al-tut | - | +122,6% | 47,8% | 2,11 |
| Haftalık DCA | - | +60,6% | 36,5% | 1,40 |
| Grid | 1955 | +56,7% | 24,3% | 1,97 |
| DCA bot | 1020 | +41,3% | 19,9% | 1,76 |
| TrendEma | 217 | +31,5% | 17,3% | 1,56 |
| Grid + DCA bot + TrendEma (1/3) | 3192 | +43,1% | 15,9% | 2,31 |
| NFI X8 | 25 | +15,2% | 1,5% | 8,60 (<50 işlem) |

NFI 25 işlemin hepsini kazandı, paranın ortalama ~%0'ı coinde (çok seçici). Düşüş çok küçük ama getiri de al-tut'un 1/8'i; 25 işlem istatistik için az. Train'deki gibi: "az al, stop koyma, dönmesini bekle" profili.

## 2026-11-01 · "Early" sınavı (2018-01-01 → 2021-01-01, hiç kullanılmamış dönem)

`ft.py download --universe early --early`, `ft.py backtest --slice early --universe early [--no-kill-switch] --strategy TrendEma TrendEmaVolTarget TrendEmaBtcRising TrendEmaBtcRisingGap TrendEmaLongTrend TrendEmaPyramidBtc`, `ft.py bots ...` (main a57643b). 13 coinden 12'si (EOS verisi yok). Al-tut penceresi 2018-06-12'den (ETC). Kurallar bugünkü halleriyle, değişiklik yok. Bu dilim sadece yargı içindir.

| Bot (kill switch açık, aynı pencere) | İşlem | Getiri | Saatlik DD | Calmar | 2018 | 2019 | 2020 |
|---|---|---|---|---|---|---|---|
| Al-tut | - | +5,9% | 78,7% | 0,03 | -66,5% | +6,3% | +198,6% |
| Haftalık DCA | - | +92,8% | 54,6% | 0,54 | -8,4% | -10,4% | +135,2% |
| Grid | 2664 | -4,2% | 47,3% | -0,04 | -39,8% | +3,2% | +54,5% |
| DCA bot | 2076 | +6,8% | 47,3% | 0,06 | -39,2% | +6,7% | +65,0% |
| Rotasyon | 323 | +129,9% | 48,5% | 0,79 | -17,4% | +19,9% | +132,2% |
| TSMOM | 432 | +94,5% | 23,9% | 1,24 | -15,3% | +23,9% | +85,5% |
| TrendEma (canlı) | 675 | +74,3% | 14,2% | 1,71 | +2,1% | +13,2% | +51,2% |
| **TrendEmaVolTarget** | 675 | +72,4% | **9,6%** | **2,47** | +0,4% | +16,7% | +47,4% |
| TrendEmaBtcRisingGap | 313 | +64,9% | 12,2% | 1,77 | -2,7% | +23,9% | +36,8% |
| TrendEmaBtcRising | 371 | +49,1% | 13,1% | 1,30 | | | |
| TrendEmaLongTrend | 469 | +61,7% | 14,4% | 1,44 | | | |
| TrendEmaPyramidBtc | 404 | +17,1% | 24,0% | 0,27 (2019-12'de kill switch) | | | |

Kill switch kapalıyken sonuçlar aynı; tek fark PyramidBtc (+106%, Calmar 1,32).

Okuma: Hiç görülmemiş 2018 çöküşü + toparlanma döneminde bizim trend kurallarımız ünlü botların hepsinden iyi (grid ve DCA bot 2018'de -%39-40). En iyi Calmar yine VolTarget (2,47, en küçük düşüş %9,6); canlıdaki TrendEma 1,71.

## 2026-11-01 · VolTarget %50 + TSMOM %50 (önceden kaydedildi)

`ft.py bots --slice validation --no-kill-switch --universe core|wide|alt2022|alt2023|alt2024 --strategy TrendEmaVolTarget` ve `ft.py bots --slice early --universe early --strategy TrendEmaVolTarget` (main 2f1248a), fee 0.0015. Validation `--timerange 20240613-20250807`, early `20180101-20210101` (pencere 2018-06-12'den).

| Grup | VolTarget Calmar / DD | TSMOM | **Karışım Calmar / DD** | Al-tut | DCA bot | Grid |
|---|---|---|---|---|---|---|
| core val. | 1,93 / 13,0% | 1,21 | 1,59 / 15,2% | 2,11 | 1,76 | 1,97 |
| wide val. | 0,83 / 20,1% | 0,99 | **0,98 / 19,4%** | 0,62 | 0,78 | 0,71 |
| alt2022 val. | 0,88 / 10,1% | 0,07 | 0,28 / 18,9% | -0,35 | -0,14 | -0,14 |
| alt2023 val. | 0,43 / 17,4% | 0,09 | 0,24 / 20,1% | -0,20 | 0,11 | 0,02 |
| alt2024 val. | 0,30 / 13,6% | -0,58 | -0,32 / 17,1% | -0,45 | -0,03 | 0,01 |
| early | 2,47 / 9,6% | 1,24 | 1,71 / 15,7% | 0,03 | 0,06 | -0,04 |

Ölçüt: Calmar VolTarget'ten yüksek ≥3/5 (oldu: 1/5), DD daha düşük ≥4/5 (oldu: 1/5), early'de ≥ (olmadı) → **FAIL**. TSMOM yeni dönemlerde VolTarget'ten zayıf; karıştırmak onu aşağı çekiyor.

## 2026-11-01 · VolTarget plato kontrolü (sadece train, sağlamlık)

`ft.py backtest --slice train --no-kill-switch --strategy VTFast15 ... VTVol960` + `ft.py bots --slice train --no-kill-switch` (main 0c7c2f6), `--timerange 20210101-20240613`, 5 coin, fee 0.0015. Temel (VolTarget) Calmar 1,86; eşik: ≥ 1,30 (%70) VE > al-tut 1,69. Ünlü botlar: grid 1,32, DCA bot 0,82, haftalık DCA 0,52, TSMOM 2,90.

| Parametre | Daha hızlı / küçük | **Temel** | Daha yavaş / büyük |
|---|---|---|---|
| Hızlı EMA (20) | 15 → **0,67** ✗ | 1,86 | 25 → 1,88 ✓ |
| Yavaş EMA (50) | 40 → **0,98** ✗ | 1,86 | 60 → 1,57 (≥%70, al-tut altı) ✗ |
| Trend EMA (200) | 150 → **1,22** ✗ | 1,86 | 250 → 1,91 ✓ |
| Stop (-%8) | -%6 → 1,95 ✓ | 1,86 | -%10 → 1,86 ✓ |
| Oynaklık penceresi (720) | 480 → 1,63 (≥%70, al-tut altı) ✗ | 1,86 | 960 → 1,81 ✓ |

Sonuç: **Plato değil.** Stop ve oynaklık penceresi sağlam. EMA uzunlukları **hızlı yönde kırılgan**: 15/40/150 ile Calmar %35-65 düşüyor (daha çok testere işlemi). Yavaş yönde (25/250) aynı ya da biraz iyi. TrendEma'nın train komşularında da aynı desen görülmüştü. Bu bir seçim değil; kural değişmiyor.

## 2026-11-05 · VolTarget vs Al-tut (aynı yatırım)

Sadece ölçüm; kural değişmedi, deneme sayılmaz (N=160). Test dilimi zaten kullanılmıştı; Kaan'ın planı gereği sadece ölçüldü. Komut: `ft.py bots --slice S --no-kill-switch --strategy TrendEmaVolTarget` (test için `--final-test`, early için `--universe early`). Fee 0.0015, Calmar saatlik düşüşle. Tablo main 7042349 üstünde `scripts/benchmark.py` değişikliğiyle üretildi. Fresh verisi 2026-11-03'e kadar.

**Gerçek saatlik oran kullanıldı:** `benchmark.invested_ratio` = açık pozisyon değeri / toplam hesap, işlem listesinden. Oran bir önceki saatten alınır; bu yüzden kıyas her işleme bir saat geç girer.

| Dilim (`--timerange`, coin) | VolTarget | Al-tut | **Al-tut (aynı yatırım)** | + devir komisyonu | Sabit ortalama oran | Ort. oran | İşlem |
|---|---|---|---|---|---|---|---|
| train `20210101-20240613`, core | 1,86 (+%113, DD %13,2) | 1,69 (+%2427, DD %92,1) | **2,97** (+%198, DD %12,5) | 1,91 | 0,87 | %12,9 | 638 |
| validation `20240613-20250807`, core | 1,93 (+%29, DD %13,0) | 2,11 (+%123, DD %47,8) | **2,44** (+%35, DD %12,2) | 1,60 | 1,79 | %15,2 | 217 |
| test `20250807-20261001`, core | -0,76 (-%19, DD %21,9) | -0,38 (-%27, DD %63,7) | **-0,58** (-%11, DD %16,0) | -0,72 | -0,18 | %12,3 | 226 |
| early `20180101-20210101`, early | 2,46 (+%72, DD %9,6) | 0,03 (+%6, DD %78,7) | **1,27** (+%36, DD %10,1) | 0,40 | 0,27 | %14,8 | 696 |
| fresh `20261001-20261104`, core | -8,40 (-%3,3, DD %3,7) | -4,63 (-%14, DD %17,3) | **-7,93** (-%2,6, DD %3,2) | -8,12 | -7,91 | %8,7 | 17 |

Kill switch açıkken: train, validation ve fresh aynı; test -0,84 vs aynı yatırım -0,81 (176 işlem, ort. oran %9,4; + devir -0,84); early 2,47 vs 1,56 (675 işlem; + devir 0,50). Fresh'te 17 işlem var (50'den az): anlamlı değil, Calmar bir aylık sonucu yıllığa çevirdiği için abartılı.

**Üç satır neyi ayırıyor:**

- **Sabit ortalama oran:** aynı ortalama miktar, ama zamanlama yok.
- **Al-tut (aynı yatırım):** aynı saatlerde aynı miktar, botun zamanlaması içinde; ama coin seçimi yok, bütün sepet. Devir komisyonu yok, yani ucuza yapılmış hali.
- **+ devir komisyonu:** aynı satır, oran her değiştiğinde komisyon ödeyerek. Gerçekte izlemenin maliyetine daha yakın.

**Okuma:**

1. VolTarget ucuz kıyası (komisyonsuz izleme) 5 dilimin 4'ünde geçemiyor; sadece early'de geçiyor.
2. Devir komisyonlu kıyasla validation ve early'de açık önde, train ve test'te neredeyse eşit, fresh anlamsız.
3. Zamanlama değer katıyor gibi: sabit orana göre aynı yatırım satırı train, validation ve early'de çok daha iyi. Test'te ise tersi (-0,58 vs -0,18).
4. Coin seçimi ve tek tek çıkışlar ek getiri getirmiyor gibi görünüyor: aynı saatlerde bütün sepeti tutmak en az o kadar iyi.

**Sınırlar:** Sepet başta eşit ağırlıklı, sonra yeniden dengelenmiyor; train'in +%2427'si büyük ölçüde SOL'dan geliyor ve aynı yatırım satırını da yukarı çeker. Bu tablo üstünlük ya da yetersizlik kanıtı değil, gözlem. Buradan yeni kural türetmek yasak: denemeler donduruldu.

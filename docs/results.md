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

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

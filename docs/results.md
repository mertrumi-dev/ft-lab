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

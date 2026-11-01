# Araştırma 06: Rejim analizi — VolTarget hangi piyasada kazanıyor, hangisinde kaybediyor?

Sadece analiz. **Bu belgeye bakılarak bugün hiçbir kural değişmez.** Sadece train (2021-01 → 2024-06, 5 coin) ve early (2018 → 2020, early evreni) dilimleri kullanıldı. Validation, test ve taze veri kullanılmadı.

Komut: `python3 scripts/ft.py regimes --slice train --no-kill-switch` ve `python3 scripts/ft.py regimes --slice early --universe early`.

## Rejimler nasıl belirlendi?

Her saat, bir önceki **kapanmış** BTC günlük mumunun rejimini alır (geleceğe bakmak yok):

- **Boğa:** BTC kapanışı 200 günlük ortalamanın (SMA200) üstünde ve SMA200 yükseliyor (20 gün öncekinden yüksek).
- **Ayı:** kapanış SMA200'ün altında ve SMA200 düşüyor.
- **Yatay/testere:** geri kalan her şey (fiyat ortalamanın etrafında gidip geliyor).
- **Oynaklık:** BTC'nin son 30 günlük oynaklığı dilim içinde üçe bölündü (düşük / orta / yüksek, her biri zamanın 1/3'ü).

Her hücre: o rejimdeki saatlerin getirisi **yıla çevrilmiş** hali, sadece o saatler arka arkaya eklenince görülen en büyük düşüş, piyasada kalma oranı (paranın ne kadarı coinde), işlem sayısı ve kazanan işlem oranı (işlem, girdiği saatin rejimine yazılır). İşlem sayısı ve kazanma oranı sadece Freqtrade stratejileri için var. TrendEma ve VolTarget aynı sinyalle girer, bu yüzden işlem sayıları aynı; farkı pozisyon boyutu yaratır.

## Train (2021-01 → 2024-06, 5 coin, kill switch kapalı)

Zamanın dağılımı: boğa %53, yatay/testere %21, ayı %26

| Bot | boğa | yatay/testere | ayı |
|---|---|---|---|
| Buy & hold | +840%/yıl, düşüş 56% | +42%/yıl, düşüş 54% | -71%/yıl, düşüş 86% |
| Weekly DCA | +103%/yıl, düşüş 32% | +13%/yıl, düşüş 30% | -34%/yıl, düşüş 52% |
| Grid bot | +66%/yıl, düşüş 18% | +20%/yıl, düşüş 14% | -9%/yıl, düşüş 19% |
| DCA bot (3Commas) | +44%/yıl, düşüş 19% | +34%/yıl, düşüş 19% | -11%/yıl, düşüş 28% |
| TSMOM | +119%/yıl, düşüş 20% | +38%/yıl, düşüş 10% | -0%/yıl, düşüş 19% |
| TrendEma | +80%/yıl, düşüş 16%, piyasada 20%, 387 işlem %30 kazanç | +11%/yıl, düşüş 11%, piyasada 13%, 121 işlem %34 kazanç | +14%/yıl, düşüş 10%, piyasada 13%, 130 işlem %32 kazanç |
| TrendEmaVolTarget | +41%/yıl, düşüş 14%, piyasada 16%, 387 işlem %30 kazanç | +9%/yıl, düşüş 5%, piyasada 9%, 121 işlem %34 kazanç | +8%/yıl, düşüş 8%, piyasada 10%, 130 işlem %32 kazanç |

Oynaklık rejimi: düşük oynaklık %33, orta oynaklık %33, yüksek oynaklık %33

| Bot | düşük oynaklık | orta oynaklık | yüksek oynaklık |
|---|---|---|---|
| Buy & hold | +37%/yıl, düşüş 75% | +245%/yıl, düşüş 78% | +253%/yıl, düşüş 61% |
| Weekly DCA | +42%/yıl, düşüş 43% | +42%/yıl, düşüş 49% | +18%/yıl, düşüş 28% |
| Grid bot | +1%/yıl, düşüş 15% | +39%/yıl, düşüş 17% | +65%/yıl, düşüş 21% |
| DCA bot (3Commas) | +3%/yıl, düşüş 19% | +34%/yıl, düşüş 17% | +40%/yıl, düşüş 24% |
| TSMOM | +33%/yıl, düşüş 25% | +77%/yıl, düşüş 22% | +81%/yıl, düşüş 21% |
| TrendEma | +23%/yıl, düşüş 11%, piyasada 17%, 218 işlem %29 kazanç | +58%/yıl, düşüş 13%, piyasada 18%, 215 işlem %33 kazanç | +55%/yıl, düşüş 13%, piyasada 17%, 205 işlem %33 kazanç |
| TrendEmaVolTarget | +18%/yıl, düşüş 11%, piyasada 16%, 218 işlem %29 kazanç | +26%/yıl, düşüş 12%, piyasada 13%, 215 işlem %33 kazanç | +30%/yıl, düşüş 5%, piyasada 10%, 205 işlem %33 kazanç |
$ docker compose run --rm -v /Users/mert/ft-lab/scripts:/freqtrade/scripts:ro --entrypoint python freqtrade /freqtrade/scripts/regimes.py --slice train --universe core --results-dir /freqtrade/user_data/backtest_results/no_kill_switch --strategy TrendEma TrendEmaVolTarget

## Early (2018 → 2020, early evreni)

Zamanın dağılımı: boğa %41, yatay/testere %17, ayı %42

| Bot | boğa | yatay/testere | ayı |
|---|---|---|---|
| Buy & hold | +38%/yıl, düşüş 61% | -31%/yıl, düşüş 44% | -10%/yıl, düşüş 74% |
| Weekly DCA | +52%/yıl, düşüş 40% | -22%/yıl, düşüş 33% | +36%/yıl, düşüş 34% |
| Grid bot | +9%/yıl, düşüş 36% | -18%/yıl, düşüş 23% | -5%/yıl, düşüş 47% |
| DCA bot (3Commas) | +11%/yıl, düşüş 36% | -20%/yıl, düşüş 25% | +5%/yıl, düşüş 46% |
| TSMOM | +42%/yıl, düşüş 22% | -3%/yıl, düşüş 22% | +34%/yıl, düşüş 20% |
| TrendEma | +22%/yıl, düşüş 14%, piyasada 23%, 275 işlem %32 kazanç | +7%/yıl, düşüş 13%, piyasada 20%, 103 işlem %24 kazanç | +34%/yıl, düşüş 13%, piyasada 19%, 243 işlem %36 kazanç |
| TrendEmaVolTarget | +26%/yıl, düşüş 10%, piyasada 17%, 275 işlem %32 kazanç | +13%/yıl, düşüş 10%, piyasada 15%, 103 işlem %24 kazanç | +27%/yıl, düşüş 9%, piyasada 13%, 243 işlem %36 kazanç |

Oynaklık rejimi: düşük oynaklık %33, orta oynaklık %33, yüksek oynaklık %33

| Bot | düşük oynaklık | orta oynaklık | yüksek oynaklık |
|---|---|---|---|
| Buy & hold | +40%/yıl, düşüş 39% | -7%/yıl, düşüş 50% | -18%/yıl, düşüş 60% |
| Weekly DCA | +28%/yıl, düşüş 30% | +66%/yıl, düşüş 34% | +1%/yıl, düşüş 37% |
| Grid bot | +14%/yıl, düşüş 22% | +9%/yıl, düşüş 29% | -23%/yıl, düşüş 34% |
| DCA bot (3Commas) | +26%/yıl, düşüş 23% | +3%/yıl, düşüş 30% | -17%/yıl, düşüş 34% |
| TSMOM | +34%/yıl, düşüş 20% | +75%/yıl, düşüş 12% | -7%/yıl, düşüş 21% |
| TrendEma | +48%/yıl, düşüş 12%, piyasada 23%, 241 işlem %35 kazanç | +36%/yıl, düşüş 12%, piyasada 20%, 192 işlem %33 kazanç | -5%/yıl, düşüş 17%, piyasada 20%, 188 işlem %28 kazanç |
| TrendEmaVolTarget | +43%/yıl, düşüş 8%, piyasada 18%, 241 işlem %35 kazanç | +30%/yıl, düşüş 10%, piyasada 14%, 192 işlem %33 kazanç | +2%/yıl, düşüş 7%, piyasada 12%, 188 işlem %28 kazanç |

Not: Early'de 2018'in ilk ~7 ayı etiketsiz kaldı (SMA200 ve eğimi için yeterli geçmiş yok); yüzdeler etiketli saatler üzerinden. Early sonuçları kill switch açık koşudan; o koşuda kill switch tetiklenmemişti.

## 3 sonuç

1. **Yatay/testere piyasa VolTarget'in zayıf yeri. Kaybettirmiyor ama az kazandırıyor; bu bilinen bedel.** Train'de yılda +%9 (boğada +%41; ayıda da benzer, +%8), early'de +%13 (boğada +%26). Early testerede kazanan işlem oranı %24'e iniyor (diğer rejimlerde %32-36). Trend kuralı yanlış alarm veriyor; küçük stop zararları birikiyor. Ünlü botlar testerede karışık: train'de grid +%20 ve DCA bot +%34 ile iyi, early'de grid -%18, DCA bot -%20, haftalık DCA -%22. "Grid testerede kazanır" kuralı iki dilimde tutarlı değil.
2. **Ayı piyasada koruma çalışıyor.** BTC SMA200 altında ve düşerken coini tutmak train'de yılda -%71 (düşüş %86), early'de -%10 (düşüş %74). VolTarget aynı saatlerde train'de +%8 (düşüş %8), early'de +%27 (düşüş %9). Sebebi: kural her coinin kendi trendine bakıyor ve çoğu zaman dışarıda bekliyor (piyasada %10-13). Ayı içindeki kısa yükselişleri de yakalıyor. Her iki dilimde de VolTarget'in eksi yıllık getirili bir rejimi yok.
3. **Oynaklık arttıkça VolTarget'in boyut küçültmesi işe yarıyor.** Yüksek oynaklıkta düşüş train'de %5, early'de %7. Aynı sinyalle tam boyut giren TrendEma'da bu %13 ve %17. Early yüksek oynaklıkta TrendEma yılda -%5 kaybederken VolTarget +%2'de kalıyor. Bedeli: train'in yüksek oynaklıklı boğasında TrendEma +%55, VolTarget +%30. Paranın çoğu boğa piyasasından geliyor (train boğa: +%41/yıl). Bot "yükselişte kazan, düşüşte dışarıda dur" diye çalışıyor; B&H'nin boğadaki +%840'ına yaklaşamıyor.

## Fikir listesi (test etmeden önce journal.md'ye ön-kayıt şart)

Bunlar bu analizden çıkan fikirler, **kanıt değil**. Her biri denenmeden önce docs/journal.md'ye kriteriyle yazılmalı ve sadece train'de türetilmeli.

- [ ] Testere rejiminde (BTC SMA200 eğimi yatay) yeni girişleri durdurmak. Dikkat: testere hâlâ artı, yani filtre muhtemelen getiriyi düşürür. Ancak düşüşü belirgin azaltırsa anlamlı. Ön-kayıt şart.
- [x] Boğa rejiminde hedef oynaklığı yükseltmek (%60 → %80): ön-kayıtla denendi (TrendEmaVolTargetBullVol), **FAIL**. Validation'da Calmar 0/5 grupta daha iyi; düşüş 5 grubun hepsinde büyüdü. Train'de iyileşti (2,08 vs 1,86), yeni döneme taşınmadı. Ayrıntı: journal.md.
- [ ] Testerede kazanma oranı düşük: girişte 20/50 kesişmesinin "net" olmasını istemek (ör. EMA20, EMA50'nin %0,5 üstünde). Gap denemesi (EMA200 için) başarısız olmuştu; bu farklı bir yer. Ön-kayıt şart.
- [ ] Grid botu sadece testere rejiminde çalıştırmak: train'de lehine (+%20), early'de aleyhine (-%18). Tutarsız, düşük öncelik.

## Anlaman gerekenler

- **Toplam sonuç, nerede kazanıp kaybettiğini gizler.** Rejimlere bölünce kuralın "kişiliği" görünüyor: boğada kazanır, ayıda kenarda bekler, testerede az kazanır.
- **Geleceğe bakmamak analizde de önemli.** Her saat, sadece o saatte bilinen (dünkü kapanmış) BTC mumuna göre etiketlendi.
- **Analizden çıkan fikir, test değildir.** Aynı veriye bakıp kural ayarlamak aşırı uyum (overfitting) demek; bu yüzden fikirler önce ön-kayıt listesine gider.

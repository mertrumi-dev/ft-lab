# Kart 41: Al-tut (aynı yatırım)

## Soru

Bot al-tut'tan çok daha az düşüyor. Ama parasının ortalama sadece %13'ü piyasada. Parasının çoğu nakitte duran herkes az düşer. O zaman botun gerçek katkısı ne?

## Yeni satır ne yapıyor?

`scripts/benchmark.py` içinde iki fonksiyon:

**`invested_ratio(curve)`**
- Girdi: botun saatlik hesap tablosu.
- Çıktı: her saat `açık pozisyon değeri / toplam hesap`, 0 ile 1 arasında.

**`exposure_matched_equity(closes, ratio, fee)`**
- Girdi: coin fiyatları ve o oran.
- Her saat şunu yapar: `hesap × (1 + önceki saatin oranı × sepetin bu saatki getirisi)`.
- Çıktı: saatlik hesap değeri.

Kalan para nakitte durur ve faiz almaz.

## Neden önceki saatin oranı?

Bu saatin oranı bu saatin fiyatını içerir. Onu kullanmak, geleceği bilmek olurdu (look-ahead). Bedeli: kıyas her işleme bir saat geç girer.

## Testler neyi garanti ediyor?

- Oran hep 0 ise getiri tam 0.
- Oran hep 1 ise sonuç normal al-tut ile birebir aynı.

Bu iki uç doğruysa, formülün ortası da büyük ihtimalle doğrudur. Aralığın iki ucunu test etmek iyi bir alışkanlıktır.

## Dikkat: bu satır zamanlamasız değil

Oran botun piyasaya girip çıktığı saatleri taşıyor. Yani bu satır "bot ne zaman piyasadaysa o zaman bütün sepeti tut" demek. Karşılaştırma üç parçaya ayrılıyor:

`sabit oran → aynı yatırım` farkı = zamanlamanın katkısı
`aynı yatırım → VolTarget` farkı = coin seçiminin ve maliyetlerin katkısı

## Komisyon seçimi

Ana satır sadece giriş ve çıkış komisyonu öder: botun yendiğini söylemeyi zorlaştıran, ucuz kıyas. Gerçekte oranı saat saat izlemek daha pahalı olurdu. O yüzden `charge_turnover=True` ile ikinci ölçüm de yapıldı. Doğru cevap ikisinin arasında bir yerde.

## Sonuç (Calmar, kill switch kapalı)

| | train | validation | test | early |
|---|---|---|---|---|
| VolTarget | 1,86 | 1,93 | -0,76 | 2,46 |
| Aynı yatırım (ucuz) | 2,97 | 2,44 | -0,58 | 1,27 |
| Aynı yatırım (devir komisyonlu) | 1,91 | 1,60 | -0,72 | 0,40 |
| Sabit ortalama oran | 0,87 | 1,79 | -0,18 | 0,27 |

Tam tablo: `docs/results.md`.

## Anlaman gerekenler

- **Az düşüş tek başına beceri değildir.** Az yatırım yapan herkes az düşer. Önce aynı miktarla kıyasla.
- **Bir kıyasın neyi sabit tuttuğunu bil.** Bu satır miktarı ve zamanı sabit tutar, sadece coin seçimini çıkarır.
- **Bu gözlem yeni kural değildir.** "O zaman bütün sepeti alalım" bir fikirdir ve aynı veriden çıkar. Denemeler donduruldu; böyle bir deneme için Kaan'ın onayı gerekir.

# Öğretici kart 37: Bir filtre hangi işlemleri attı? (`ft.py removed`)

## Sorun

Bir giriş filtresi (örneğin "aşırı korkuda alma") ana kuralın bazı alımlarını engeller. Backtest sonunda sadece toplam bir sayı görürüz: "Calmar 2,44 oldu." Ama asıl soru şu: **filtre hangi işlemleri attı ve bunlar iyi miydi, kötü müydü?**

Araştırma 15 bunun neden önemli olduğunu gösterdi: bir filtre ortalamada iyi görünüp belirli yıllarda (özellikle büyük trendlerin başında) en iyi işlemleri kesebiliyor.

## Araç

```bash
python3 scripts/ft.py removed --strategy TrendEmaVolTargetNoChase --slice early --universe early
```

Ne yapar:

1. Ana kuralın (VolTarget) ve filtreli kuralın mevcut backtest sonuçlarını okur. **Kendisi backtest çalıştırmaz**; sonuç yoksa "önce backtest et" der.
2. Ana kuralın aldığı ama filtrenin almadığı işlemleri bulur (aynı coin + aynı giriş saati).
3. Bunları yıl yıl özetler: kaç işlem, toplam kâr/zarar, kazanma oranı, girişten sonraki 7 günde fiyatın %15 ya da daha fazla yükseldiği işlemlerin payı (gerçek trend başlangıcı mıydı?), girişteki 30 günlük oynaklık.

Örnek çıktı (T151, 2018-20):

```
removed 206 of 696 base entries, their P/L +356.0 USDT (+43% of the base profit)
year   trades      P/L   win  rise>=15% in 7d  vol30 med
2018       47    +30.7   40%              26%       107%
2019       92   +101.9   33%              26%        87%
2020       67   +223.4   42%              33%        82%
```

## Nasıl okunur?

| Bir yılda çıkarılan işlemlerin kârı | Anlamı |
|---|---|
| **Eksi** (zararlıydılar) | Filtre o yıl işe yaradı: kaybedenleri attı |
| **Artı** (kârlıydılar) | Filtre o yıl zarar verdi: kazananları attı (çoğu zaman trend başlangıçları) |

Yukarıdaki örnekte üç yılda da artı: filtre 2018-20'de kuralın kârının %43'ünü taşıyan işlemleri atmış. Bu yüzden early sınavında kaldı.

**Sağlam bir filtre** her yılda, her piyasa türünde kaybedenleri atar. Sadece bazı yıllarda işe yarıyorsa, aslında bir "piyasa türü bahsi" yapıyordur.

## Deneme sırasında otomatik

Giriş filtresi denemelerinde:

```bash
python3 scripts/ft.py trial --strategy X --entry-filter
```

Her dilimin backtest'inden sonra bu tabloyu kendisi basar. Hüküm yine `scripts/criterion.py`'nin ölçütüyle verilir; bu tablo sadece **anlamak** içindir, hükmü değiştirmez.

## Anlaman gerekenler

- **Toplam sayı gizler, döküm gösterir.** Bir sonucu anlamak için onu parçalara ayır: yıl yıl, coin coin.
- **Teşhis aracı ile hüküm aracı ayrıdır.** `removed` neden olduğunu gösterir; geçip kalmaya `criterion.py` karar verir. İkisini karıştırmak, sonuca göre ölçüt değiştirmeye kapı açar.
- **Okuma aracı kendi başına iş yapmaz.** Bu araç hiçbir zaman backtest çalıştırmaz; sadece var olanı okur. Böylece yanlışlıkla "yeni bir bakış" (deneme sayısı) oluşmaz.

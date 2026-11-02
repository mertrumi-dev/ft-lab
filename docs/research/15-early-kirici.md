# Araştırma 15: Neden 2018-20 (early) filtreleri bozuyor? (2026-11-02)

Neden: Son denemelerde aynı şey tekrar etti. Bir filtre 2021-25'te (train, validation, yeni coinler) ana kuralı iyileştiriyor, ama 2018-20'de (early) bozuyor:

| Deneme | Fikir | train Calmar | early Calmar (sınır 2,21) |
|---|---|---|---|
| T145 FearBlock | aşırı korkuda alma | 2,18 (VolTarget 1,86) | 2,14 ✗ |
| T146 FearExit | aşırı korkuda sat | 2,28 | 1,45 ✗ |
| T151 NoChase | fiyat 2×ATR sıçramışsa alma | 2,44 | 1,44 ✗ |

Bu belge **sadece analiz**. Yeni deneme yok, ölçüt değişmedi, N aynı (149). Mevcut backtest sonuçları kullanıldı (kill switch kapalı, komisyon %0,15).

## Yöntem

Her filtre için: VolTarget'in girdiği ama filtrenin **girmediği** işlemler ("çıkarılan işlemler"; aynı coin + aynı giriş saati). Bunlara üç soru:

1. Toplamda kazandırıyorlar mıydı, kaybettiriyorlar mıydı?
2. Girişten sonraki 7 günde fiyat ne kadar yükseldi? (Gerçek bir trendin başlangıcı mıydı?)
3. Girişteki 30 günlük oynaklık neydi?

Dilimler: train core (2021-01-01 → 2024-06-13, 5 coin) ve early (2018-01-01 → 2021-01-01, early grubu). Not: T146 girişleri değil çıkışları değiştirdiği için bu karşılaştırmaya uymuyor; etkisi early'de çok sayıda erken çıkış ve yeniden giriş (146 yeni işlem, toplam -43 USDT).

## Bulgular

### 1. Çıkarılan işlemler early'de çok daha değerliydi

| | train | early |
|---|---|---|
| VolTarget toplam kâr | +1.128 USDT | +821 USDT |
| T151'in çıkardığı işlemlerin kârı | +148 USDT (toplamın **%13**'ü) | +356 USDT (toplamın **%43**'ü) |
| T145'in çıkardığı işlemlerin kârı | +19 USDT | +79 USDT |

Early'de filtrenin attığı işlemler, kuralın kârının neredeyse yarısını taşıyordu.

### 2. Yıl yıl: filtre bir "rejim bahsi"

T151 (sıçramayı kovalama), çıkarılan işlemlerin kârı, yıl yıl:

| Yıl | Çıkarılan işlem | Kârları | Yorum |
|---|---|---|---|
| 2018 | 47 | +31 | ayı piyasası, ama sıçramaların bir kısmı gerçek |
| 2019 | 92 | +102 | ilkbahar toparlanması |
| 2020 | 67 | **+223** | Mart çöküşünden sonra V dönüşü, boğa başlangıcı |
| 2021 | 68 | **+256** | boğa: sıçramalar gerçek trend başıydı |
| 2022 | 59 | **-81** | ayı / testere: filtre işe yaradı |
| 2023 | 65 | **-42** | yatay: filtre işe yaradı |
| 2024 (yarım) | 29 | +15 | karışık |

Aynı desen T145'te (aşırı korkuda alma): 2018'de -16 USDT (filtre hafifçe yardım etti), 2020'de **+92 USDT** (%42 kazanan). Mart 2020 çöküşündeki "aşırı korku", ardından gelen büyük yükselişin tam başıydı.

**Sonuç:** Bu filtreler aslında bir piyasa rejimi bahsi. Testere ve ayı yıllarında yardım ediyorlar, ama **V şeklindeki dönüşlerde ve boğanın başında** zarar veriyorlar, çünkü orada "aşırı" görünen an (sert sıçrama, aşırı korku) gerçek trendin başlangıcı.

### 3. Early daha oynak ve sıçramalar daha sık "gerçek"

| | train | early |
|---|---|---|
| Çıkarılan girişlerde 30 günlük oynaklık (medyan) | %70-87 | %88-108 |
| T151: girişten sonra 7 günde ≥ %15 yükselenlerin payı | %19 | %28 |
| T145: aynı pay | %18 | %24 |

2018-20 piyasası daha oynak. Oynak bir piyasada "2×ATR sıçrama" ya da "aşırı korku" istisna değil, sık görülen bir durum. Filtre daha sık devreye giriyor ve gerçek hareketleri de kesiyor.

## Neden 2018-20 farklı? (yorum, test edilmedi)

- **İki büyük V dönüşü içeriyor:** 2019 ilkbaharı (2018 ayısından çıkış) ve Mart 2020 çöküşünden sonraki toparlanma. 2021-25'te bu kadar keskin dönüşler daha az.
- **Daha oynak ve daha genç bir piyasa:** vadeli işlemler ve kurumsal para henüz az; hareketler daha sert.
- **Coin grubu farklı:** early grubu 2018'in coinleri (ADA, XLM, LTC, QTUM...), bugünün 5 coini değil.

## Gelecekteki filtre fikirleri için tasarım dersi

1. **"Toplam" yetmez, yıl yıl bak.** Bir filtrenin attığı işlemler toplamda zararlı olabilir ama belirli yıllarda (özellikle trend başlangıçlarında) çok kârlı olabilir. Sağlam bir filtre, **her rejimde** kaybedenleri atmalı.
2. **"Aşırılık" filtreleri bir rejim bahsidir.** Aşırı korku, sert sıçrama, heyecan zirvesi: bunların hepsi testerede iyi, V dönüşünde kötü. Böyle bir fikir önerilirken bu bilinerek önerilmeli; önsel beklenti düşük tutulmalı.
3. **early dilimi bir "V dönüşü sınavı" gibi.** Bir fikir sadece early'de kalıyorsa, büyük ihtimalle trend başlangıçlarını kesiyordur. Ölçütü değiştirmek doğru değil: gerçekte de bir V dönüşü gelecek ve kural onu kaçırmamalı.
4. **Bir analiz aracı olarak kullanılabilir:** yeni bir filtre denendiğinde "çıkarılan işlemlerin yıl yıl kârı" tablosu hükme ek bilgi olarak bakılabilir. Bu bir hüküm kuralı değil, anlamaya yardım eden bir tablo.

## Komutlar ve dönemler

- Analiz: scratchpad'deki `early_breaker.py` (salt okunur; `report.latest_stats_per_strategy`, no_kill_switch sonuçları), konteyner içinde.
- train core: `--timerange 20210101-20240613`, 5 coin; early: `--timerange 20180101-20210101`, early grubu. Komisyon 0.0015, kill switch kapalı.

## Anlaman gerekenler

- **Ortalama gizler.** Bir filtrenin "ortalamada" iyi olması, her dönemde iyi olduğu anlamına gelmez. Yıllara bölmek gerçek davranışı gösterir.
- **"Aşırı" an bazen başlangıçtır.** Korku ya da sert sıçrama, testerede bir uyarı, V dönüşünde bir başlangıç işaretidir. Kural ikisini ayıramıyorsa, ikisini birden keser.
- **Sınavı kolaylaştırma.** Bir dilim sürekli bozuyorsa, sorun sınavda değil, fikrin bir rejimde kör olmasında olabilir.

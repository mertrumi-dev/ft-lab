# Araştırma 16: Hafta özeti, T150-T162 (2026-11-04)

Bu belge, yeni başlayan biri için sade dille yazıldı. Soru şuydu: ana kuralı yeni fikirlerle ya da yeni veri kaynaklarıyla daha iyi yapabilir miyiz?

**Kısa cevap: Ana kural (TrendEmaVolTarget) aynen kaldı.** Hiçbir fikir bütün sınavları geçemedi. Üç fikir, sadece bundan sonraki yeni fiyatlarla yargılanmak üzere izlemeye alındı.

## Sınav nasıl işliyor?

Her fikir denenmeden **önce** yazıldı (ön kayıt). Sonra ana kuralla dört dönemde karşılaştırıldı:

| Dönem | Geçme şartı |
|---|---|
| 2021-24 (train, 5 coin) | ana kuralın en az %90'ı |
| 2024-25 (validation, 5 coin) | en az ana kural kadar |
| 2024-25 yeni coinler (alt2024b) | ana kuraldan yüksek ve düşüş daha büyük değil |
| 2018-20 (early) | ana kuralın en az %90'ı |

Sayılar **Calmar**: yıllık getiri bölü en büyük düşüş. Yüksek olan iyi. Ana kuralın sayıları: **1,86 / 1,93 / -0,46 / 2,46**.

## Ne denendi?

| Deneme | Fikir (sade) | 2021-24 | 2024-25 | Yeni coin | 2018-20 | Sonuç |
|---|---|---|---|---|---|---|
| T150 | Grubundan güçlü coinleri al | | | | | **Koşulmadı:** T107'nin neredeyse aynısı |
| T151 | Fiyat çok sıçramışsa kovalama | 2,44 | 1,91 | +0,23 | 1,44 | Kaldı (iki dönem) |
| T152 | Hafta sonu sinyaliyle alma | 1,66 | 2,21 | -0,31 | 2,67 | Kaldı (0,01 farkla) → izleme F011 |
| T153 | BTC kırılınca altcoinleri sat | 0,48 | 0,71 | -0,49 | 1,18 | Kaldı (dördü de) |
| T154 | Vadeli fonlama oranı aşırıysa alma | 1,94 | 1,93 | -0,45 | 3,32* | Kaldı (0,0008 farkla), neredeyse etkisiz |
| T155 | Stablecoin arzı artıyorsa al | 2,48 | 1,87 | -0,37 | 2,41 | Kaldı (bir dönem) → izleme F012 |
| T158 | Madenciler zorlanıyorsa alma | 0,99 | 0,83 | -0,52 | 1,54 | Kaldı (dördü de) |
| T159 | Wikipedia ilgisi artıyorsa al | 2,06 | 2,96 | +0,12 | 1,24 | Kaldı (bir dönem) → izleme F013 |
| T162 | BTC'nin payı düşerken altcoin al | 0,93 | 0,39 | -0,76 | 1,57 | Kaldı (dördü de) |

\* T154'te fonlama verisi 2019-09'da başladığı için bu sınav 2019-09 → 2021-01 döneminde yapıldı (ana kural orada 3,43).

T156/T157 ve T160/T161 yeni fikir değil, komşu ayar kontrolüydü (aşağıda).

**Haber (GDELT) denenemedi:** servis bu bilgisayarın adresinden gelen istekleri reddediyor. Sunucuya geçince tekrar denenecek. Deneme sayısı (N) şu an **160**.

## Üç tasarım dersi

### 1. Kazananı erken satmak zarar veriyor

Bu kural kârını birkaç büyük trendden alıyor. T060, T109, T135 ve bu hafta T153 hep aynı şeyi gösterdi: işlemi erken kapatan kural büyük kazançları da kesiyor. T153'te BTC kırıldığında kapatılan işlemler ortalamada hâlâ kârdaydı.

### 2. "Aşırı an" filtreleri aslında piyasa türü bahsi

Aşırı korku, sert sıçrama, heyecan zirvesi: bunlara bakan filtreler yatay ve düşen piyasada yardım ediyor, ama büyük dönüşlerin başında zarar veriyor. Çünkü "aşırı" görünen an bazen trendin başlangıcıdır (araştırma 15). T151'in attığı işlemler 2018-20'de ana kuralın kârının %43'ünü taşıyordu.

### 3. Piyasa geneli kapılar toparlanmanın başını kesiyor

"Piyasa iyi durumda değilse hiç alma" diyen kurallar (T158 madenci stresi, T162 BTC payı) toparlanmaların başını kaçırıyor. T158'in attığı işlemler 2020'de +353 USDT kazandırmıştı. T162'nin attığı işlemler sekiz yılın hepsinde kârlıydı. Dönüş, kapı açılmadan önce başlıyor.

## İzleme listesi (yeni fiyatlarla yargılanacak)

Bugünkü kuralı değiştirmezler. Her biri kilitli şartla, 6 ay sonra yargılanır; erken bakmak kodla engelli.

| Satır | Fikir | Başlangıç → hüküm | Dikkat |
|---|---|---|---|
| F011 | Hafta sonu alma | 2026-11-03 → 2027-05-03 | Yıl yıl karışık (2020 ve 2021'de kazananları attı) |
| F012 | Stablecoin arzı artıyorsa al | 2026-11-05 → 2027-05-05 | Komşu ayarlar iyi değil (plato yok) |
| F013 | Wikipedia ilgisi artıyorsa al | 2026-11-05 → 2027-05-05 | Plato yok; 2018-20'de kötü; ama aynı yatırım seviyesinde "ana kural + nakit"ten üç dönemde iyi |

Daha eski F001-F010 satırları da sürüyor.

## Komşu ayar kontrolü neden önemli?

Bir ayar iyi çıktığında yanındaki ayarlara da bakıyoruz. Yanındakiler kötüyse o ayar büyük ihtimalle şanslı bir tepedir:

- **Stablecoin:** 30 gün 2,48 ama 14 gün 1,31.
- **Wikipedia:** 20/60 ayarı 2021-24'te 4,28 gibi çok iyi görünüyor, ama onu seçmedik. Sonuca bakıp en iyi ayarı seçmek, geçmişi ezberlemektir.

## Bu hafta yapılan hatalar (dürüstçe)

- T162'yi önce BNB'yi de içeren bir tanımla yazdım; BNB verisi 2019'da bitiyordu. Sonuca bakmadan koşuyu durdurdum, tanımı düzelttim.
- T159'da "fark sadece daha az piyasada kalmaktan geliyor" dedim. Ölçünce 2021-25 için yanlış çıktı, düzelttim.
- Mac'in uykusu ve ısınması yüzünden botlar uzun süre durdu. **Botlar şu an kapalı**; 24 saatlik Faz 0 sayacı işlemiyor. Asıl çözüm uyumayan bir sunucu.

## Anlaman gerekenler

- **Yeni veri kaynağı otomatik olarak yeni bilgi demek değil.** Dokuz fikrin hiçbiri bütün sınavları geçmedi.
- **Bir sınavı kıl payı kaçırmak yine de kalmaktır.** Kuralı sonuca göre esnetmek, kendini kandırmanın başlangıcıdır.
- **Yüksek skor tek başına yetmez.** Yıl yıl davranışına, komşu ayarlara ve getiri ile düşüşe ayrı ayrı bak.

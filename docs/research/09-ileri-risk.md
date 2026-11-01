# Araştırma 09: Önümüzdeki 12 ay için risk tahmini (2026-11-01)

Soru: Bu akşam dry-run'a geçen VolTarget, yeni (kilitlenen) kill switch'le önümüzdeki 12 ayda nasıl bir yol izleyebilir? Kill switch'e ne kadar ihtimalle çarpar?

Komut: `python3 scripts/ft.py forward-risk`. Her gün günlük rapora bir satır olarak girer ("İleriye risk").

## Nasıl hesaplandı?

1. Kuralın daha önce yargılanmış dönemlerdeki **günlük getirileri** alındı: validation, 5 coin, kill switch kapalı (419 gün) + early, 2018-2020 (933 gün).
2. Bu günler **7 günlük bloklar** halinde rastgele yeniden dizildi (sakin ve fırtınalı haftalar bir arada kalsın diye). 365 günlük **10.000 farklı yıl** üretildi. Bu yöntemin adı block bootstrap (`expected.py` ile aynı).
3. Her senaryoda sermaye zirveden %20 düştüğü gün kill switch **kilitlenir** ve o senaryo düz devam eder (yeni işlem yok, R13).
4. Aynısı TrendEma ve aynı coinleri sadece tutmak (al-tut) için yapıldı. Al-tut'ta kill switch yok; satırı "kaç senaryoda %20 düşüş görülürdü" diye okunur.

## Sonuç

| | Kill switch 3 ay | 6 ay | 12 ay | 12 ay ortanca | En kötü %5 | Zarar ihtimali | En uzun "zirve altı" (ortanca) |
|---|---|---|---|---|---|---|---|
| **VolTarget** | %0,0 | %0,1 | **%1,1** | **+%22,9** | **-%4,0** | **%8** | 132 gün |
| TrendEma | %0,2 | %3,1 | %12,2 | +%23,3 | -%14,5 | %17 | 147 gün |
| Al-tut (aynı coinler) | (%20 düşüş: %79) | (%96) | (%99,8) | +%28,5 | -%65,0 | %37 | 189 gün |

## Kaan için sade dille

- Geçmiş tekrar ederse VolTarget'in tipik yılı **+%23 civarı**. 20 yıldan 1'i **-%4 veya daha kötü** olur; **12 yılda 1** zararla kapanır.
- Kill switch'e çarpma ihtimali **yılda ~%1**. TrendEma'da bu %12. Fark, oynak coinde küçük pozisyon (VolTarget) sayesinde.
- Sadece coin tutsaydık getiri biraz daha yüksek olurdu (+%28), ama 20 yılda 1, **-%65**; hemen her yıl bir noktada %20'den fazla düşüş.
- Bot genelde **4 aya yakın** (132 gün) bir süre önceki zirvesinin altında kalabiliyor. Bu normal; panik sebebi değil.

## Bu sayılara neden fazla güvenmemeli (önemli)

- **Tahmin değil:** Bu, geçmişin karıştırılmış hali. Gelecek, geçmişte hiç görülmemiş bir şey getirebilir.
- **İyimser olma ihtimali yüksek:** Geçmiş olarak VolTarget'in **iyi** olduğu dönemler kullanıldı (validation + early). VolTarget zaten bu dönemlerde iyi olduğu için seçildi. Final test dönemi (2025-08 → 2026-10) bu geçmişte **yok**; o dönemde TrendEma -%20 ile kill switch'e çarpmıştı. Gerçek risk bu tablodan büyük olabilir.
- **İstatistiksel kanıt yok:** Çoklu deneme düzeltmesinden sonra (Deflated Sharpe, N = 94) VolTarget'in üstünlüğü kanıtlanmış değil (DSR < 0,95).
- **Kill switch yaklaşık:** Gerçek kill switch kapanmış işlemlere bakıyor, bu simülasyon açık işlemler dahil günlük değere. Günlük değer genelde daha derine düştüğü için kill switch ihtimali burada biraz **yüksek** çıkar (temkinli yön).
- **Asıl hakem ileriye dönük gerçek fiyatlar:** dry-run, sonra demo. Günlük rapordaki "beklenen aralıkta mı" satırı (`expected.py`) bunu izliyor.

## Kod

- `scripts/forward_risk.py`:
  - `latch_paths`: kill switch gününü bulur ve sonrasını düzleştirir.
  - `stats`: kill ihtimali (3/6/12 ay), ortanca, en kötü %5, zarar ihtimali, en uzun zirve altı süre.
  - `longest_underwater`: en uzun kesintisiz zirve altı süresi.
- Testler (`tests/test_forward_risk.py`) kilidin doğru gün devreye girdiğini ve sonrasının düz kaldığını, ufuk sayımını ve rapora giden satırı kontrol ediyor.

## Anlaman gerekenler

- **Bootstrap:** Elindeki tek geçmişi parçalara bölüp yeniden dizerek "olabilecek başka yıllar" üretmek. Blok kullanmak, kötü haftaların arka arkaya gelme eğilimini korur.
- **Ortanca ile en kötü %5 birlikte okunur:** Tek bir "beklenen getiri" sayısı riski gizler.
- **Seçim yanlılığı:** Bir kuralı iyi göründüğü veriden seçip aynı veriyle geleceğini tahmin edersen, sonuç iyimser çıkar.

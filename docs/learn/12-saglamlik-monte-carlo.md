# Öğretici kart 12: TrendEma'nın sağlamlık sınavı (sayı komşuları + Monte Carlo)

24 denemeden sonra en iyi kural hâlâ TrendEma. Artık yeni kural aramayı bırakıp şunu soruyoruz: **TrendEma'ya ne kadar güvenebiliriz?**

## 1. Sayı komşuları (`trend_ema_sensitivity.py`)

TrendEma 3 sayıya dayanıyor: 20, 50 ve 200. Her komşu bu sayılardan sadece birini %20-25 oynatıyor:

| Komşu | Hızlı | Yavaş | Trend |
|---|---|---|---|
| TrendEma | 20 | 50 | 200 |
| EmaFast15 / EmaFast25 | **15 / 25** | 50 | 200 |
| EmaSlow40 / EmaSlow60 | 20 | **40 / 60** | 200 |
| EmaTrend150 / EmaTrend250 | 20 | 50 | **150 / 250** |

Nasıl okuyacağız: Komşular TrendEma'ya yakınsa kural sağlam, uzaksa şanslı. **En iyi komşuya geçmeyeceğiz**, çünkü o ezberleme olur. (Aynı mantık kart 05'te de var.)

## 2. Monte Carlo (`scripts/montecarlo.py`)

Backtest bize işlemlerin **tek bir sırasını** gösteriyor. Aynı işlemler başka sırayla gelseydi, kötü işlemler art arda gelip düşüş çok daha derin olabilirdi.

Adımlar:
1. Her işlemin kârı, o anki hesabın yüzdesine çevrilir. Örnek: 1000'lik hesapta +100 = %10.
2. Bu yüzdelerden rastgele, tekrar seçmeye izin vererek (bootstrap) aynı sayıda işlem çekilir. Yeni bir "alternatif geçmiş" oluşur.
3. Bu 2000 kere yapılır. Her alternatif geçmişte en büyük düşüş ve yıllık büyüme hesaplanır.
4. Rastgelelik sabit tohumla (`SEED = 42`) yapılır. Aynı veri her çalıştırmada aynı cevabı verir.

Tablodaki sütunlar:

| Sütun | Anlamı |
|---|---|
| `DD med` | Tipik en büyük düşüş |
| `DD 95%` | 100 alternatif geçmişin 95'inde düşüş bundan küçük. "Kötü ama gerçekçi" senaryo |
| `DD worst` | 2000'in en kötüsü |
| `CAGR 5%` | Kötü şanslı senaryoda yıllık büyüme |
| `P(loss)` | Dönem sonunda zararda bitme olasılığı |
| `P(DD>=20%)` | Kill switch'in tetiklenme olasılığı |

Not: Burada düşüş sadece kapanmış işlemlerden hesaplanır, saatlik değil. Yani gerçekte biraz daha kötü olabilir.

## Komutlar

```
python3 scripts/ft.py backtest --slice train --no-kill-switch --strategy EmaFast15 EmaFast25 EmaSlow40 EmaSlow60 EmaTrend150 EmaTrend250
python3 scripts/ft.py report --slice train --no-kill-switch --strategy TrendEma EmaFast15 EmaFast25 EmaSlow40 EmaSlow60 EmaTrend150 EmaTrend250
python3 scripts/ft.py montecarlo --slice train --no-kill-switch --strategy TrendEma
```

## Testler (10 yeni, toplam 155)

- Her komşu tek bir sayıyı %20-25 değiştiriyor ve risk kurallarını koruyor.
- İşlem yüzdeleri doğru: +100 / 1000 = %10, sonra -110 / 1100 = -%10.
- Aynı tohumla aynı sonuç çıkıyor. Düşüş ve büyüme sıralamaları mantıklı.
- Hep zararlı işlemler hep zararla bitiyor.
- Test dilimi bu komutta da kapalı.

---

## Anlaman gerekenler

1. Sayılar biraz oynayınca çöken kural güvenilmez.
2. Tek bir geçmiş şanslı ya da şanssız olabilir; Monte Carlo "olası kötü günü" gösterir.
3. Bu sınavlar kuralı değiştirmek için değil, ne kadar güveneceğimizi ölçmek için.

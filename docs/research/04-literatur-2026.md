# Araştırma 04: Yeni literatür, "yükselişte az coinde kalma" sorunu (2026-11-01)

Sorun: Adaylarımız (TrendEma, BtcRisingGap) paranın ortalama %10-20'sini coinde tutuyor. Düşüşte bu iyi, yükselişte al-tut ve DCA'nın gerisinde kalıyor (validation 2024-25).

## Okunanlar
- Bui & Nguyen (2026), "Systematic Trend-Following with Adaptive Portfolio Construction", arXiv:2602.11708. 6 saatlik mum, momentum girişi + ATR takip eden stop (α=2,5), aylık parametre optimizasyonu, **%70 long / %30 short, vadeli işlemler (perpetual)**. 2022-2024 Calmar 3,18. Ama ayı piyasasında long tarafı negatif (Sharpe -0,31). Kazancın önemli kısmı short bacaktan geliyor. Sharpe hesabı tablo ile tutmuyor (2,14 vs 2,41). Tek grup, tekrar edilmemiş.
- Zarattini, Pagani, Barbon (2025), "Catching Crypto Trends": tur 4'te denendi (TrendDonchianEnsemble), train'de FAIL.

## Bize uygun olan / olmayan
| Fikir | Durum |
|---|---|
| Short bacak | Yasak (sadece spot, kaldıraç/futures yok) |
| Aylık yeniden optimizasyon | Bizim walk-forward testimiz "en iyiyi seç"in sabit kurala yenildiğini gösterdi |
| ATR takip eden stop | Tur 1 TrendEmaAtrTrail, FAIL |
| Long-only trend takibi ayıda zararlı | Bizim final test bulgumuzla aynı |

## Sonuç
Yeni literatür, yalnız-long spot trend takibinin yükselişte al-tut'u yakalayamayacağını, düşüşte ise korumanın ana katkı olduğunu doğruluyor. Yükselişte daha çok coinde kalmak için tek yol pozisyon büyüklüğü / toplam yatırım oranı. Bu da risk kuralı (R2 %1 risk, R4 %25, R7 nakit) değişikliği demek. Kural gereği bu Kaan'ın kararı; ancak geçmiş veride kanıtlanırsa önerilecek.

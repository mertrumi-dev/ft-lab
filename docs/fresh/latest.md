# Günlük rapor 2026-11-01

Sadece ölçüm. Kurallar bu rapora bakılarak değiştirilmez. Yatırım tavsiyesi değildir.

## 1. Bot sağlığı

- Çalışıyor mu: ft-lab Up 21 hours
- Kendi kodundaki hata: 0 (bağlantı hatası: 259)
- İşlemler: 0 açık, 0 kapanmış, gerçekleşen kâr/zarar +0.00 USDT
- Kill switch: zirveden düşüş %0.0 (sınır %20)
- Faz 0: NOT YET: running 17.2h without a gap, needs 24h

## 2. Botun 5 coini şu an (1 saatlik grafik)

| Coin | Durum | EMA200'e uzaklık | Pozisyon boyutu |
|---|---|---|---|
| BNB/USDT | EMA200 altında (bekliyor) | -1.6% | 100% |
| BTC/USDT | EMA200 altında (bekliyor) | -1.9% | 100% |
| ETH/USDT | EMA200 altında (bekliyor) | -2.0% | 100% |
| XRP/USDT | EMA200 altında (bekliyor) | -2.5% | 100% |
| SOL/USDT | EMA200 altında (bekliyor) | -4.4% | 100% |

## 3. Piyasa genişliği (havuzdaki coinlerin yüzde kaçı EMA200 üstünde)

- 2026-11-01: %13 (8 coin trendde, 0 alım sinyali)

## 4. Taze veri (testten sonraki gerçek fiyatlar), 5 coin

Getiri ve düşüş, taze dilimin başından bugüne. 50'den az işlem = henüz anlamlı değil.

```
Buy & hold                    -    -13.5%   -82.8%   17.3%   -4.78
Weekly DCA (savings)          -    -10.0%   -72.4%   12.0%   -6.04
Grid bot (Pionex-style)      83     -3.9%   -38.0%    6.1%   -6.24
DCA bot (3Commas-style)      13     -3.3%   -33.8%    4.5%   -7.50  <50 trades
TSMOM (ours, daily, vol-scaled)      7     -7.7%   -62.3%   11.7%   -5.33  <50 trades
TrendEma                     17     -3.4%   -34.0%    3.8%   -9.05  <50 trades
TrendEmaVolTarget            17     -3.3%   -33.3%    3.7%   -9.08  <50 trades
TrendEmaVolTarget2h           9     -2.3%   -24.5%    3.0%   -8.25  <50 trades
VolTarget 1h+2h 50/50        26     -2.8%   -29.0%    3.3%   -8.78  <50 trades
```

İzleme (altın dahil 6 coin): 
```
TrendEmaVolTarget            20     -3.5%   -34.9%    3.9%   -9.05  <50 trades
```

## 5. Emir kalitesi

```
tradesv3.dryrun.sqlite: no orders yet (the bot has not traded). Nothing to measure.
Read-only report. Use it with docs/research/05-maliyet-onerisi.md (post-only decision).
$ docker compose run --rm -v /Users/mert/ft-lab/scripts:/freqtrade/scripts:ro --entrypoint python freqtrade /freqtrade/scripts/execution.py
```

## 6. Yapay zeka grafik yorumları

- Kaydedilen yorum: 5, puanlanan: 0. Bota bağlanması için önce 50+ puanlanmış tahminde yazı-tura ve 'hep yukarı'yı geçmesi gerekiyor.

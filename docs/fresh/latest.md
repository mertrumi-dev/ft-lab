# Günlük rapor 2026-11-04

Sadece ölçüm. Kurallar bu rapora bakılarak değiştirilmez. Yatırım tavsiyesi değildir.

## 1. Bot sağlığı

- Çalışıyor mu: not running
- Kendi kodundaki hata: 0 (bağlantı hatası: 0)
- En uzun bağlantısız süre: yok
- İşlemler: 0 açık, 0 kapanmış, gerçekleşen kâr/zarar +0.00 USDT
- Kill switch: zirveden düşüş şu an %0.0, en kötü %0.0 (sınır %20)
- Faz 0: FAIL: no heartbeat in the log

## 2. Botun 5 coini şu an (1 saatlik grafik)

| Coin | Durum | EMA200'e uzaklık | Pozisyon boyutu |
|---|---|---|---|
| ETH/USDT | trendde (yukarı) | +5.4% | 100% |
| XRP/USDT | trendde (yukarı) | +2.5% | 100% |
| BTC/USDT | trendde (yukarı) | +2.3% | 100% |
| BNB/USDT | trendde (yukarı) | +0.6% | 100% |
| SOL/USDT | EMA200 altında (bekliyor) | -0.9% | 100% |

## 3. Piyasa genişliği (havuzdaki coinlerin yüzde kaçı EMA200 üstünde)

- 2026-11-01: %8 (4 coin trendde, 0 alım sinyali)
- 2026-11-02: %2 (1 coin trendde, 0 alım sinyali)
- 2026-11-04: %41 (25 coin trendde, 0 alım sinyali)

## 4. Taze veri (testten sonraki gerçek fiyatlar), 5 coin

Getiri ve düşüş, taze dilimin başından bugüne. Yıllık = o hızla bir yıl sürseydi. 50'den az işlem = henüz anlamlı değil.

```
Bot                                   İşlem    Getiri    Yıllık   MaxDD  Calmar
Buy & hold                                -    -13.6%    -80.3%   17.3%   -4.63
Weekly DCA (savings)                      -     -8.6%    -63.1%   10.2%   -6.20
Grid bot (Pionex-style)                  88     -3.8%    -35.1%    6.1%   -5.76
DCA bot (3Commas-style)                  14     -3.4%    -31.9%    4.5%   -7.07  <50 işlem
TSMOM (ours, daily, vol-scaled)           7     -7.7%    -58.8%   11.7%   -5.03  <50 işlem
TrendEma                                 17     -3.4%    -31.4%    3.8%   -8.37  <50 işlem
TrendEmaVolTarget                        17     -3.3%    -30.8%    3.7%   -8.40  <50 işlem
TrendEmaVolTargetAdx                      9     -1.8%    -18.3%    2.2%   -8.24  <50 işlem
TrendEmaVolTarget2h                       9     -2.3%    -22.5%    3.0%   -7.59  <50 işlem
VolTarget 1h+2h 50/50                    26     -2.8%    -26.8%    3.3%   -8.10  <50 işlem
```

VolTarget beklenen aralıkta mı? 33 gün, getiri -3.3% (beklenen aralık %5-%95: -4.3% .. +12.0%, yüzdelik 10%) -> beklenen aralıkta

İleriye risk: VolTarget önümüzdeki 12 ay (geçmişten 10.000 senaryo): ortanca +23%, kötü %5'lik dilim -4%, zarar ihtimali %8, kill switch ihtimali %1 (tahmin değil, geçmişin tekrar karıştırılması)
Stres (kötü dönem dahil): VolTarget (kötü dönem dahil) önümüzdeki 12 ay (geçmişten 10.000 senaryo): ortanca +13%, kötü %5'lik dilim -10%, zarar ihtimali %20, kill switch ihtimali %2 (tahmin değil, geçmişin tekrar karıştırılması)

İzleme (altın dahil 6 coin): 
```
Bot                                   İşlem    Getiri    Yıllık   MaxDD  Calmar
TrendEmaVolTarget                        20     -3.5%    -32.3%    3.9%   -8.37  <50 işlem
```

## 5. Emir kalitesi

```
tradesv3.adx20.dryrun.sqlite: no orders yet (the bot has not traded). Nothing to measure.
tradesv3.dryrun.sqlite: no orders yet (the bot has not traded). Nothing to measure.
tradesv3.voltarget.dryrun.sqlite: no orders yet (the bot has not traded). Nothing to measure.
Read-only report. Use it with docs/research/05-maliyet-onerisi.md (post-only decision).
```

## 6. Yapay zeka grafik yorumları

- Kaydedilen yorum: 15, puanlanan: 0. Bota bağlanması için önce 50+ puanlanmış tahminde yazı-tura ve 'hep yukarı'yı geçmesi gerekiyor.
- Puanlama: henüz puanlanacak tahmin yok (ilk: 2026-11-08, 2026-11-07 kapanışıyla), bekleyen 15

## 7. İşlemler (sade dille)

Henüz işlem yok. Botun 5 coini için bir sonraki alım şartı (1 saatlik grafik):
- BTC: fiyat EMA200 üstünde ve kısa trend zaten yukarı; yeni giriş için EMA20 önce EMA50'nin altına inip tekrar yukarı kesmeli
- ETH: fiyat EMA200 üstünde ve kısa trend zaten yukarı; yeni giriş için EMA20 önce EMA50'nin altına inip tekrar yukarı kesmeli
- SOL: fiyat EMA200'ün %0.4 altında; önce EMA200 üstüne çıkmalı, sonra EMA20 EMA50'yi yukarı kesmeli
- BNB: fiyat EMA200 üstünde ve kısa trend zaten yukarı; yeni giriş için EMA20 önce EMA50'nin altına inip tekrar yukarı kesmeli
- XRP: fiyat EMA200 üstünde ve kısa trend zaten yukarı; yeni giriş için EMA20 önce EMA50'nin altına inip tekrar yukarı kesmeli

## Sahte para botları yan yana (sadece yargı, kurallar buna göre değişmez)

| Bot | Durum | Açık | Kapanmış | Gerçekleşen K/Z | En kötü düşüş |
|---|---|---|---|---|---|
| VolTarget (ana bot) | DURMUŞ, 0 hata | 0 | 0 | +0.00 USDT | %0.0 |
| ADX20 (paralel bot) | DURMUŞ, 0 hata | 0 | 0 | +0.00 USDT | %0.0 |
50'den az kapanmış işlemle bu karşılaştırma henüz anlamlı değil.

## Ön kayıtlı fikirler (sadece yeni veride, hüküm günü gelmeden karar yok)

- F001 TrendEmaVolTargetDaily: henüz hüküm yok (2/365 gün, 363 gün kaldı)
- F002 Weekly DCA 50% + VolTarget 50%: henüz hüküm yok (2/91 gün, 89 gün kaldı)
- F003 TrendEmaVolTargetCooldown24: henüz hüküm yok (2/181 gün, 179 gün kaldı)
- F004 TrendEmaVolTargetDerisk72h: henüz hüküm yok (2/181 gün, 179 gün kaldı)
- F005 TrendEmaVolTargetAdx: henüz hüküm yok (2/181 gün, 179 gün kaldı)
- F006 TrendEmaVolTargetTakeHalf2R: henüz hüküm yok (2/181 gün, 179 gün kaldı)
- F007 TrendEmaVolTargetVolConfirm: henüz hüküm yok (2/181 gün, 179 gün kaldı)
- F008 TrendEmaVolTargetVote9: henüz hüküm yok (2/181 gün, 179 gün kaldı)
- F009 TrendEmaVolTargetLetRun: henüz hüküm yok (1/181 gün, 180 gün kaldı)
- F010 TrendEmaVolTargetFearBlock: henüz hüküm yok (1/181 gün, 180 gün kaldı)
- F011 TrendEmaVolTargetNoWeekend: henüz hüküm yok (1/181 gün, 180 gün kaldı)
- F012 TrendEmaVolTargetStableFlow: başlamadı (başlangıç 2026-11-05, hüküm 2027-05-05)
- F013 TrendEmaVolTargetAttnTrend: başlamadı (başlangıç 2026-11-05, hüküm 2027-05-05)

## 8. Grafik okuma (günlük grafik, sade dille)

**BTC — günlük grafik, son kapanmış mum 2026-11-03, kapanış 77.453,86$**
- Fiyat 20 günlük ortalamanın %3,0 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %3,3 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %1,2 üstünde: uzun vadede güçlü.
- Hareket: son 7 günde %4,3 düştü, son 30 günde %10,5 düştü, son 90 günde %19,8 yükseldi.
- Son 60 günün aralığı: en düşük 75.644,48$, en yüksek 86.620,00$.
- En yakın destek (fiyatın son düştüğü dip): 76.568,72$.
- En yakın direnç (fiyatın son döndüğü tepe): 78.189,21$.
- Oynaklık: yıllık %28,1 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 1,0 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an yeni alım yapmaz: trend zaten sürüyor; yeni giriş için kısa vadenin önce aşağı, sonra tekrar yukarı dönmesi gerekir.
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %33).

**ETH — günlük grafik, son kapanmış mum 2026-11-03, kapanış 2.274,77$**
- Fiyat 20 günlük ortalamanın %3,2 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %5,6 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %1,8 altında: uzun vadede zayıf.
- Hareket: son 7 günde %3,2 düştü, son 30 günde %16,6 düştü, son 90 günde %19,2 yükseldi.
- Son 60 günün aralığı: en düşük 2.245,54$, en yüksek 2.776,19$.
- En yakın destek (fiyatın son düştüğü dip): 2.245,54$.
- En yakın direnç (fiyatın son döndüğü tepe): 2.359,68$.
- Oynaklık: yıllık %36,0 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 0,9 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an yeni alım yapmaz: trend zaten sürüyor; yeni giriş için kısa vadenin önce aşağı, sonra tekrar yukarı dönmesi gerekir.
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %47).

**SOL — günlük grafik, son kapanmış mum 2026-11-03, kapanış 92,8300$**
- Fiyat 20 günlük ortalamanın %7,5 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %10,1 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %5,4 altında: uzun vadede zayıf.
- Hareket: son 7 günde %8,4 düştü, son 30 günde %23,7 düştü, son 90 günde %25,4 yükseldi.
- Son 60 günün aralığı: en düşük 91,9800$, en yüksek 122,15$.
- En yakın destek (fiyatın son düştüğü dip): yok: son 60 günde fiyatın altında dönülmüş bir dip yok (fiyat aralığın en altına yakın).
- En yakın direnç (fiyatın son döndüğü tepe): 102,44$.
- Oynaklık: yıllık %41,7 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 0,8 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an almaz, çünkü saatlik grafikte fiyat 200 saatlik ortalamanın altında (büyük resim aşağı).
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %55).

**BNB — günlük grafik, son kapanmış mum 2026-11-03, kapanış 698,14$**
- Fiyat 20 günlük ortalamanın %3,7 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %4,2 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %0,8 üstünde: uzun vadede güçlü.
- Hareket: son 7 günde %6,3 düştü, son 30 günde %12,2 düştü, son 90 günde %17,6 yükseldi.
- Son 60 günün aralığı: en düşük 698,14$, en yüksek 799,41$.
- En yakın destek (fiyatın son düştüğü dip): yok: son 60 günde fiyatın altında dönülmüş bir dip yok (fiyat aralığın en altına yakın).
- En yakın direnç (fiyatın son döndüğü tepe): 727,59$.
- Oynaklık: yıllık %39,9 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 1,0 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an yeni alım yapmaz: trend zaten sürüyor; yeni giriş için kısa vadenin önce aşağı, sonra tekrar yukarı dönmesi gerekir.
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %42).

**XRP — günlük grafik, son kapanmış mum 2026-11-03, kapanış 1,2767$**
- Fiyat 20 günlük ortalamanın %2,0 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %4,5 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %6,4 altında: uzun vadede zayıf.
- Hareket: son 7 günde %4,1 düştü, son 30 günde %16,0 düştü, son 90 günde %20,2 yükseldi.
- Son 60 günün aralığı: en düşük 1,2377$, en yüksek 1,5727$.
- En yakın destek (fiyatın son düştüğü dip): 1,2377$.
- En yakın direnç (fiyatın son döndüğü tepe): 1,3313$.
- Oynaklık: yıllık %44,3 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 0,6 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an yeni alım yapmaz: trend zaten sürüyor; yeni giriş için kısa vadenin önce aşağı, sonra tekrar yukarı dönmesi gerekir.
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %52).

Geçmişin okunması, tahmin değil, yatırım tavsiyesi değil.

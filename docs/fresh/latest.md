# Günlük rapor 2026-11-02

Sadece ölçüm. Kurallar bu rapora bakılarak değiştirilmez. Yatırım tavsiyesi değildir.

## 1. Bot sağlığı

- Çalışıyor mu: ft-lab Up About an hour
- Kendi kodundaki hata: 0 (bağlantı hatası: 0)
- En uzun bağlantısız süre: yok
- İşlemler: 0 açık, 0 kapanmış, gerçekleşen kâr/zarar +0.00 USDT
- Kill switch: zirveden düşüş şu an %0.0, en kötü %0.0 (sınır %20)
- Faz 0: NOT YET: running 1.2h without a gap, needs 24h

## 2. Botun 5 coini şu an (1 saatlik grafik)

| Coin | Durum | EMA200'e uzaklık | Pozisyon boyutu |
|---|---|---|---|
| BTC/USDT | EMA200 altında (bekliyor) | -1.1% | 100% |
| ETH/USDT | EMA200 altında (bekliyor) | -1.3% | 100% |
| BNB/USDT | EMA200 altında (bekliyor) | -1.5% | 100% |
| XRP/USDT | EMA200 altında (bekliyor) | -2.2% | 100% |
| SOL/USDT | EMA200 altında (bekliyor) | -4.3% | 100% |

## 3. Piyasa genişliği (havuzdaki coinlerin yüzde kaçı EMA200 üstünde)

- 2026-11-01: %8 (4 coin trendde, 0 alım sinyali)

## 4. Taze veri (testten sonraki gerçek fiyatlar), 5 coin

Getiri ve düşüş, taze dilimin başından bugüne. Yıllık = o hızla bir yıl sürseydi. 50'den az işlem = henüz anlamlı değil.

```
Bot                                   İşlem    Getiri    Yıllık   MaxDD  Calmar
Buy & hold                                -    -13.1%    -80.9%   17.3%   -4.67
Weekly DCA (savings)                      -     -9.7%    -69.8%   12.0%   -5.83
Grid bot (Pionex-style)                  84     -3.7%    -35.6%    6.1%   -5.83
DCA bot (3Commas-style)                  13     -3.2%    -31.7%    4.5%   -7.04  <50 işlem
TSMOM (ours, daily, vol-scaled)           7     -7.7%    -61.1%   11.7%   -5.23  <50 işlem
TrendEma                                 17     -3.4%    -33.1%    3.8%   -8.81  <50 işlem
TrendEmaVolTarget                        17     -3.3%    -32.4%    3.7%   -8.84  <50 işlem
TrendEmaVolTarget2h                       9     -2.3%    -23.8%    3.0%   -8.02  <50 işlem
VolTarget 1h+2h 50/50                    26     -2.8%    -28.2%    3.3%   -8.54  <50 işlem
```

VolTarget beklenen aralıkta mı? 31 gün, getiri -3.3% (beklenen aralık %5-%95: -4.2% .. +11.6%, yüzdelik 10%) -> beklenen aralıkta

İleriye risk: VolTarget önümüzdeki 12 ay (geçmişten 10.000 senaryo): ortanca +23%, kötü %5'lik dilim -4%, zarar ihtimali %8, kill switch ihtimali %1 (tahmin değil, geçmişin tekrar karıştırılması)
Stres (kötü dönem dahil): VolTarget (kötü dönem dahil) önümüzdeki 12 ay (geçmişten 10.000 senaryo): ortanca +13%, kötü %5'lik dilim -10%, zarar ihtimali %20, kill switch ihtimali %2 (tahmin değil, geçmişin tekrar karıştırılması)

İzleme (altın dahil 6 coin): 
```
Bot                                   İşlem    Getiri    Yıllık   MaxDD  Calmar
TrendEmaVolTarget                        20     -3.5%    -33.9%    3.9%   -8.81  <50 işlem
```

## 5. Emir kalitesi

```
tradesv3.adx20.dryrun.sqlite: no orders yet (the bot has not traded). Nothing to measure.
tradesv3.dryrun.sqlite: no orders yet (the bot has not traded). Nothing to measure.
tradesv3.voltarget.dryrun.sqlite: no orders yet (the bot has not traded). Nothing to measure.
Read-only report. Use it with docs/research/05-maliyet-onerisi.md (post-only decision).
```

## 6. Yapay zeka grafik yorumları

- Kaydedilen yorum: 5, puanlanan: 0. Bota bağlanması için önce 50+ puanlanmış tahminde yazı-tura ve 'hep yukarı'yı geçmesi gerekiyor.
- Puanlama: henüz puanlanacak tahmin yok (ilk: 2026-11-08, 2026-11-07 kapanışıyla), bekleyen 5

## 7. İşlemler (sade dille)

Henüz işlem yok. Botun 5 coini için bir sonraki alım şartı (1 saatlik grafik):
- BTC: fiyat EMA200'ün %1.1 altında; önce EMA200 üstüne çıkmalı, sonra EMA20 EMA50'yi yukarı kesmeli
- ETH: fiyat EMA200'ün %1.3 altında; önce EMA200 üstüne çıkmalı, sonra EMA20 EMA50'yi yukarı kesmeli
- SOL: fiyat EMA200'ün %4.3 altında; önce EMA200 üstüne çıkmalı, sonra EMA20 EMA50'yi yukarı kesmeli
- BNB: fiyat EMA200'ün %1.5 altında; önce EMA200 üstüne çıkmalı, sonra EMA20 EMA50'yi yukarı kesmeli
- XRP: fiyat EMA200'ün %2.2 altında; önce EMA200 üstüne çıkmalı, sonra EMA20 EMA50'yi yukarı kesmeli

## Sahte para botları yan yana (sadece yargı, kurallar buna göre değişmez)

| Bot | Durum | Açık | Kapanmış | Gerçekleşen K/Z | En kötü düşüş |
|---|---|---|---|---|---|
| VolTarget (ana bot) | çalışıyor, 0 hata | 0 | 0 | +0.00 USDT | %0.0 |
| ADX20 (paralel bot) | çalışıyor, 0 hata | 0 | 0 | +0.00 USDT | %0.0 |
50'den az kapanmış işlemle bu karşılaştırma henüz anlamlı değil.

## Ön kayıtlı fikirler (sadece yeni veride, hüküm günü gelmeden karar yok)

- F001 TrendEmaVolTargetDaily: henüz hüküm yok (0/365 gün)
- F002 Weekly DCA 50% + VolTarget 50%: henüz hüküm yok (0/91 gün)
- F003 TrendEmaVolTargetCooldown24: henüz hüküm yok (0/181 gün)
- F004 TrendEmaVolTargetDerisk72h: henüz hüküm yok (0/181 gün)
- F005 TrendEmaVolTargetAdx: henüz hüküm yok (0/181 gün)
- F006 TrendEmaVolTargetTakeHalf2R: henüz hüküm yok (0/181 gün)
- F007 TrendEmaVolTargetVolConfirm: henüz hüküm yok (0/181 gün)
- F008 TrendEmaVolTargetVote9: henüz hüküm yok (0/181 gün)
- F009 TrendEmaVolTargetLetRun: başlamadı (başlangıç 2026-11-03, hüküm 2027-05-03)

## 8. Grafik okuma (günlük grafik, sade dille)

**BTC — günlük grafik, son kapanmış mum 2026-11-01, kapanış 78.354,00$**
- Fiyat 20 günlük ortalamanın %2,7 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %2,5 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %2,4 üstünde: uzun vadede güçlü.
- Hareket: son 7 günde %2,2 düştü, son 30 günde %7,3 düştü, son 90 günde %23,4 yükseldi.
- Son 60 günün aralığı: en düşük 75.644,48$, en yüksek 86.620,00$.
- En yakın destek (fiyatın son düştüğü dip): 76.568,72$.
- En yakın direnç (fiyatın son döndüğü tepe): 81.343,50$.
- Oynaklık: yıllık %28,5 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 0,9 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an almaz, çünkü saatlik grafikte fiyat 200 saatlik ortalamanın altında (büyük resim aşağı).
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %32).

**ETH — günlük grafik, son kapanmış mum 2026-11-01, kapanış 2.275,31$**
- Fiyat 20 günlük ortalamanın %4,0 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %6,1 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %1,8 altında: uzun vadede zayıf.
- Hareket: son 7 günde %2,3 düştü, son 30 günde %14,7 düştü, son 90 günde %22,3 yükseldi.
- Son 60 günün aralığı: en düşük 2.245,54$, en yüksek 2.776,19$.
- En yakın destek (fiyatın son düştüğü dip): yok: son 60 günde fiyatın altında dönülmüş bir dip yok (fiyat aralığın en altına yakın).
- En yakın direnç (fiyatın son döndüğü tepe): 2.359,68$.
- Oynaklık: yıllık %36,6 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 0,9 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an almaz, çünkü saatlik grafikte fiyat 200 saatlik ortalamanın altında (büyük resim aşağı).
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %44).

**SOL — günlük grafik, son kapanmış mum 2026-11-01, kapanış 94,5300$**
- Fiyat 20 günlük ortalamanın %7,4 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %9,2 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %3,8 altında: uzun vadede zayıf.
- Hareket: son 7 günde %6,8 düştü, son 30 günde %20,3 düştü, son 90 günde %28,5 yükseldi.
- Son 60 günün aralığı: en düşük 94,5300$, en yüksek 122,15$.
- En yakın destek (fiyatın son düştüğü dip): yok: son 60 günde fiyatın altında dönülmüş bir dip yok (fiyat aralığın en altına yakın).
- En yakın direnç (fiyatın son döndüğü tepe): 102,44$.
- Oynaklık: yıllık %42,0 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 0,8 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an almaz, çünkü saatlik grafikte fiyat 200 saatlik ortalamanın altında (büyük resim aşağı).
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %52).

**BNB — günlük grafik, son kapanmış mum 2026-11-01, kapanış 712,69$**
- Fiyat 20 günlük ortalamanın %2,5 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %2,5 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %2,9 üstünde: uzun vadede güçlü.
- Hareket: son 7 günde %3,5 düştü, son 30 günde %7,2 düştü, son 90 günde %20,9 yükseldi.
- Son 60 günün aralığı: en düşük 698,46$, en yüksek 799,41$.
- En yakın destek (fiyatın son düştüğü dip): 712,06$.
- En yakın direnç (fiyatın son döndüğü tepe): 727,59$.
- Oynaklık: yıllık %41,0 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 1,0 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an almaz, çünkü saatlik grafikte fiyat 200 saatlik ortalamanın altında (büyük resim aşağı).
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %42).

**XRP — günlük grafik, son kapanmış mum 2026-11-01, kapanış 1,2507$**
- Fiyat 20 günlük ortalamanın %4,6 altında: kısa vadede zayıf.
- Fiyat 50 günlük ortalamanın %6,9 altında: orta vadede zayıf.
- Fiyat 200 günlük ortalamanın %8,4 altında: uzun vadede zayıf.
- Hareket: son 7 günde %3,5 düştü, son 30 günde %15,8 düştü, son 90 günde %16,3 yükseldi.
- Son 60 günün aralığı: en düşük 1,2377$, en yüksek 1,5727$.
- En yakın destek (fiyatın son düştüğü dip): 1,2377$.
- En yakın direnç (fiyatın son döndüğü tepe): 1,3313$.
- Oynaklık: yıllık %44,5 (son 30 gün).
- Son 30 günde işlem hacmi normalin (90 günlük ortalama) 0,6 katı.
Botun gözüyle (1 saatlik grafik, yukarıdaki günlük görünümden daha kısa vadeli):
- Bot şu an almaz, çünkü saatlik grafikte fiyat 200 saatlik ortalamanın altında (büyük resim aşağı).
- Alırsa pozisyon boyutu normalin %100'i olur (saatlik oynaklık yıllık %50).

Geçmişin okunması, tahmin değil, yatırım tavsiyesi değil.

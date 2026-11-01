# Proje günlüğü

Her faz sonunda: ne yaptık, ne öğrendik, ne işe yaramadı. Deneme sayıları da buraya.

## Faz 0: Kurulum (başladı 2026-10-31)

- Freqtrade 2026.10, Docker Compose, SampleStrategy, dry-run 1000 USDT sahte cüzdan.
- Pair'ler: BTC, ETH, SOL, BNB, XRP / USDT.
- Geçiş kriteri: 24 saat kesintisiz dry-run, loglarda ERROR yok.

### 2026-10-31: örnek strateji kaldırıldı

- Kaan'ın kararı: hazır örnek yok, sadece kendi kurallarımız. `SampleStrategy` silindi.
- İlk kendi stratejimiz `TrendEma` (EMA20/50 kesişimi + EMA200 trend filtresi, 1h) ve risk kural kitabı v1 (`docs/risk-rules.md`) yazıldı.
- 25 test (güvenlik + strateji + risk kilitleri). Testler bilerek bozulan kodu yakalıyor (filtre silme, stoploss gevşetme).
- 24 saatlik dry-run sayacı TrendEma ile yeniden başlıyor.
- Deneme sayacı: backtest 0, hyperopt 0 (henüz veri yok).
- Risk kitabı v1.1: günlük/haftalık kayıp limiti ve LowProfitPairs çıkarıldı (R9 ve kill switch ile örtüşüyordu, fazla ayar). Başarı ölçütü risk-ayarlı oldu (Calmar).
- Araştırma 01: profesyonel trend takipçilerinden denenecekler listesi (docs/research/01-...). Bota henüz eklenmedi; Faz 2'de tek tek ölçülecek.
- Faz 1 araçları önceden yazıldı (bota dokunmadan): splits.py (train 2021-01-01..2024-06-13, validation ..2025-08-07, test ..2026-10-01), benchmark.py, ft.py (test dilimi kilidi, hyperopt sadece train, deneme kaydı). 38 test.
- Araştırma 02: açık kaynak botlar ve kazananlar (docs/research/02-...). NFI gibi hazır stratejiler kurallarımıza uymuyor; tek gerçekçi yol risk kontrollü trend takibi. Backtest'e --enable-protections eklendi.
- 4 deneme stratejisi yazıldı (ATR stop, takip eden stop çıkışı, 4h, kırılım girişi), her biri tek değişiklik. ft.py birden fazla stratejiyi yan yana backtest ediyor. 49 test.
- 2026-10-31 gece: geçmiş veri Kaan'ın Mac'inde indirildi (5 pair, 1h 53.307 mum, 4h 13.331 mum, 2020-10'dan). ft.py: stratejiler timeframe'e göre gruplanıyor (Freqtrade tek run'da tek timeframe), `--strategy all`, `benchmark` ve `report` Docker içinde (Mac'te Python kurulumu gerekmez). report.py: başarı kuralına göre PASS/FAIL. 56 test.
- 2026-10-31 23:43 UTC: İLK SONUÇ (train, 5 strateji): TrendEma PASS (Calmar 2,99 vs al-tut 1,69, DD %14,8, 638 işlem). ATR/4h/kırılım FAIL. Ayrıntı: docs/results.md. Sıradaki: TrendEma validation.
- Validation #1: TrendEma FAIL kıl payı (Calmar 1,90 vs al-tut 2,11), PF train ile aynı (1,62 vs 1,63). Sıradaki: yeni iyileştirmeler sadece train'de, sonra validation #2.
- Tur 2 deneme stratejileri (sadece train'de denenecek): TrendEmaAtrWide (stop 5×ATR), TrendEmaSlow (EMA50/200 + EMA600), TrendEmaMulti (3 ortalama çifti oylaması), TrendEmaBtc (BTC EMA200 üstündeyken al). Öğretici kart 04. 65 test; yeni testler TrendEmaBtc'de gerçek bir hata yakaladı (`self.dp` Freqtrade dışında yok → `getattr`).
- Dürüstlük notu: tur 2 fikirleri validation #1 sonucunu gördükten sonra yazıldı. Bu serbest (validation seçim için var), ama her validation bakışı o dilimi biraz "ezberletir". Validation bakışı sayacı tutuluyor; 3-4 bakıştan sonra validation da güvenilmez sayılmalı.
- Tur 2 train sonucu: hiçbiri TrendEma'yı (2,99) geçmedi. En yakın TrendEmaSlow (2,83, PF 2,08, 215 işlem). Validation #2'ye sadece TrendEmaSlow giriyor. Sayaç: train 9, validation 1.
- 2026-11-01 00:00 UTC: Validation #2: TrendEmaSlow PASS (Calmar 3,32 vs al-tut 2,11, DD %9,7, 71 işlem, PF 2,07 ≈ train 2,08). İlk train+validation kazananı. Sayı sağlamlığı için 6 komşu sınıf (SlowFast40/60, SlowSlow150/250, SlowTrend450/750) yazıldı, sadece train'de çalışacak. TrendEmaSlow startup 1200→1500 (komşulardaki EMA750 için). 77 test.
- Sayı sağlamlığı (train): 6 komşudan 5'i PASS (Calmar 1,85-3,69), SlowSlow150 FAIL (1,25). Kural geniş bir bölgede çalışıyor; hızlı tarafa kayınca zayıflıyor. En iyi komşuya geçilmedi. Karar: 24h kontrolünden sonra dry-run TrendEmaSlow'a geçecek. Sayaç: train 15, validation 2, test 0.
- Sağlamlık araçları (Faz 3'ün başı, kural seçimi değil güven ölçümü): `--universe wide` (Ocak 2021'in en büyük ~25 coininden 15'i, scripts/universe.py) ve `--fee-stress` (komisyon %0,3). report.py artık sadece aynı dilim + aynı coin grubu + aynı komisyonla alınmış sonuçları aynı tabloya koyuyor. Öğretici kart 06. 83 test.
- Sağlamlık sonuçları: wide (14 coin) TrendEma 1,75 / Slow 1,21 vs al-tut 0,49, ikisi PASS; 2 kat komisyon TrendEma 1,97 / Slow 2,18 vs 1,69, ikisi PASS. Düşüşü ~%20 çıkan sonuçlarda kill switch tetiklenmiş olabilir; rapora 'Last trade' sütunu ve kill switch işareti eklendi. 84 test.
- 2026-11-01: KRİTİK BULGU. Kill switch backtest'te tetiklenince dönemin geri kalanında alım yok; 14 coin testinde TrendEma Temmuz 2021'de durdu. Önceki 7 sonuç yarıda kesilmiş. Araştırma için sadece backtest'te kapatılabilen anahtar eklendi (`--no-kill-switch`, dry-run/canlıda her zaman açık, testle zorunlu). Öğretici kart 07. 101 test.
- Kill switch kapalı yeniden ölçüm: ana 5 coinde TrendEma/Slow aynı (hiç çarpmamışlar); Multi 2,31 (DD %23). 14 coinde TrendEma 0,83 (DD %37,7), Slow 0,41 FAIL (DD %41,8). Önceki wide PASS'leri kill switch'in botu 2022'den önce durdurmasından geliyordu. Slow dry-run geçişi ertelendi. Ders: altcoinlerde 2022 ayı piyasası kuralı ağır yaralıyor; piyasa rejimi (BTC) filtresi bir sonraki hipotez.
- 14 coin + BTC filtresi: DD %37,7 → %21,0, getiri +156% → +82%, Calmar 0,90 (TrendEma 0,83). Filtre düşüşte koruyor ama kazancı da kesiyor. Kural değişmedi.
- Yıl yıl rapor (`report --by-year`, `--strategy` filtresi): eski sonuçları yıllara böler, yeni deneme değil. Öğretici kart 08. 106 test.
- Rapor artık strateji düşüşünü saat saat, açık işlemler dahil ölçüyor (scripts/equity.py, al-tut ile aynı yöntem); Calmar ve PASS/FAIL buna göre. 'In coins' = paranın ortalama ne kadarı coinde. Kill switch işareti hâlâ kapanmış işlem düşüşüne bakıyor. 110 test.
- Saatlik ölçümle: TrendEmaSlow validation 1,62 → FAIL (önceki 3,32 iyimser ölçümdendi). Hiçbir strateji train+validation geçmiyor. Ortalama yatırım oranı ~%16. Tur 3 (ADX, uzun trend) train'de koşuyor.
- Tur 3: ADX (1,28) ve LongTrend (2,25) 5 coinde TrendEma'yı (2,69) geçmedi; LongTrend 14 coinde en iyi (0,98). Giriş filtreleri hep yatırım oranını düşürüyor. Sayaç: train 17 strateji denemesi, wide 5, validation 2, test 0.
- %2 risk: Calmar ~aynı (3,06 kill kapalı / 2,68 açık, Ocak 2022'de durdu); canlı risk %1 kalıyor. Araştırma: Catching Crypto Trends (2025) → günlük, çok pencereli Donchian topluluğu + oynaklık hedefleme + hacimle coin seçimi. Dry-run logunda 249 websocket/DNS hatası (çoğu 31 Eki 18-19 UTC); Faz 0 kriteri tartışmalı, 24h kontrolünde incelenecek.
- Tur 3b (Mac oturumu, branch mac/auto-lab): TrendEmaFng (dünkü Fear&Greed >= 75 ise alma; veri alternative.me, scripts/sentiment.py) ve TrendEmaCalm (ATR% son 30 günün %80'i üstündeyse alma). Train, kill switch kapalı: 5 coinde Fng 1,48 FAIL, Calm 1,95 (TrendEma 2,70); 14 coinde Fng 0,27 FAIL, Calm 0,74 (TrendEma 0,76). İkisi de elendi. Ders: açgözlülük filtresi trendin en iyi günlerini kesiyor; giriş filtreleri hep yatırımı ve kazancı düşürüyor. Öğretici kart 11. 143 test. Sayaç: +2 train, +2 wide (train 19, wide 7, validation 2, test 0; Donchian Ensemble/Full denemeleri ana oturumun sayacında).

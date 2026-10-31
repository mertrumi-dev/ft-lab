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

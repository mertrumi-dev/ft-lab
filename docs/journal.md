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

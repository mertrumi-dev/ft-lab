# ft-lab: Claude için proje kuralları

Freqtrade tabanlı kişisel kripto trading botu. Sahibi Kaan (bilgisayar mühendisliği 1. sınıf, trading bilgisi sıfıra yakın). Amaç: doğru çalışan, al-tut'u (buy-and-hold) ölçülebilir şekilde geçmeye çalışan, overfitting'e (aşırı uydurma) karşı korunmuş bir bot yazmak ve bu işi öğrenmek.

## Kaan'ın altın kuralları (2026-10-31)

1. **Her işlemi sıfırdan anlat.** Kaan hiç kripto alıp satmadı. Hazır terim/kod verip geçme; ne olduğunu, neden yapıldığını günlük dille açıkla.
2. **Temel en sağlam şekilde, araştırarak.** Her değişikliği Kaan'a söyle; onay bekleme, uygula, ama açıkla. (Güvenlik çizgileri ve gerçek para bu kuralın dışında: onlar için her zaman önce sor.)
3. **Hız: bekleme minimum, çalışma maksimum.** Erteleme yok; Kaan'dan bir şey beklerken yapılabilecek her işi paralel yap. Ama sağlamlıktan ödün yok.

Mesajlar kısa, tek seferde tek istek. Detay dosyaya (`docs/`).

## Güvenlik çizgileri (asla esnemez)

- **Gerçek para yok.** `dry_run: false`, gerçek borsa anahtarı veya withdraw (para çekme) izinli anahtar için tek satır kod/konfig yazma, önerme. Kaan istese bile önce uyar.
- **Sırlar sadece `.env`'de.** `config.json` içindeki key/secret/password/token alanları boş kalır. `tests/test_config_safety.py` bunu zorlar.
- Commit öncesi: `python3 -m pytest` geçmeli, `git status` içinde `.env`, `user_data/data/`, `*.sqlite` olmamalı.
- **Sadece spot.** Kaldıraç (leverage) ve futures yok.
- Dışarıdan strateji/kod kopyalanırsa: dosyanın başına kaynak + lisans yaz, önce okuyup Kaan'a özetle.
- Freqtrade çekirdeği fork edilmez; sadece `user_data/strategies`, config ve `scripts/` katmanında çalışılır.

## Backtest kuralları

- Her backtest sonucu al-tut benchmark'ı (`scripts/benchmark.py`, Faz 1) ile yan yana raporlanır.
- Veri bölme: train / validation / test. **Son %20 test dilimi hyperopt'ta ve strateji geliştirirken asla kullanılmaz.** Test dilimine bakıp strateji değiştirmek yasak; her seferinde Kaan'a hatırlat.
- Kayma (slippage) için komisyon yüksek tutulur: `--fee 0.0015` (%0.1 komisyon + %0.05 kayma payı).
- 50'den az işlem = istatistiksel olarak anlamsız, uyar.
- Başarı ölçütü (risk-ayarlı): Calmar oranı al-tut'tan yüksek + max drawdown al-tut'un yarısından az + en az 50 işlem. Ham getiride al-tut'u geçmek beklenmez (sermayenin çoğu nakitte).
- Sayı verirken komutu ve tam `--timerange`'i yaz. Sayıları süsleme; kötü strateji kötüdür.
- Kaç deneme/hyperopt yapıldığını `docs/journal.md`'de say (validation dilimi de zamanla ezberlenir).

## Çalışma modu

- Açıklamalar Türkçe; kod, komut, dosya ve değişken isimleri İngilizce.
- Bilinmeyen terimi ilk birkaç geçişte parantezle Türkçe aç: "drawdown (tepe noktadan düşüş)".
- Proje modu: direkt uygula. Büyük değişiklikten önce 2-3 cümleyle ne ve neden.
- Kaan her detayı bilmek istiyor. Her kod değişikliğinde:
  - **KOD KARTI:** değişen kod (repoda, commit halinde).
  - **ÖĞRETİCİ KARTI:** `docs/learn/NN-konu.md`; kod ne yapıyor, neden bu yapı, her satır grubu ne işe yarıyor, yeni başlayan birine anlatır gibi.
- Büyük işlerin sonunda "Anlaman gerekenler": en fazla 3 madde.
- Debug: belirti → olası nedenler → kanıt (log/test) → kök neden → en küçük düzeltme → doğrulama. Tahminle yama yok.
- "Çalışıyor" demeden önce çalıştır, çıktıyı göster.
- Her faz sonunda `docs/journal.md`'ye "ne öğrendik / ne işe yaramadı".

## Ortam

- Kaan: macOS, Apple M2, 16 GB RAM. Ayrıca bir sunucusu var (7/24 için, ileride).
- Bot Docker Compose ile çalışır. Image sabit sürüm: `freqtradeorg/freqtrade:2026.10`.
- Claude'un bulut ortamı Binance API'ye erişemez; veri indirme, backtest ve bot Kaan'ın makinesinde çalışır. Geçmiş veri Kaan'ın Mac'inde indirildi (2026-10-31, 2020-10'dan beri 1h + 4h).
- Başlangıç pair'leri: BTC, ETH, SOL, BNB, XRP / USDT. Ana timeframe: 1h.
- Hazır/örnek strateji kullanılmaz; botta sadece kendi kurallarımız var. Aktif strateji: `TrendEma` (`user_data/strategies/trend_ema.py`).
- Deneme stratejileri: `user_data/strategies/trend_variants.py` (tur 1: TrendEmaAtr, TrendEmaAtrTrail, TrendEma4h, TrendBreakout; tur 2: TrendEmaAtrWide, TrendEmaSlow, TrendEmaMulti, TrendEmaBtc; Slow* = TrendEmaSlow sayı sağlamlığı komşuları). TrendEmaSlow train + validation (#2) PASS: dry-run adayı. Canlıya sadece train + validation'da kazanan geçer.
- Risk kuralları: `docs/risk-rules.md`. Bir risk sayısını değiştirmek = Kaan'a sor + tabloyu ve testi güncelle. Testi gevşeterek kural gevşetmek yasak.
- Demo borsa (Faz 5): Binance. Telegram: Faz 5'te.

## Komutlar

```bash
docker compose pull                 # image'ı indir
docker compose up -d                # botu arka planda başlat
docker compose logs -f              # canlı log (Ctrl+C ile çık, bot durmaz)
docker compose down                 # botu durdur
docker compose run --rm freqtrade <alt-komut> --config /freqtrade/user_data/config/config.json   # tek seferlik freqtrade komutu
.venv/bin/python -m pytest          # tüm testler (83)
.venv/bin/python scripts/ft.py download|backtest|hyperopt   # Freqtrade'i HER ZAMAN bunun üzerinden çalıştır (dilim + fee kilidi)
.venv/bin/python scripts/ft.py report --slice train          # tüm stratejiler vs al-tut, kısa tablo (Docker içinde)
.venv/bin/python scripts/ft.py backtest|report --slice train --universe wide   # 2021'in büyük 15 coini (hayatta kalan yanılgısı testi)
.venv/bin/python scripts/ft.py backtest|report --slice train --fee-stress      # komisyon %0,3 (2 kat) stres testi
```

FreqUI: http://127.0.0.1:8080 (kullanıcı adı/şifre `.env`'de).

## Faz durumu

- [ ] Faz 0: kurulum, TrendEma ile 24 saat temiz dry-run
- [ ] Faz 1: benchmark + veri bölme
- [ ] Faz 2: 3 strateji (EMA cross, RSI+ATR, DCA)
- [ ] Faz 3: robustluk (walk-forward, hassasiyet, Monte Carlo, kill switch)
- [ ] Faz 4: ccxt ile sıfırdan mini bot (grid burada denenir)
- [ ] Faz 5: Binance demo, 4 hafta

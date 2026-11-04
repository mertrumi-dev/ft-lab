# ft-lab: Claude için proje kuralları

Freqtrade tabanlı kişisel kripto trading botu. Sahibi Kaan (bilgisayar mühendisliği 1. sınıf, trading bilgisi sıfıra yakın). Amaç: doğru çalışan, al-tut'u (buy-and-hold) ölçülebilir şekilde geçmeye çalışan, overfitting'e (aşırı uydurma) karşı korunmuş bir bot yazmak ve bu işi öğrenmek.

## Kaan'ın altın kuralları (2026-10-31)

1. **Her işlemi sıfırdan anlat.** Kaan hiç kripto alıp satmadı. Hazır terim/kod verip geçme; ne olduğunu, neden yapıldığını günlük dille açıkla.
2. **Temel en sağlam şekilde, araştırarak.** Her değişikliği Kaan'a söyle; onay bekleme, uygula, ama açıkla. (Güvenlik çizgileri ve gerçek para bu kuralın dışında: onlar için her zaman önce sor.)
3. **Hız: bekleme minimum, çalışma maksimum.** Erteleme yok; Kaan'dan bir şey beklerken yapılabilecek her işi paralel yap. Ama sağlamlıktan ödün yok.
   (2026-11-01 ek) Botu Claude kendisi geliştirir: testleri Remote Control ile Kaan'ın Mac'inde kendisi çalıştırır, sonucu yorumlar, sıradaki denemeyi kendisi seçer, boş durmaz, her önemli sonucu thread'e kısaca yazar.
4. **Kaan'a soru sorma, en iyisini bul (2026-11-01).** Kaan'a soracağın bir soru varsa önce web'de derinlemesine araştır, cevabı kendin bul ve kararı ver; ne seçtiğini ve neden seçtiğini söyle. İstisna: güvenlik çizgileri (gerçek para, kaldıraç, gizli anahtarlar) ve canlı botun risk sayıları. Bunlarda yine önce Kaan'a sor.

Mesajlar kısa, tek seferde tek istek. Detay dosyaya (`docs/`).

## Güvenlik çizgileri (asla esnemez)

- **Gerçek para yok.** `dry_run: false`, gerçek borsa anahtarı veya withdraw (para çekme) izinli anahtar için tek satır kod/konfig yazma, önerme. Kaan istese bile önce uyar.
- **Sırlar sadece `.env`'de.** `config.json` içindeki key/secret/password/token alanları boş kalır. `tests/test_config_safety.py` bunu zorlar.
- Commit öncesi: `python3 scripts/ft.py test` geçmeli, `git status` içinde `.env`, `user_data/data/`, `*.sqlite` olmamalı.
- **Sadece spot.** Kaldıraç (leverage) ve futures yok.
- Dışarıdan strateji/kod kopyalanırsa: dosyanın başına kaynak + lisans yaz, önce okuyup Kaan'a özetle.
- Freqtrade çekirdeği fork edilmez; sadece `user_data/strategies`, config ve `scripts/` katmanında çalışılır.

## Backtest kuralları

- **N=160'ta donduruldu (2026-11-05). Yeni T denemesi veya F satırı için Kaan'ın açık onayı gerekir. Onay olmadan ön kayıt bile açma.** Kod da zorlar: `trials.py --open` / `prereg.py --open` `--kaan-approved "<mesaj id veya tarih>"` olmadan reddeder; elle eklenen satırı kontrol ve testler yakalar; `ft.py trial` trials.csv'de satırı olmayan stratejiyi koşmaz (`scripts/freeze.py`).
- Her backtest sonucu al-tut benchmark'ı (`scripts/benchmark.py`, Faz 1) ile yan yana raporlanır.
- (Kaan, 2026-11-01) Her testte ünlü botlar da yan yana: haftalık DCA, grid bot (Pionex tarzı), DCA bot (3Commas tarzı), NFI X8 (`ft.py bots`). NFI sadece araştırma kıyası; `user_data/strategies/thirdparty/`, GPL-3.0, bot yükleyemez.
- Veri bölme: train / validation / test. **Son %20 test dilimi hyperopt'ta ve strateji geliştirirken asla kullanılmaz.** Test dilimine bakıp strateji değiştirmek yasak; her seferinde Kaan'a hatırlat.
- Kayma (slippage) için komisyon yüksek tutulur: `--fee 0.0015` (%0.1 komisyon + %0.05 kayma payı).
- 50'den az işlem = istatistiksel olarak anlamsız, uyar.
- Başarı ölçütü (risk-ayarlı): Calmar oranı al-tut'tan yüksek + max drawdown al-tut'un yarısından az + en az 50 işlem. Ham getiride al-tut'u geçmek beklenmez (sermayenin çoğu nakitte).
- Sayı verirken komutu ve tam `--timerange`'i yaz. Sayıları süsleme; kötü strateji kötüdür.
- Kaç deneme/hyperopt yapıldığını `docs/journal.md`'de say (validation dilimi de zamanla ezberlenir).
- Yeni deneme ön kaydından önce aynı fikir denenmiş mi bak: `python3 scripts/trials.py --find <kelime>` (trials.csv + journal). Denenmişse ön kayda yaz ve önce söyle. `--find` eş anlamlıları da arar (trials.SYNONYMS: ör. strength = momentum = üst yarı); yine de birkaç farklı kelimeyle ara. Kazananı erken kesen çıkışlar ve "aşırı an" giriş filtreleri bu kuralda tekrar tekrar başarısız oldu (journal, araştırma 15): böyle bir fikirde önsel düşük yazılır.

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
- Hazır/örnek strateji kullanılmaz; botta sadece kendi kurallarımız var. **Çalışan dry-run botu (2026-11-01 akşamından itibaren): `TrendEmaVolTarget`** (`user_data/strategies/sizing.py`, DB `tradesv3.voltarget.dryrun.sqlite`). Eski TrendEma DB'si (`tradesv3.dryrun.sqlite`) analiz için duruyor.
- **Aday: `TrendEmaVolTarget`** (`user_data/strategies/sizing.py`; pozisyon = %12,5 × min(1, %60 / coinin 30 günlük oynaklığı)). Formel train ölçütünü geçemedi ama validation 4/4 grup + early'de en iyi; DSR < 0,95 (üstünlük kanıtlı değil). FİNAL TEST (bir kez, 2026-11-01): -%19,9, kill switch tetiklendi → FAIL; kural değişmedi, risk beklentisi araştırma 09'da (stres satırı). 2026-11-01 akşamı Faz 0 kontrolünden sonra dry-run'da TrendEma'nın yerine geçiyor (dal `switch-voltarget-rebased`, yeni DB `tradesv3.voltarget.dryrun.sqlite`). Mini bot da aynı kuralı oynuyor (`--rule voltarget`).
- 2026-11-01 FAIL'ler (ön kayıtlı, journal.md): final test (TrendEma, PyramidBtc), BtcRising/Gap kapıları, VolTargetBtc, Portfolio, Pool v1/v2, +TSMOM karışımı, Pullback, core_gold, 2h, Derisk, 1h+2h (kıl payı), AtrStop, Breadth, TSMOM, BullVol; plato: EMA uzunlukları hızlı yönde kırılgan.
- İzleme satırları (taze veride sadece yargı, asla ayar; `daily.py`): VolTarget2h, VolTarget@core_gold, VolTarget 1h+2h 50/50.
- **Paralel dry-run (2026-11-01 akşamından itibaren):** `forward-adx20` = TrendEmaVolTargetAdx (T108; ayrılmış hakem judge_old'da T111 PASS, train core'da FAIL, DSR 0,34). DB `tradesv3.adx20.dryrun.sqlite`, FreqUI :8081, profile `forward`. Sadece yargı: ana botla yan yana günlük rapor. PyramidBtc forward servisi kaldırıldı (final testte FAIL).
- Eski denemeler: `trend_variants.py` (tur 1-3, 7), `sma_daily.py`, `dip_rsi.py`, `donchian_ensemble.py`, `regime.py` (BTC kapıları), `sizing.py` (VolTarget ailesi + komşular). Ayrıntı: `docs/journal.md`, `docs/results.md`. Canlıya sadece train + validation'da kazanan geçer.
- Veri dilimleri (`scripts/splits.py`): train 2021-01→2024-06, validation →2025-08, test →2026-10 (kullanıldı), **fresh** = testten sonra bugüne (sadece yargı), **early** = 2018→2020 (sadece yargı).
- Coin grupları (`scripts/universe.py`): core (botun 5 coini), wide (2021'in büyük 15'i), alt2022/alt2023/alt2024, early (2018 coinleri), pool (~71 coin, tarayıcı), core_gold (core + PAXG).
- Risk kuralları: `docs/risk-rules.md`. Bir risk sayısını değiştirmek = Kaan'a sor + tabloyu ve testi güncelle. Testi gevşeterek kural gevşetmek yasak.
- Demo borsa (Faz 5): Binance. Telegram: Faz 5'te.

## Komutlar

```bash
export PATH=$HOME/.docker/bin:$PATH  # Docker Desktop'ın docker'ı (Mac'te PATH'te değil)
docker compose up -d freqtrade      # botu arka planda başlat (servis adıyla: forward botuna dokunmaz)
docker compose logs -f freqtrade    # canlı log (Ctrl+C ile çık, bot durmaz)
docker compose down                 # botu durdur
docker compose --profile forward up -d forward-adx20   # ileriye dönük test botu: TrendEmaVolTargetAdx (sahte para, kendi DB'si, FreqUI :8081)
python3 scripts/health.py --service forward-adx20   # ileriye dönük botun sağlığı
python3 scripts/ft.py test          # tüm testler, Docker içinde (444+; ilk sefer --build). Mac python3'te pandas yok
python3 scripts/ft.py download [--universe U] [--early] [--fine]   # veri (early: 2018'den, fine: 5m/15m NFI için)
python3 scripts/ft.py backtest|report --slice S [--universe U] [--fee-stress] [--no-kill-switch] --strategy A B
python3 scripts/ft.py bots --slice S [--universe U] --no-kill-switch --strategy A B   # ünlü botlar (DCA, grid, 3Commas DCA, TSMOM) + bizimkiler
python3 scripts/ft.py report --slice train --by-year --strategy A B   # yıl yıl kırılım
python3 scripts/ft.py walkforward|montecarlo|benchmark --slice train
python3 scripts/ft.py trial --strategy X [--neighbours A B --robust]   # standart deneme: 4 dilim sırayla + otomatik hüküm (scripts/criterion.py). Önce ön kayıt!
python3 scripts/ft.py verdict --strategy X [--neighbours A B --robust]  # mevcut sonuçlardan hüküm (salt okunur)
python3 scripts/ft.py removed --strategy X --slice S [--universe U]   # filtrenin attığı işlemler yıl yıl (salt okunur; trial --entry-filter bunu her dilimde basar)
python3 scripts/ft.py prereg-judge --due|--id F005   # taze-veri satırlarını hüküm gününde yargıla (öncesinde REDDEDER); PASS = ADAY, sonraki 6 ayda tek başına geçerse DOĞRULANDI; daily.py zamanı gelince kendisi çağırır
python3 scripts/ft.py regimes --slice train|early [--no-kill-switch]   # boğa/ayı/testere + oynaklık rejimine göre sonuç (analiz)
python3 scripts/ft.py expected      # VolTarget taze sonucu beklenen aralıkta mı (block bootstrap)
python3 scripts/ft.py scan [--universe core] [--csv]   # piyasa tarayıcı (salt okunur)
python3 scripts/ft.py chart --pair ETH [--tr]          # tek coin grafik okuma (--tr: sade Türkçe, tavsiye değil)
python3 scripts/ft.py explain       # dry-run işlemleri sade Türkçe (salt okunur)
python3 scripts/ft.py execution     # emir kalitesi: dolma, kayma, komisyon (salt okunur)
python3 scripts/ft.py ai-score      # yapay zeka grafik yorumlarını puanla (docs/fresh/ai-scores.csv)
python3 scripts/ft.py minibot [--once] [--rule voltarget|trendema]     # sıfırdan mini bot (kağıt üstünde, anahtarsız)
python3 scripts/daily.py            # günlük: indir + taze tablolar + rapor (docs/fresh/latest.md), 00:00 UTC sonrası
python3 scripts/health.py           # bot sağlığı + Faz 0 kararı (salt okunur)
python3 deploy/preflight.py         # sunucuya taşıma öncesi güvenlik kontrolü
```

FreqUI: http://127.0.0.1:8080 (kullanıcı adı/şifre `.env`'de).

## Faz durumu

- [ ] Faz 0: kurulum, 24 saat temiz dry-run. TrendEma koşusu 2026-11-01'de Docker durdurulunca kesildi (sayılmadı); sayaç TrendEmaVolTarget ile yeniden başladı
- [x] Faz 1: benchmark + veri bölme (2026-11-01: benchmark, splits, ft.py kilitleri, report, saatlik düşüş, yıl yıl, Monte Carlo)
- [ ] Faz 2: 3 strateji (EMA cross, RSI+ATR, DCA)
- [x] Faz 3: robustluk (walk-forward, hassasiyet, Monte Carlo, kill switch). 2026-11-02, VolTarget: walk-forward sabit 0,92 vs seç-en-iyi 0,50; hassasiyet haritası T115 (EMA 20/50 kırılgan, diğerleri pürüzsüz); Monte Carlo + ileri risk (araştırma 09); kill switch tatbikatı (araştırma 08); 2 kat komisyon. Özet: araştırma 12
- [ ] Faz 4: ccxt ile sıfırdan mini bot (grid burada denenir). 2026-11-01: `minibot/` (sadece kağıt üstünde işlem, anahtarsız; VolTarget kuralı Freqtrade ile birebir aynı, eşlik testi var)
- [ ] Faz 5: Binance demo, 4 hafta

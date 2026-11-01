# 17. Ünlü botlarla karşılaştırma

Kaan'ın isteği (2026-11-01): **her testte ünlü botlar da olsun, bizim kuralımızla yan yana ölçülsün.**

## Neden kendi verimizde çalıştırıyoruz?

Ünlü botların hiçbiri bağımsız, doğrulanmış ve komisyon dahil uzun dönem sonuç yayınlamıyor:

- **NFI:** Resmi deposunda performans tablosu yok.
- **3Commas, Cryptohopper:** Sadece reklam amaçlı (affiliate) yorumlar var.
- **Pionex grid:** Sadece tek tek kişilerin anlattıkları var.

Bu yüzden tek dürüst yol şu: **bu botların mantığını bizim coinlerimizde, bizim dilimimizde ve bizim komisyonumuzla (%0,15) çalıştırmak.**

## Masadaki botlar

| Bot | Ne yapar | Nasıl ölçüyoruz |
|---|---|---|
| **Al-tut** | Başta al, hiç dokunma | `benchmark.py` |
| **Haftalık DCA** (birikim planı, Binance/Pionex "Auto-Invest") | Her hafta aynı miktarda al | `benchmark.py: dca_equity` |
| **Grid bot** (Pionex/Binance tarzı) | Fiyatın altına %2 aralıklı 10 alım basamağı koyar. Her basamağı bir basamak yukarıda satar. Fiyat merdivenin üstüne çıkarsa merdiveni yukarı taşır. Stop yok | `scripts/grid.py` (kendi kodumuz) |
| **DCA bot** (3Commas tarzı) | Hemen küçük bir alım yapar. Düşüşte giderek büyüyen 5 ek alım yapar (-%2, -%5, -%9,5, -%16, -%26). Ortalama fiyatın %1,5 üstünde her şeyi satar ve yeniden başlar. Stop yok | `scripts/dcabot.py` (kendi kodumuz) |
| **NostalgiaForInfinity X8** (en ünlü Freqtrade stratejisi) | Aşağıda | Freqtrade backtest, orijinal kod |
| **TrendEma** (bizim kural) | Yükselişe katıl, %8 stop, işlem başına %1 risk | Freqtrade backtest |

Grid ve DCA bot ayarları, sonuç görülmeden önce, bu botların tipik varsayılanlarına göre seçildi ve **hiç ayarlanmadı**. Biz ayarlasaydık, onları kendi lehimize ya da aleyhimize bükmüş olurduk.

## NFI özeti (kodu okuduktan sonra)

- **Kaynak:** github.com/iterativv/NostalgiaForInfinity, sürüm v18.0.183. Lisans GPL-3.0.
- **Yer:** `user_data/strategies/thirdparty/`, dosyanın en başına kaynak ve lisans notu eklendi.
- **Boyut:** Yaklaşık 64 bin satır.
- **Zaman dilimi:** 5 dakikalık mumlarla çalışır. Ayrıca 15 dk, 1 saat, 4 saat, 1 gün ve BTC 4 saat verisine bakar.
- **Alım:** Onlarca alım koşulu var (etiketler "normal", "pump", "quick", "rebuy", "grind" vb.). Çoğu kısa vadeli düşüşte alım fikrine dayanıyor.
- **Stop:** Pratikte yok (`stoploss = -0.99`).
- **Ek alım:** Zarardaki işleme ek alım yapar ("grinding/rebuy", `position_adjustment_enable = True`).
- **Önerilen kurulum:** 40-80 coin, 6-12 açık işlem. Biz 5 coinde, 5 açık işlemle çalıştırıyoruz (`research-bots.json`). Bu NFI için ideal değil ve tabloda bunu söyleyeceğiz.
- **Güvenlik:** Bot NFI'ı yükleyemez, çünkü dosya varsayılan strateji klasörünün dışında. `tests/test_benchmark_bots.py` bunu, botun TrendEma ile çalıştığını ve ayarın dry-run olduğunu kontrol ediyor.

## Komutlar

```bash
.venv/bin/python scripts/ft.py download --fine                    # 5m + 15m veri (sadece NFI için)
.venv/bin/python scripts/ft.py backtest --slice train --no-kill-switch --strategy NostalgiaForInfinityX8
.venv/bin/python scripts/ft.py bots --slice train --no-kill-switch # hepsi tek tabloda
```

`bots` tablosunda her satırın düşüşü saat saat ölçülüyor, al-tut ile aynı yöntemle. Bu, kuralımızın başarı ölçütüyle aynı ölçüm.

## Bilinen basitleştirmeler

- **Grid ve DCA bot 1 saatlik mumla simüle ediliyor.** Bir mumun içinde fiyatın önce düşüp sonra mı yükseldiğini bilmiyoruz. Bu yüzden kötü olan durumu varsayıyoruz: aynı mumda hem alıp hem satmıyoruz.
- **Kâr hesabında komisyon dahil.** DCA bot'un "%1,5 kâr" hedefi komisyonlar düşüldükten sonraki kâr olarak alındı. Bu, gerçek 3Commas'a göre bota biraz cömert davranıyor.

## Ek: TrendEma %50 + Grid %50

`bots` tablosunda TrendEma'nın altında bir satır daha var: paranın yarısı TrendEma'ya, yarısı grid bota verilmiş hali.

- **Fikir:** TrendEma yükselen piyasada, grid bot yatay piyasada kazanıyor. Biri kazanmazken diğeri kazanırsa, toplam kâr eğrisi daha düzgün olur. Buna çeşitlendirme (diversification) denir.
- **Kurulum:** İki ayrı hesap düşün, ikisinde de başlangıçta paranın yarısı var. Biri diğerine hiç para aktarmıyor (yeniden dengeleme yok). Her saat iki hesabın değeri toplanıyor (`half_and_half`).
- **%50/%50 oranı sonucu görmeden seçildi.** Sonuca bakıp oranı %60/%40 gibi değiştirmek overfitting olur, bu yüzden yapılmayacak.
- **Deneme sayacına +1 olarak yazılıyor.**

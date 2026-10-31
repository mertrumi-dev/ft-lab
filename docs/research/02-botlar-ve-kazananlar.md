# Araştırma 02: En iyi açık kaynak botlar ve botla kim kazanıyor? (2026-10-31)

Kısa cevap: **Botla düzenli kazananlar çoğunlukla bizim yapamayacağımız işleri yapıyor** (hız, büyük sermaye, borsalardan prim). Bizim gibi tek bilgisayarla gerçekçi olan tek yol **sabırlı, risk kontrollü trend takibi** ve bu da mütevazı getiri bekler. Popüler "hazır botların" canlı kazandığına dair bağımsız kanıt bulamadık.

---

## 1. En popüler Freqtrade stratejileri

**freqtrade-strategies (resmi örnek deposu, ~5.400 yıldız, GPL-3.0)**
- Kendi açıklaması: "sadece eğitim amaçlı, hazır kullanım için değil".
- Al/sat ayarları hyperopt ile geçmiş veriye uydurulmuş. Yani ezberleme riski içinde.
- Canlı sonuç yok.

**NostalgiaForInfinity (NFI X6, en ünlü topluluk stratejisi, ~3.400 yıldız, GPL-3.0)**
- Tek dosya, yaklaşık 70.000 satır, ~350 ayar. 5 dakikalık mumlar, 40-80 coin.
- Mantığı: düşüşte al, düşmeye devam ederse daha çok al (DCA, "grinding"). Pratikte stoploss yok (`stoploss = -0.99`).
- Kodunu yazan kişi borsa referans linklerinden ve bağışlardan kazanıyor; strateji otomatik güncelleniyor (değişiklikleri incelemeden çalıştırıyorsun).
- Canlı performans: bağımsız kanıt yok. Kullanıcılar GitHub'da sermayenin %20-30'unu kaybettiklerini yazmış: "çok küçük kazançları 2-3 stoploss siliyor".
- Bizim için: kurallarımızla uyumsuz (stop yok, 5 dakika, çok coin, çok ayar). **Kullanmıyoruz.**

## 2. Diğer bot programları

| Program | Ne yapıyor | Lisans |
|---|---|---|
| Hummingbot (~20.900 yıldız) | Piyasa yapıcılığı (market making) ve arbitraj | Apache-2.0 |
| Jesse (~8.700) | Strateji araştırma, backtest, Monte Carlo | MIT |
| OctoBot (~6.800) | Grid, DCA, sepet, yapay zekalı işlem | GPL-3.0 |
| Superalgos (~5.600) | Görsel bot tasarımı | Apache-2.0 |

Hiçbirinde bağımsız doğrulanmış canlı kâr kaydı yok; sadece kendi iddiaları ve tek tük backtest görselleri var.

## 3. Botla gerçekten kim kazanıyor?

| Kim | Nasıl kazanıyor | Biz yapabilir miyiz? |
|---|---|---|
| **Piyasa yapıcılar** | Alış-satış fiyat farkından ve borsaların/coin projelerinin ödediği primlerden (sektör yılda ~1,2 milyar $ prim ödüyor, Hummingbot raporu) | Hayır: çok hızlı sunucu, sürekli risk dengeleme gerekir |
| **Arbitrajcılar** | Aynı coinin borsalar arası fiyat farkı | Hayır: hız ve birden fazla borsada büyük sermaye gerekir |
| **Fonlama oranı (funding) toplayanlar** | Spot al + vadeli işlemde sat, aradaki ücreti topla | Hayır: vadeli işlem (futures) gerekir, kurallarımızda yok |
| **Trend takip fonları (CTA)** | 67 piyasada 130 yıllık veride yılda %11,2 net, Sharpe 0,77; kriz dönemlerinde çoğunlukla kazanç (AQR çalışması) | **Evet, tek gerçekçi yol bu.** Ama mütevazı getiri ve uzun kayıp dönemleri beklenmeli |

## 4. Kötü haber: backtest'ler ve bireysel yatırımcılar

- **Quantopian çalışması (888 algoritma):** Backtest'teki başarı canlıdaki başarıyı neredeyse hiç tahmin etmiyor. En çarpıcı bulgu: **bir strateji ne kadar çok backtest ile kurcalandıysa, canlıda o kadar kötü.** En büyük düşüş ve oynaklık ise getiriden daha iyi tahmin ediyordu.
- **Brezilya günlük trader çalışması:** 300 günden fazla deneyenlerin %97'si para kaybetmiş.
- **Hayatta kalan yanılgısı:** İnternette gördüğün "harika" stratejiler, denenen binlercesinin şanslı kazananları. Kaybedenler yayımlanmaz.

Bizim için anlamı: Ölçme kurallarımız (test dilimine bir kere bakmak, deneme saymak, az ayar) tam da bu tuzaklara karşı. Doğru yoldayız.

## 5. Bota eklenecek yeni deneme fikirleri

Araştırma 01'deki listeye eklendi (Faz 2'de tek tek ölçülecek):

1. **Tek ortalama çifti yerine birkaç farklı uzunluk:** Kısa, orta ve uzun vadeli sinyallerin ortalaması. Tek bir sayı seçimine bağımlılığı azaltır (trend fonları böyle yapıyor).
2. **Daha yavaş ortalamalar:** Bir çalışma BTC'de çok daha uzun ortalamaların (yüzlerce saat) daha iyi çalıştığını bulmuş. Ama komisyonu hesaba katmamış ve tüm veriye uydurmuş; sadece "uzunları da dene" ipucu olarak alıyoruz. Bonus: daha az işlem, daha az komisyon.
3. **Oynaklığa göre pozisyon büyüklüğü:** Araştırma 01'deki ATR fikriyle aynı; ikinci bağımsız kaynak da destekliyor.

Ayrıca: Freqtrade backtest'inde korumaların (risk frenlerinin) da hesaba katılması için `--enable-protections` eklenmeli. `scripts/ft.py`'ye eklendi.

## Kaynaklar

- Freqtrade: https://github.com/freqtrade/freqtrade
- freqtrade-strategies: https://github.com/freqtrade/freqtrade-strategies
- NostalgiaForInfinity: https://github.com/iterativv/NostalgiaForInfinity , kullanıcı raporları: https://github.com/iterativv/NostalgiaForInfinity/issues/255
- Backtest tuzakları: https://brookmiles.github.io/freqtrade-stuff/2021/04/12/backtesting-traps
- Hummingbot: https://github.com/hummingbot/hummingbot , prim raporu: https://hummingbot.org/liquidity-mining.pdf
- Jesse: https://github.com/jesse-ai/jesse · OctoBot: https://github.com/Drakkar-Software/OctoBot · Superalgos: https://github.com/Superalgos/Superalgos
- Hurst, Ooi, Pedersen (AQR), "A Century of Evidence on Trend-Following Investing": https://www.TrendFollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf
- BTC saatlik ortalama kesişimleri (Rozario ve ark.): https://ar5iv.labs.arxiv.org/html/2009.12155
- Kripto zaman serisi momentumu: https://www.journals.vu.lt/BATP/article/view/44540 (küçük dergi, bağımsız doğrulanmadı)
- Quantopian 888 algoritma çalışması: https://quantpedia.com/quantopians-academic-paper-about-in-vs-out-of-sample-performance-of-trading-alg/
- Brezilya günlük trader çalışması (Chague ve ark.): https://ideas.repec.org/p/spa/wpaper/2019wpecon47.html
- BIS Bülten 69 (kripto uygulaması kullanıcıları): https://www.bis.org/publ/bisbull69.htm
- Backtest ezberleme olasılığı (Bailey ve ark.): https://papers.ssrn.com/abstract=2326253

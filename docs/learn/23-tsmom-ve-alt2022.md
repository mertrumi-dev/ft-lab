# 23: Zaman serisi momentumu (TSMOM) ve 5. coin grubu

Bu kart iki dosyayı anlatıyor: `scripts/tsmom.py` ve `scripts/universe.py` içindeki `ALT_2022` listesi. TSMOM, `ft.py bots` tablosunda "TSMOM (ours, daily, vol-scaled)" satırı olarak görünüyor.

## Neden yeni bir coin grubu?

Bir kuralı hep aynı coinlerde denersek, kural o coinleri ezberler. Sınavda aynı soruları görmek gibi. `alt2022`, Ocak 2022'de piyasa değeri sıralamasında yaklaşık ilk 60'ta olan ve başka hiçbir grubumuzda bulunmayan coinlerden oluşuyor: AXS, GALA, ENJ, KSM, ZEC, NEO...

Liste **hiçbir test çalıştırılmadan önce** yazıldı ve sonuçlara bakılıp değiştirilmiyor.

Listede sonradan çöken ya da Binance'ten çıkarılan coinler de var: LUNA, FTT, WAVES, XMR, HNT. Bunların verisi indirilemediği için araçlar onları atlıyor. Bu atlama da bir yanılgı yaratıyor: sadece hayatta kalanları ölçmüş oluyoruz (hayatta kalan yanılgısı). Bunu saklamıyoruz, raporda kaç coinin atlandığı yazıyor.

## TSMOM ne yapıyor?

Fikir iki makaleden geliyor. Kod tamamen bizim, sadece fikir alındı.
- Moskowitz, Ooi ve Pedersen (2012): Bir varlık son dönemde yükseldiyse, kısa süre daha yükselmeye eğilimlidir. Bu bulgu pek çok piyasada (hisse, döviz, emtia) gözlenmiş.
- Liu ve Tsyvinski (2021): Kriptoda bu etki kısa vadede çalışıyor, 1-4 hafta civarı.

Kurallar, her gün saat 00:00'da (UTC):

```python
signal = daily / daily.shift(28) - 1 > 0                   # 28 günde yükseldi mi?
vol = daily.pct_change().rolling(30).std() * np.sqrt(365)  # yıllık oynaklık
raw = (0.40 / vol).clip(upper=1.0) * part                  # oynaklığa göre pay
```

Satır satır:
1. **`signal`**: Coinin bugünkü fiyatı 28 gün öncekinden yüksekse `True` olur. `True` ise coini tut, değilse nakitte bekle.
2. **`vol`** (oynaklık): Coinin günlük fiyat değişimleri ne kadar dağınık? Son 30 günün günlük getirilerinin standart sapmasını alıp √365 ile çarpıyoruz, böylece yıllık oynaklığı buluyoruz. Örneğin BTC'de bu sayı genelde %50-70 civarında çıkar, küçük altcoinlerde %100'ü geçer.
3. **`raw`** (pay): Her coin paranın 1/N'ine sahip (`part`, N = gruptaki coin sayısı). Bu payın ne kadarının coine yatırılacağı `0.40 / oynaklık` formülüyle belirleniyor, en fazla %100. Örnek: oynaklığı %80 olan bir coin için 0,40/0,80 = 0,5 çıkar, yani payının yarısı coine gider, yarısı nakitte bekler. Sakin coine çok, çılgın coine az para gidiyor. Böylece her coinin toplam riske katkısı birbirine yaklaşıyor.
4. **R4 sınırı**: Tek bir coinde paranın en fazla %25'i olabilir. Bu, `docs/risk-rules.md` dosyasındaki kural.

**Komisyonu azaltmak için tampon (buffer):** Her gün küçük alım-satım yapmak komisyonla para kaybettirir. Bu yüzden bir coinde işlem yalnızca iki durumda yapılıyor: sinyal tersine dönerse ya da istenen pay 20 puandan fazla değişirse. Tablodaki `NaN` (boş) değeri "bugün bu coine dokunma" anlamına geliyor.

**Geleceği görmeme (no lookahead):** Karar D gününün kapanış fiyatıyla veriliyor, işlem ise D+1 gününün ilk saatinde yapılıyor. `test_no_lookahead_decision_is_traded_next_day` testi bunu kontrol ediyor.

**Pencere:** Simülasyon verinin en başından başlıyor. Böylece ölçüm dönemi başladığında zaten açık olan pozisyonlar da hesaba katılıyor. Sonra eğri ölçüm penceresine kesilip 1,0'dan başlayacak şekilde ölçekleniyor.

## Başarı şartı (sonuçtan ÖNCE yazıldı)

- 5 train grubunun en az 4'ünde hem al-tut'u hem TrendEma'yı Calmar'da geçmeli.
- 4 validation grubunun en az 3'ünde de aynısını yapmalı.

Sonuç geldiğinde `docs/results.md` dosyasına yazılacak. Sonuç kötü çıkarsa kötü olarak yazılacak.

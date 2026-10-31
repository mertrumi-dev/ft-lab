# Öğretici kart 04: Tur 2 denemeleri

Tur 1'de ana kuralımız TrendEma ders çalışma döneminde (train) geçti, deneme sınavında (validation) kıl payı kaldı: skoru 1,90, al-tut 2,11. Tur 2'de bu farkı kapatabilecek 4 fikir var. Yine her biri ana kuraldan **tek bir şeyi** değiştiriyor (neden: kart 03).

Hepsi `user_data/strategies/trend_variants.py` dosyasının sonunda, "Round 2" başlığının altında.

## 1. `TrendEmaAtrWide`: daha geniş "oynamaya göre stop"

**Sorun:** Tur 1'de ATR stop (fiyat − 2,5 × "coinin normal oynaması") 1 saatlik grafikte çok yakın çıktı (%2-3). Bot normal dalgalanmada satıyor, sonra tekrar alıyordu. Bu yüzden komisyonu boşa ödüyordu.

**Değişiklik:** 2,5 yerine 5. Kodda tek satır:
```python
class TrendEmaAtrWide(TrendEmaAtr):
    atr_mult = 5.0
```
`class A(B)` = "B'nin her şeyini al". Sadece `atr_mult` değişiyor. Bunu yapabilmek için TrendEmaAtr'deki sabit `ATR_STOP_MULT` yerine `self.atr_mult` kullanılacak şekilde düzenledik. Stop yine asla %8'den uzak olmaz.

## 2. `TrendEmaSlow`: daha yavaş ortalamalar

**Ortalama ne?** EMA20 = "son ~20 saatin ortalama fiyatı" (yeni saatlere daha çok ağırlık veriyor). Kısa ortalama hızlı tepki verir, uzun olan yavaş.

**Değişiklik:** 20/50/200 yerine 50/200/600 saat.
- **Beklenen fayda:** daha az yalancı sinyal, daha az işlem, daha az komisyon.
- **Bedel:** trende daha geç girip daha geç çıkmak.

Araştırma 02'de uzun pencerelerin BTC'de daha iyi çalıştığı not edilmişti.

`startup_candle_count = 1200`: 600 saatlik ortalamanın doğru hesaplanması için önce 1200 mum "ısınma" verisi gerekir. Bu mumlarda işlem yapılmaz.

## 3. `TrendEmaMulti`: 3 ortalama çifti oy veriyor

**Sorun:** "20 ve 50" sayılarını biz seçtik. Belki 19 ve 52 çok farklı sonuç verirdi. Tek bir sayı çiftine bağlı kalmak kırılgan.

**Değişiklik:** 3 çift: (20,50), (50,150), (100,300). Her biri "kısa uzunun üstünde mi?" diye bakıp "evet" ya da "hayır" oyu verir.
```python
votes = sum((ema(close, fast) > ema(close, slow)).astype(int) for fast, slow in MULTI_PAIRS)
```
`astype(int)`: doğru = 1, yanlış = 0. Toplam 0 ile 3 arası bir sayı çıkar.
- **Al:** oy 2'nin altındayken 2 veya 3'e çıktığı **ilk mum** + fiyat EMA200 üstünde. `bull & ~bull.shift(1)` = "şimdi evet, bir önceki mumda hayır" (`~` = değil). Böylece yükseliş boyunca her mumda tekrar tekrar "al" demiyor.
- **Sat:** oy 2'nin altına indiği ilk mum.

## 4. `TrendEmaBtc`: Bitcoin düşüşteyken alma

**Fikir:** Altcoinler (BTC dışındaki coinler) genelde Bitcoin'le birlikte düşer. BTC kendi uzun ortalamasının (EMA200) altındaysa piyasa genelde kötü havadadır. O zaman hiçbir coin alma.

Kod:
- `informative_pairs`: Freqtrade'e "her coin için BTC verisini de getir" der.
- `dp.get_pair_dataframe("BTC/USDT", ...)`: BTC'nin mumlarını getirir. `dp` = data provider (veri sağlayıcı).
- `btc_bull` sütunu = "BTC EMA200'ün üstünde mi". `merge(..., on="date")` ile aynı saatlere eşlenir.
- Giriş kuralı ana kuralla aynı. Sadece `btc_bull` yanlışsa giriş sinyali silinir.

**Testin yakaladığı hata:** İlk yazımda `self.dp` kullandım. Freqtrade dışında (bizim testlerde) bu özellik hiç yok ve kod çöktü. Düzeltme: `getattr(self, "dp", None)` = "varsa al, yoksa None". dp yoksa filtre her şeye izin verir; testte bu da ayrıca kontrol ediliyor.

## Testler (9 yeni, toplam 65)

- 4 yeni varyant da risk kurallarını koruyor: %8 tavan, short yok, frenler, kill switch'e dokunulmamış.
- Wide sadece çarpanı değiştiriyor.
- Slow'da ortalamalar doğru sırada: hızlı, yavaştan önce tepki veriyor.
- Multi: düşüş + yükseliş verisinde tam **1** giriş olmalı, oyun 2'ye geçtiği mumda.
- Btc: BTC sürekli düşerken hiç giriş yok. BTC verisi yokken ana kuralla aynı girişler.

## Nasıl ölçülecek

Sadece train diliminde, ana kuralla yan yana. Train'de ana kuraldan iyi olan varsa onu validation'a sokacağız (validation bakışı #2).

**Hatırlatma:** Test dilimine (son %20) hâlâ dokunmuyoruz.

---

## Anlaman gerekenler

1. 4 fikir, 4 ayrı strateji. Her biri ana kuraldan tek şey farklı.
2. Validation'a her baktığımızda o dilim biraz "ezberlenir". Bu yüzden oraya az ve sayarak bakıyoruz.
3. Test yazmak işe yaradı: BTC filtresindeki hatayı Kaan'ın Mac'ine gitmeden yakaladı.

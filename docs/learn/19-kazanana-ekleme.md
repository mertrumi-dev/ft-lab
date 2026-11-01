# 19. Kazanana ekleme (piramit), tur 8

## Analizden gelen fikir

İşlem analizinde iki şey çıktı:

1. **Kârın tamamı birkaç uzun yükselişten geliyor.** En iyi %10'luk işlem dilimi, toplam kârın %201'ini yapıyor. Kalan işlemler toplamda zararda.
2. **Paranın sadece %17'si coinde duruyor.** Büyük yükselişlerde fırsatın küçük bir kısmını alıyoruz.

Ünlü trend takipçileri (1980'lerin "Turtle" tüccarları gibi) bunu şöyle çözer: **kazanan işleme ekleme yapmak.** Bu, NFI'ın yaptığının tam tersi. NFI kaybeden işleme ekleme yapıyor ("ortalama düşürme"), biz kazanan işleme ekliyoruz.

## Kural

- Giriş ve çıkış TrendEma ile aynı.
- İşlem **+%4 kâra** geçince aynı büyüklükte **bir kez** daha alınır. +%4, %8'lik stop mesafesinin yarısıdır.
- Toplam pozisyon sermayenin %25'ini geçemez (R4).
- **Ekleme yapıldıktan sonra stop yukarı çekilir.** Böylece pozisyonun tamamı stop'a değse bile kayıp sermayenin %1'ini geçmez (R2). Stop yine de -%8'den geniş olamaz (R1).

## Sayısal örnek

- Sermaye 1000 USDT. İlk alış: 125 USDT ile 100 dolardan 1,25 coin.
- Fiyat 104 dolar olunca (+%4) 125 USDT ile 1,2 coin daha alınır.
- Toplamda 2,45 coin var, ortalama alış fiyatı yaklaşık 102 dolar.
- Kayıp en fazla 10 USDT olmalı (1000'in %1'i). 10 / 2,45 ≈ 4,1 dolar.
- Yeni stop: 102 - 4,1 ≈ **97,9 dolar**. Bu, ilk alış fiyatının yaklaşık %2 altı.

```python
def pyramid_stop_price(avg_price, amount, capital, risk, max_loss):
    by_risk = avg_price - risk * capital / amount   # toplam kayıp = %1 sermaye
    by_cap = avg_price * (1 - max_loss)             # ama -%8'den geniş değil
    return max(by_risk, by_cap)                      # ikisinden dar olanı
```

## Freqtrade parçaları

- `position_adjustment_enable = True`: Freqtrade'e "açık işleme ekleme yapabilirim" demek.
- `max_entry_position_adjustment = 1`: En fazla 1 ekleme.
- `adjust_trade_position()`: Her mumda çağrılır. Bir sayı döndürürse o kadar USDT'lik alım yapılır. `None` döndürürse bir şey yapılmaz.
- `custom_stoploss()`: Ekleme olduysa yeni stop'u hesaplar. Ekleme olmadıysa `None` döner ve normal -%8 stop geçerli kalır.

## Risk kuralları açısından

- R1, R2 ve R4 korunuyor ve testlerle kontrol ediliyor.
- R7'deki "paranın en az %62'si nakitte" sonucu değişebilir. 3 işlemin her biri %25 olursa nakit %25'e düşer.
- Bu yüzden: piramit kuralı **kazansa bile canlıya geçmeden önce** risk tablosu güncellenecek ve Kaan'a sorulacak. Bu, bir risk sayısını değiştirmek demek.

## Tur 9: sadece boğa piyasasında ekle (TrendEmaPyramidBtc)

**Sorun:** Pyramid'in bedeli derin düşüş. 2022 ve 2025 gibi kötü dönemlerde eklenen para geri veriliyor.

**Tek değişiklik:** Ekleme sadece **BTC 200 saatlik ortalamasının üstündeyken** yapılır. Bu "piyasa havası iyi" demek. Alım ve satış kuralları değişmiyor.

**Neden bu seçildi:**
- Yeni bir sayı eklemiyor. Aynı filtre tur 2'de (TrendEmaBtc) denendi.
- O denemede filtre alımlara uygulandığında düşüşü azaltmıştı, ama kazancı da kesmişti.
- Burada filtre alımlara değil, sadece eklemeye uygulanıyor. Böylece TrendEma'nın kendisi hiç değişmiyor.

**Dürüstlük notu:** Bu fikir validation sonucunu gördükten sonra yazıldı. Validation'a girerse 4. bakış olacak. Validation'ı her kullanışımızda biraz daha ezberlemiş oluyoruz.

# Öğretici kart 28: İşlem açıklayıcı (`ft.py explain`)

## Neden?

Bot bir işlem yaptığında veritabanında sadece sayılar olur: giriş fiyatı, çıkış fiyatı, kâr. "Neden aldı, neden sattı, iyi miydi?" sorularının cevabı orada yazmaz. Bu araç her işlemi sade Türkçe ile anlatır. Böylece botun kurallarını gerçek örneklerle öğrenirsin.

## Nerede?

- `docs/fresh/trades-explained.md`: bütün işlemler (daily.py her gün yeniler).
- Günlük kısa raporun 7. bölümü: ilk satırları.

## Her işlem için ne yazar?

- **Neden aldı:** Hangi saatte EMA20, EMA50'yi yukarı kesti; fiyat uzun vade çizgisinin (EMA200) yüzde kaç üstündeydi.
- **Pozisyon boyutu (VolTarget):** Coin ne kadar oynaktı, bu yüzden normalin yüzde kaçı alındı.
- **Yatırılan para ve risk:** Kaç USDT girdi; stop'a çarparsa en fazla ne kadar kaybedilir (yaklaşık yatırılanın %8'i, sermayenin %1'i).
- **Neden sattı:** Trend bitti (EMA20 aşağı kesti), stop çalıştı ya da hâlâ açık.
- **Sonuç:** Yüzde ve USDT olarak, komisyon dahil.
- **Kıyas:** Aynı saatlerde coini sadece tutsaydın ne olurdu.

## İşlem yokken

Her coin için bir sonraki alım şartını yazar. Örnek: "BTC: fiyat EMA200'ün %1,9 altında; önce EMA200 üstüne çıkmalı, sonra EMA20 EMA50'yi yukarı kesmeli."

Bot kuralı iki adımlı:
1. Büyük resim yukarı olmalı (fiyat EMA200 üstünde).
2. Kısa vade yukarı dönmeli (EMA20, EMA50'yi aşağıdan yukarı kesmeli).

## Kod

- `indicators`: botun kullandığı sayıları hesaplar (EMA20/50/200, 30 günlük oynaklık).
- `next_entry_need`: işlem yokken her coin için hangi adımın eksik olduğunu söyler.
- `explain_trade`: tek bir işlemi anlatır.
- Veritabanı sadece okuma modunda açılır; bota dokunmaz.

## Anlaman gerekenler

- **Kural mekanik:** Bot "hissetmez"; iki şart sağlanınca alır, biri bozulunca satar.
- **Kayıp işlemler normal:** Trend takibinde işlemlerin çoğu küçük kayıpla kapanır. Kârı az sayıdaki uzun trend getirir. Açıklamalarda bunu göreceksin.
- **"Sadece tutmak" kıyası** dürüstlük için var: bot bazen tutmaktan kötü yapar, bazen çok daha iyi (özellikle düşüşte).

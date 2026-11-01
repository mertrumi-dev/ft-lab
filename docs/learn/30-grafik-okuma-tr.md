# Öğretici kart 30: Türkçe grafik okuma (`ft.py chart --tr`)

## Ne yapar?

Bir coinin grafiğini sade Türkçe cümlelerle okur:

```
python3 scripts/ft.py chart --pair ETH --tr
```

Önce o coinin 1 saatlik ve günlük mumlarını indirir, sonra `scripts/chart.py --lang tr` çalışır. `--tr` olmadan aynı sayılar İngilizce çıkar (koordinatör için).

## Hangi sayılar?

| Cümle | Nereden geliyor |
|---|---|
| "Fiyat 50 günlük ortalamanın %3 altında: orta vadede zayıf" | Günlük kapanış ile EMA20 / EMA50 / EMA200 arasındaki fark |
| "son 7 günde %4 düştü" | 7, 30, 90 gün önceki kapanışa göre değişim |
| "En yakın destek (fiyatın son düştüğü dip)" | Son 60 günde fiyatın altındaki en yakın yerel dip |
| "En yakın direnç (fiyatın son döndüğü tepe)" | Son 60 günde fiyatın üstündeki en yakın yerel tepe |
| "işlem hacmi normalin 1,3 katı" | Son 30 günün ortalama hacmi / 90 günlük ortalama hacim |
| "Bot şu an almaz, çünkü ..." | Botun kendi kuralı (1 saatlik grafik, EMA20/50 ve EMA200) |

Her okuma şu cümleyle biter: **"Geçmişin okunması, tahmin değil, yatırım tavsiyesi değil."** Araç sadece olanı anlatır; "al" ya da "sat" demez.

## Kod nasıl çalışıyor?

- `daily_reading` ve `bot_view` sayıları **bir kez** hesaplar. İngilizce `render` ve Türkçe `render_tr` aynı sözlükten (dictionary, anahtar-değer tablosu) okur. Dil değişir, sayı değişmez.
- `px_tr`: Türk sayı yazımı (binlik nokta, ondalık virgül: 74.200,00). 1$'ın altındaki çok küçük fiyatlar bilimsel gösterim (5e-06) yerine düz yazılır: 0,000005.
- `ft.py` içindeki `--tr` bayrağı (flag, açık/kapalı seçenek) komuta sadece `--lang tr` ekler.

## Anlaman gerekenler

- **Hesap ile gösterim ayrı tutulur.** Böylece Türkçe metin eklemek hesaplara dokunmadı; testler ikisini ayrı kontrol eder.
- **Destek/direnç burada sadece geçmişteki dip/tepe.** Fiyatın orada duracağını garanti etmez.
- Günlük görünüm ile botun 1 saatlik görünümü farklı şey söyleyebilir; ikisi farklı zaman ölçeği.

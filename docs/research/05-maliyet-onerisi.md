# Araştırma 05: Maliyet (komisyon + kayma) önerisi (2026-11-01)

Sadece öneri. Raporlardaki resmi komisyon %0,15 olarak kalıyor (CLAUDE.md). Çalışan dry-run botun ayarına dokunulmadı.

## Neden önemli?

Komisyon 2 katına (%0,30) çıkınca VolTarget'in Calmar'ı validation wide'da 0,83'ten -0,13'e, early'de 2,47'den 1,49'a düşüyor. Bot 3,5 yılda ~640 işlem yapıyor; her işlemde iki kez komisyon ödeniyor.

## Ölçüm (sadece bilgi, yaklaşık)

Mevcut VolTarget işlemleri (aynı giriş/çıkış fiyatları), sadece komisyon bacakları yeniden hesaplandı. Kapanmış işlem düşüşü ve yaklaşık Calmar:

| Dilim / grup | %0,15 | %0,10 | %0,075 |
|---|---|---|---|
| train core (638 işlem) | +112,6%, ~2,01 | +126,0%, ~2,34 | +133,0%, ~2,51 |
| validation wide | +19,3%, ~0,90 | +22,9%, ~1,13 | +24,7%, ~1,26 |
| validation alt2022 | +10,2%, ~1,15 | +12,5%, ~1,55 | +13,7%, ~1,79 |
| validation alt2023 | +8,5%, ~0,54 | +10,9%, ~0,71 | +12,2%, ~0,81 |
| validation alt2024 | +4,7%, ~0,34 | +6,6%, ~0,49 | +7,6%, ~0,56 |
| early | +79,1%, ~3,03 | +89,5%, ~3,53 | +95,0%, ~3,81 |

Yöntem: işlem başına getiri × ((1-f_yeni)/(1-0,0015))², sermayeye oranla bileşik. Yaklaşık, çünkü pozisyon boyutları ve kill switch yolu değişmiyor.

Okuma: Maliyeti %0,15'ten %0,10'a indirmek, her dilimde Calmar'ı ~%15-35 artırıyor. Hiçbir strateji değişikliği bugüne kadar yeni verilerde bu kadar tutarlı bir kazanç vermedi.

## Mevcut durum

- `entry_pricing.price_side = "same"` ve `exit_pricing.price_side = "same"`, `use_order_book = true`, `order_book_top = 1`: alışta en iyi alış fiyatına, satışta en iyi satış fiyatına limit emir. Yani zaten "kuyrukta bekleyen" (maker tarafı) fiyatlama.
- `unfilledtimeout` 10 dakika: dolmayan emir iptal.

## Öneri (Faz 5, Binance demo hesabında ölçülecek)

1. Komisyonu BNB ile ödemek (Binance'te spot komisyonda %25 indirim): %0,10 → %0,075. Hesap ayarıdır; kodda değişiklik yok.
2. Girişlerde "post-only" emir (`order_time_in_force: {"entry": "PO"}`): emir piyasa fiyatına çarpıp taker olacaksa borsa reddeder, böylece maker komisyonu garanti olur.
3. Ölçülecek risk: **dolmayan emirler = kaçan girişler.** Trend kuralımızda kârın çoğu az sayıdaki büyük trendden geliyor (en iyi %10 işlem kârın ~%200'ü). Hızlı yükselişte limit emir dolmazsa tam o işlem kaçar. Demo hesapta 4 hafta: (a) giriş emirlerinin kaçta kaçı 10 dakikada doldu, (b) dolmayanların sonradan ne kadar yükseldiği.
4. Karar ölçütü (önceden): dolma oranı ≥ %90 ve kaçan girişlerin ortalama getirisi tasarrufu geçmiyorsa post-only kalır; geçmiyorsa normal limit emre dönülür.

# Öğretici kart 10: Günlük kanal oylaması (TrendDonchianEnsemble)

## Nereden çıktı?

2025 tarihli bir akademik çalışmadan: Zarattini, Pagani, Barbon, *Catching Crypto Trends*. 2015-2025 kripto verisinde şu tarif test edilmiş:

| Sonuç (makalede) | Değer |
|---|---|
| Yıllık getiri | %18 |
| En büyük düşüş | %11 |
| Komisyon | %0,1 |

Bu bir backtest; makaleden başka bağımsız doğrulama yok. Kod bizim, fikir onlardan. Kaynak dosyanın başında yazılı.

## Fikir 1: Donchian kanalı

Son N günün **en yüksek** ve **en düşük** fiyatı iki çizgi çizer. Aradaki bölge "kanal"dır.

- **Al:** Bugünkü kapanış, son N günün en yükseğini geçti. Fiyat kanalın üstüne çıktı, yani yeni bir yükseliş başlıyor olabilir.
- **Sat:** Kapanış, kanalın ortasına konan stop'un altına indi.

Stop sadece yukarı kayar. Fiyat yükseldikçe kanal da yükselir, stop da peşinden gelir. Düşerse stop yerinde kalır. Böylece kâr kilitlenir.

Kod: `channel_state()`.

```python
h = pd.Series(high).rolling(n).max().shift(1)
```
`shift(1)` önemli: "son N gün" bugünü içermez. Böylece geleceği görme hatası yapılmaz.

Döngü her gün için şunu yapar:
- **Pozisyondaysak:** `stop = max(stop, kanal ortası)`. Kapanış stop'un altındaysa çık.
- **Pozisyonda değilsek:** Kapanış kanal tepesini geçerse gir.

## Fikir 2: 9 farklı süre oy veriyor

Tek bir N yerine 9 N kullanıyoruz: 5, 10, 20, 30, 60, 90, 150, 250 ve 360 gün. Her biri ayrı ayrı "içerdeyim" (1) ya da "dışardayım" (0) der. Ortalama = oy oranı.

| Oy veren süre | Pozisyon |
|---|---|
| 9'un hepsi | tam pozisyon |
| 3'ü | 3/9 = üçte bir pozisyon |
| hiçbiri | sat |

Neden: "20 mi 50 mi?" sorusunun tek doğru cevabı yok. Hepsini kullanınca tek bir sayıyı şansla seçme riski (sayı sağlamlığı sorunu, kart 05) azalır.

## Fikir 3: Oynaklığa göre büyüklük

Oynaklık (volatility) = fiyatın ne kadar sert sallandığı. Son 90 günün günlük değişimlerinden hesaplanıp yıllığa çevrilir.

Hedef yıllık %25. Formül: `ölçek = min(1, 0,25 / oynaklık)`.

| Coinin oynaklığı | Ölçek | Pozisyon |
|---|---|---|
| %100 (çok sert) | 0,25 | çeyrek pozisyon |
| %25 ve altı | 1 | tam pozisyon |

Sonuç: Sert coinde küçük, sakin coinde büyük pozisyon. Her coin portföye yaklaşık aynı "sarsıntıyı" katar.

## Bizim farkımız (kurallarımız gereği)

| Konu | Makale | Biz |
|---|---|---|
| Kaldıraç | %200'e kadar | Yok. Bir coine en fazla %1 risk kuralının izin verdiği para (sermayenin %12,5'i) |
| Zarar kes | Yok | -%8 sabit stop, frenler ve kill switch aynen duruyor |

Kaldıraç ve -%8 stop yüzünden sonuç makaleden farklı çıkabilir.

## Freqtrade'de pozisyon büyütme/küçültme

`position_adjustment_enable = True` ve `adjust_trade_position()` her yeni günde çalışır:

1. Hedef para hesaplanır: bütçe × oy oranı × ölçek.
2. Elimizdeki değer hesaplanır: coin adedi × fiyat.
3. Fark hedefin %20'sinden küçükse dokunulmaz. Neden: her alım-satım komisyon demek.
4. Fark büyükse eksik kısım alınır ya da fazla kısım satılır (kısmi satış).

## Veri

360 günlük kanal için 1 yıllık geçmiş gerekiyor. Bu yüzden günlük mumları 2019'dan indiriyoruz (`ft.py download`, sadece 1d için `--erase` ile baştan).

## Testler (7 yeni, toplam 128)

- Kanal kırılınca giriyor, yükselen ortanın altına düşünce çıkıyor.
- Bugünün kendi tepesi kanala dahil değil (geleceği görme yok).
- Stop asla aşağı inmiyor.
- Oynaklık ölçeği doğru: sert coin çeyrek pozisyon, sakin coin oy oranını aşmıyor.
- Uzun düşüşte kimse içeride değil, uzun yükselişte 9 sürenin hepsi içeride.
- Risk kuralları aynı. Bütçe sermayenin %12,5'ini aşmıyor (%1 risk).

---

## Anlaman gerekenler

1. Tek bir ayar yerine 9 ayarın oylaması: şansa daha az bağımlı.
2. Sert coinde küçük, sakin coinde büyük pozisyon.
3. Akademik bir sonucu kopyalamıyoruz; kendi risk kurallarımızla yeniden test ediyoruz.

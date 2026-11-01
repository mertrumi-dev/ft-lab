# 16. Sıfırdan mini bot (Faz 4)

Freqtrade bizim yerimize çok şey yapıyor. Bu fazda aynı işi **kendimiz** yazdık, böylece bir botun içinde ne olduğunu satır satır görüyorsun. Kod `minibot/` klasöründe ve 4 dosyadan oluşuyor.

**Güvenlik:** Bot sadece herkese açık fiyatları okur. API anahtarı (borsaya "benim adıma işlem yap" yetkisi veren şifre) **hiç kullanmaz**. Para hayalidir ve `minibot/state.json` dosyasında tutulur. Bu dosya git'e girmez. Testler, kaynak kodda anahtar alanı geçmediğini her seferinde kontrol eder.

## 1. `signals.py`: kararı veren kısım

TrendEma kuralının pandas'sız, düz Python listeleriyle yazılmış hali:

```python
alpha = 2 / (length + 1)
out.append(v if not out else out[-1] + alpha * (v - out[-1]))
```

EMA'nın (üssel hareketli ortalama) tüm formülü bu kadar. Her yeni fiyat, ortalamayı `alpha` kadar kendine doğru çeker. EMA20 için alpha yaklaşık 0,095, yani her yeni mum ortalamayı yaklaşık %10 etkiler.

`signal()` fonksiyonu son kapanmış muma bakıp "buy", "sell" veya "hold" döndürür.

**En önemli test:** 3000 rastgele mumda, mini botun kararları Freqtrade stratejisinin kararlarıyla **birebir aynı** çıkıyor. Yani iki farklı kod aynı kuralı uyguluyor.

## 2. `paper.py`: sahte hesap

Hesap basit bir sözlükten oluşuyor: `cash` (nakit), `positions` (açık işlemler), `closed` (kapanmış işlemler), `peak` / `realized` (kill switch için).

| Fonksiyon | Ne yapar |
|---|---|
| `stake_for` | Ne kadar alınacağını hesaplar: sermaye × %1 / %8, en fazla sermayenin %25'i, × VolTarget katsayısı (kart 31) |
| `buy` | Nakitten düşer, komisyonu keser, pozisyon açar. Aynı coinden ikinci pozisyonu ve kill switch tetiklenmişse yeni alımı reddeder |
| `sell` | Pozisyonu kapatır, kârı/zararı yazar, kill switch tepe noktasını günceller |
| `stop_hit` | Mumun en düşük fiyatı giriş fiyatının %8 altına indi mi? |

## 3. `bot.py`: döngü

Her saatin 30. saniyesinde bot şu adımları izler:

1. Her coin için son 1000 saatlik mumu ister (`fetch_ohlcv`; 2026-11-01 öncesi 500, oynaklık için 721 kapanış gerekiyor). Pozisyon boyutu için kart 31.
2. **Son mumu atar.** O saat henüz bitmedi, kapanış fiyatı kesin değil. Bunu yapmayan botlar backtest'te iyi, canlıda kötü sonuç verir.
3. Coin elimizdeyse ve son mumun en düşük fiyatı stop'a değdiyse, stop fiyatından satar.
4. Değmediyse sinyale bakar ve alır, satar ya da bekler.
5. Hesabı `state.json` dosyasına yazar. Önce `.tmp` dosyasına yazıp sonra adını değiştirir, böylece elektrik kesilse bile yarım dosya kalmaz. Bot yeniden başladığında kaldığı yerden devam eder.

## Freqtrade'in bizim yerimize yaptıkları (mini botta eksik olanlar)

- **Kapalıyken kaçan mumlar.** Bot kapalıyken stop'a değen fiyatı görmez, çünkü sadece son mumun en düşük fiyatına bakar.
- **Fiyat boşlukları.** Fiyat stop'un altında açılırsa (gap), gerçekte daha kötü bir fiyattan satılır. Mini bot stop fiyatını varsayar, bu iyimser bir varsayım.
- **Gerçek emirler.** Limit emri, kısmen dolan emir, borsa hataları, yeniden deneme yok.
- **Korumalar.** Cooldown ve StoplossGuard yok.

Bu eksikler bilerek bırakıldı. Mini bot öğrenmek için, gerçek bot Freqtrade'de kalıyor.

## Komut

```bash
python3 scripts/ft.py minibot --once   # tek tur
```

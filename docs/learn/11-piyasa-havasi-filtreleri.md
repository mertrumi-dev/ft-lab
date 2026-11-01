# Öğretici kart 11: Piyasa havası filtreleri (Korku/Açgözlülük ve oynaklık)

Bu iki deneme Kaan'ın "bot haberlere ve grafiğe bakıp inisiyatif alsın" isteğinden çıktı. İkisi de TrendEma'ya **tek bir** ek giriş şartı koyuyor. Çıkış, stoploss, pozisyon büyüklüğü ve kill switch aynı kalıyor.

Dosyalar: `user_data/strategies/trend_sentiment.py`, `scripts/sentiment.py`, `tests/test_trend_sentiment.py`.

## 1. TrendEmaFng: "haber havası" filtresi

### Fear & Greed Index nedir?

alternative.me her gün 0-100 arası bir sayı yayımlıyor. Sayı oynaklıktan, işlem hacminden, sosyal medyadan, BTC hakimiyetinden ve Google aramalarından hesaplanıyor. 0'a yakınsa herkes korkuyor, 100'e yakınsa herkes açgözlü. 75 ve üstü "Extreme Greed" (aşırı açgözlülük).

Neden haber yerine bu? Haber metinlerinin geçmişini gün gün, bedava ve tutarlı bulmak çok zor; olmayan geçmişle de backtest yapılamaz. Bu endeks 2018'den beri her gün var, yani dürüstçe ölçülebilen tek "piyasa havası" verisi bu.

### Kural

Dün endeks 75 veya üstüyse bugün yeni alım yapma.

Fikir: herkes coşkuluyken almak çoğu zaman tepeden almak demek. Kanıt zayıf: sadece blog ve Reddit backtest'leri var, hakemli bir çalışma yok. Bu yüzden bu gerçek bir deney, kesin bir bilgi değil.

### Kod nasıl çalışıyor?

- `scripts/sentiment.py`: API'den tüm geçmişi indirir, `user_data/data/fear_greed.json` dosyasına `{"2024-01-01": 72, ...}` diye yazar. Sadece standart kütüphane kullanır, Mac'te ekstra kurulum gerekmez. Dosya gitignore'da çünkü kod değil, veri.
- `load_fear_greed()`: dosyayı okuyup tarihe göre sıralı bir pandas Series yapar. Dosya yoksa boş Series döner; o zaman filtre kapalı kalır ve log'a uyarı yazılır.
- `fng_for_candles()`: her saatlik mum için **bir önceki günün** değerini koyar. Neden önceki gün? Bugünün değeri gün içinde bir anda yayımlanıyor. Sabah 03:00 mumunda bugünün değerini kullanırsak, o an henüz var olmayan bir bilgiyi kullanmış oluruz (lookahead, "geleceğe bakma"). Backtest'te bu küçük hile sonucu olduğundan iyi gösterir. Bunu `test_fng_uses_only_previous_day_no_lookahead` testi kilitliyor.
- `populate_entry_trend`: önce TrendEma kendi giriş sinyallerini koyar (`super()`), sonra endeksin 75 ve üstü olduğu mumlarda sinyal silinir. Veri yoksa (NaN) `NaN >= 75` False olur, yani alıma izin verilir.

## 2. TrendEmaCalm: "grafik okuma" filtresi

### Kural

Coin şu an son 30 günün %80'inden daha oynaksa yeni alım yapma.

- Oynaklık = ATR / fiyat (ATR: bir mumun ortalama ne kadar oynadığı, kart 03).
- `atr_pct.shift(1).rolling(720).quantile(0.8)`: **önceki** 720 mumun (30 gün) %80'lik dilimi. `shift(1)` sayesinde mum kendini kendisiyle kıyaslamıyor. Testte gelecekteki mumları değiştirip bugünkü kararın değişmediğini kontrol ediyoruz.

Testten **önce** yazdığım beklenti: büyük ihtimalle az etkisi olacak. 2026'da yayımlanan bir çalışma (Tripathi, Financial Economics Letters) BTC'de trend takibinin oynaklık rejimine göre farklılaşmadığını bulmuş.

## Sonuçlar (train 2021-01-01..2024-06-13, kill switch kapalı, saatlik açık-işlem dahil düşüş)

| | 5 ana coin Calmar | DD | 14 coin Calmar | DD |
|---|---|---|---|---|
| Al-tut | 1,69 | %92,1 | 0,49 | %90,6 |
| TrendEma | **2,70** | %16,4 | 0,76 | %41,3 |
| TrendEmaCalm | 1,95 | %17,1 | 0,74 | %35,2 |
| TrendEmaFng | 1,48 FAIL | %14,4 | 0,27 FAIL | %42,3 |

## Ne öğrendik?

1. **Korku/açgözlülük filtresi zarar veriyor.** Trend takibi zaten yükselişte para kazanıyor ve yükselişlerde endeks çoğu zaman "aşırı açgözlü" oluyor. Filtre en iyi trend günlerinde alımı engelliyor (2021: +%177 → +%60). Yani "herkes coşkuluyken alma" trend takipçisi için yanlış ders.
2. **Oynaklık filtresi beklendiği gibi işe yaramadı.** Düşüş biraz azaldı (14 coinde %41 → %35) ama kazanç daha çok azaldı.
3. Bu turla birlikte görülen ortak desen: **giriş filtreleri hep aynı şeyi yapıyor.** Daha az işlem, daha az yatırım, daha az kazanç; risk-ayarlı sonuç da iyileşmiyor. Bir sonraki yönün "daha az alım" değil, "ne kadar alım" (pozisyon büyüklüğü) ya da "ne zaman çıkış" olması daha mantıklı.

## Anlaman gerekenler

- **Lookahead (geleceğe bakma):** Backtest'te sadece o anda gerçekten bilinen veriyi kullan. Günlük veriyi saatlik mumlarla birleştirirken bunun en kolay yolu bir gün geriden takip etmek.
- **Hipotezi testten önce yaz.** Sonucu görünce "aslında beklemiştim" demek kolay. Beklentiyi önceden yazınca kendini kandıramazsın.
- **Mantıklı görünen fikir veride işe yaramayabilir.** "Coşkuda alma" kulağa akıllıca geliyor ama trend takibinin para kazandığı an tam olarak o coşku anları.

# 22: Taze veri, haftalık rotasyon ve "güvenli" DCA botu

Bu kart 1 Kasım 2026'da yazılan üç parçayı anlatıyor: `scripts/splits.py` içindeki `fresh` dilimi, `scripts/rotation.py` ve `scripts/dcabot.py` içindeki `simulate_pair_safe`. Üçünün sonucu da `docs/results.md` dosyasında.

---

## 1. Taze veri (`--slice fresh`)

**Sorun.** Geçmiş veriyi üç parçaya bölmüştük: train (geliştirme), validation (kontrol) ve test (final sınavı). Final sınavını kullandık, validation'a da 5 kez baktık. Bir sınav sorusunu ne kadar çok görürsen o kadar ezberlersin. Bu yüzden eski veri artık "yeni kanıt" vermiyor.

**Çözüm.** 1 Ekim 2026'dan sonraki fiyatları kural yazarken hiç görmedik. Bu dönem her gün bir gün uzuyor.

```python
def fresh_slice(today=None):
    today = today or datetime.now(timezone.utc).date()
    return Slice("fresh", DATA_END, max(today, DATA_END))
```

Satırların anlamı:
- `DATA_END` test diliminin bittiği gün, yani 2026-10-01. Taze dilim tam orada başlıyor, bu yüzden test dilimiyle hiç çakışmıyor.
- `today` bugünün tarihi (UTC). Dilimin sonu her gün kendiliğinden ilerliyor.
- `max(...)` bir güvenlik önlemi. Bilgisayarın saati yanlış olsa bile dilim test dilimine geri taşamaz.

**Kural.** Taze veri sadece **hüküm vermek** için kullanılır, kural geliştirmek için kullanılmaz. "Ekim'de şu kötü çıktı, kuralı şöyle değiştireyim" demek yasak. Öyle yaparsak taze veriyi de ezberlemiş oluruz.

---

## 2. Haftalık rotasyon (`scripts/rotation.py`)

**Fikir.** TrendEma her coine tek tek bakıp "bu coin yükseliyor mu?" diye soruyor. Rotasyon ise coinleri birbiriyle yarıştırıyor: "Son 30 günde en çok hangisi yükseldi?" Akademik dayanağı, kriptoda momentum olduğunu gösteren çalışmalar (Liu & Tsyvinski 2021) ve Antonacci'nin "çift momentum" fikri.

**Kurallar.** Her pazartesi:
1. BTC 100 günlük ortalamasının altındaysa her şeyi sat ve nakitte bekle.
2. Her coinin son 30 günlük getirisini hesapla.
3. Getirisi 0'dan büyük olan en iyi 4 coine paranın %25'ini ver. Boş kalan yerler nakitte durur.

```python
score = daily / daily.shift(lookback) - 1        # 30 günlük getiri
btc_ok = btc_daily > btc_daily.rolling(sma_days).mean()   # BTC ortalamanın üstünde mi
best = s[s > 0].sort_values(ascending=False).head(top)    # pozitif olanlardan en iyi 4
```

`simulate` fonksiyonu kararı pazar akşamı kapanışında veriyor, işlemi bir sonraki saatin mumunda yapıyor. Böylece "geleceği görme" hatası (lookahead) olmuyor. Her alımda ve satımda komisyon ödeniyor.

**Sonuç.** 5 büyük coinde Calmar 3,72 çıktı, kâğıt üstünde parlak. Ama 14 coinde ve 2023 grubunda düşüş %66-77 oldu. Kural elendi.

**Ders.** Haftada bir karar vermek, çöküş gelince bir hafta geç kalmak demek. Altcoinler bir haftada %40 düşebiliyor.

---

## 3. "Güvenli" DCA botu (`simulate_pair_safe`)

**Fikir.** Normal DCA botu (3Commas tarzı) iki dönemde de sağlam çıktı. Biz ona iki güvenlik eklemeyi denedik:
1. Sadece BTC'nin 50 günlük ortalaması yükselirken yeni alım dizisine başla.
2. Alım dizisi toplamda %8 zarara düşerse hepsini sat.

**Sonuç.** Her yerde normal DCA botundan kötü çıktı. 2024-25'te 14 coinde normal bot +%26 yaptı, güvenli bot -%18.

**Neden.** DCA botu fiyat düştükçe alıp dönüşü bekleyerek kazanıyor. %8 stop ise tam dönüşün başladığı yerde satıyor. "Stop koy" ile "düştükçe ekle" birbirine zıt iki mantık. Karıştırınca ikisinin de sadece maliyeti kalıyor.

---

## Bugünün genel dersi

Eski veride "en iyi" görünen kural (BtcRisingGap) çöküşlerde gerçekten koruyor. Ama 2024-25'te ve yeni coinlerde her sınavı geçmedi. Elimizdeki kuralların hiçbiri al-tut'u her dönemde geçmiyor. Bunu süslemiyoruz. Bundan sonra asıl hakem, her sabah otomatik ölçülen taze veri.

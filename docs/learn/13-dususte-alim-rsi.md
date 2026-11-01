# 13. Düşüşte alım: RSI(2) + ATR (Faz 2, ikinci aile)

## Fikir, günlük dille

TrendEma **güçlüyü alır**: fiyat yükselmeye başlayınca biner.
Bu yeni kural tam tersini yapar ve **zayıflığı alır**:

> Büyük resim yukarıyken fiyat birkaç saat sert düştüyse al. Fiyat toparlanınca sat.

Buna "mean reversion" (ortalamaya dönüş) denir. Fikir şu: sağlıklı bir yükselişte ani düşüşler çoğu zaman geri döner.

Neden deniyoruz? İki kural farklı anlarda para kazanırsa, ikisi birlikte daha düzgün bir kâr eğrisi verir.

## Kaynak

Fikir Larry Connors ve Cesar Alvarez'in *Short Term Trading Strategies That Work* (2008) kitabındaki "RSI(2)" kuralından geliyor. Orada borsa endeksleri (S&P 500 gibi) için günlük mumlarla anlatılır. Biz sadece fikri aldık. Kod tamamen bizim (`user_data/strategies/dip_rsi.py`).

**Dürüst beklenti:** Bu kuralın hisse endekslerinde işe yaradığı çok yayınlandı. Kriptoda kanıt zayıf. Ayrıca her kazanç küçük olduğu için komisyon (%0,15 giriş + %0,15 çıkış) kârın büyük kısmını yiyebilir. Bu yüzden sonuç kötü çıkarsa şaşırmayacağız.

## Kurallar

| Parça | Kural | Neden |
|---|---|---|
| Büyük resim | Fiyat EMA200'ün üstünde | Düşen bıçağı tutmamak için sadece yükselen piyasada alırız |
| Giriş | RSI(2) < 10 | Son 2-3 mum alışılmadık sertlikte düştü |
| Çıkış | Kapanış, son 5 mumun ortalamasının (SMA5) üstünde | Fiyat toparlandı, iş bitti |
| Stop | Giriş fiyatı - 2,5 × ATR, en fazla -%8 | Düşüş devam ederse zarar sınırlı kalsın |
| Büyüklük | Stop'a değerse sermayenin %1'i gider | TrendEma ile aynı risk kuralı |

## RSI nedir?

RSI (Relative Strength Index, göreceli güç endeksi) 0 ile 100 arasında bir sayıdır.

- Son mumlarda yükselişlerin ortalamasını düşüşlerin ortalamasıyla karşılaştırır.
- **100'e yakın:** son zamanlarda neredeyse hep yükseldi.
- **0'a yakın:** son zamanlarda neredeyse hep düştü.
- Normal RSI 14 mumluk pencereye bakar. Biz **2 mumluk** olanı kullanıyoruz. Bu sadece son 2-3 muma bakar, yani çok hızlı tepki verir.

```python
change = close.diff()                                    # her mumun bir öncekine göre farkı
gain = change.clip(lower=0).ewm(alpha=1/length).mean()   # sadece artışların ortalaması
loss = (-change.clip(upper=0)).ewm(alpha=1/length).mean()  # sadece düşüşlerin ortalaması
rsi = 100 - 100 / (1 + gain / loss)
```

- `clip(lower=0)`: negatifleri 0 yapar, geriye sadece artışlar kalır.
- `ewm(alpha=1/length)`: Wilder'ın yumuşatması, yani yakın mumlara daha çok ağırlık veren bir ortalama.
- Hiç düşüş yoksa `loss` 0 olur ve bölme bozulur. O durumda RSI'yı 100 sayıyoruz.

## ATR stop neden girişe sabit?

TrendEma ATR denemesinde stop fiyatla birlikte yukarı kayıyordu (trailing, takip eden stop). Dip alımında işlem kısa sürer, bu yüzden stop'u **giriş fiyatına** sabitliyoruz:

```python
stop = giriş_fiyatı - min(2.5 × ATR, %8 × giriş_fiyatı)
```

Örnek: giriş 100 $, ATR 2 $ ise stop 95 $ olur. ATR 10 $ ise 2,5 × 10 = 25 $ olurdu, ama %8 tavanı yüzünden stop 92 $ olur.

## İki deneme

- `DipRsi`: 1 saatlik mumlar.
- `DipRsi4h`: aynı kural 4 saatlik mumlarda. Daha az sinyal, işlem başına daha büyük hareket, yani komisyonun payı daha küçük.

Bu iki deneme sayaca (`docs/journal.md`) eklenir. Test dilimine (son %20) dokunulmaz.

## Testler (`tests/test_dip_rsi.py`)

- RSI sadece yükselişte 100, sadece düşüşte 0 çıkıyor ve hep 0-100 arasında kalıyor.
- Stop %8'den geniş olamıyor.
- Yükselen trendde ani düşüşte alıyor, toparlanınca satıyor. Düzgün yükselişte almıyor.
- Düşen piyasada hiç almıyor (EMA200 filtresi).
- Risk sayıları canlı kurallarla aynı ve kill switch miras alınıyor.
- **Geleceğe bakmıyor:** son mumu değiştirmek önceki göstergeleri değiştirmiyor. Bu, backtest'te yanlışlıkla geleceği görme hatasına karşı bir koruma.

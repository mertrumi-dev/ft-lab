# Öğretici kart 01: TrendEma stratejisi ve risk kuralları

Bu kart `user_data/strategies/trend_ema.py` ve `tests/test_trend_ema.py` dosyalarını baştan sona açıklıyor. Örnek strateji (`sample_strategy.py`) silindi; artık botta sadece bizim kurallarımız var.

---

## 1. Önce kavramlar

**Mum (candle):** Belli bir sürenin fiyat özeti. 1 saatlik mumda 4 sayı var: o saatin açılış, en yüksek, en düşük ve kapanış fiyatı. Bir de hacim (o saatte ne kadar alınıp satıldığı).

**Ortalama (moving average):** Son N mumun kapanış fiyatlarının ortalaması. Fiyattaki zikzakları yumuşatır, yönü gösterir.

**EMA (üstel hareketli ortalama):** Yeni fiyatlara daha çok ağırlık veren ortalama. Normal ortalamaya göre fiyat değişimine daha hızlı tepki verir.
- EMA20: son ~20 saatin yönü (kısa vade, "hızlı")
- EMA50: son ~50 saatin yönü (orta vade, "yavaş")
- EMA200: son ~200 saatin (~8 gün) yönü (büyük resim, "trend")

**Kesişim (cross):** Hızlı EMA yavaş EMA'nın altından üstüne geçerse kısa vadeli yön yukarı dönmüş demektir. Üstünden altına geçerse aşağı dönmüş.

```
fiyat
  │        ╭──╮  hızlı EMA
  │   ╭───╯────╲──── yavaş EMA
  │──╯ ↑        ╲
  │    AL        ↓ SAT
  └──────────────────── zaman
```

## 2. Kuralımız tek cümleyle

> Büyük resim yukarıyken (fiyat EMA200'ün üstünde) kısa vadeli yön yukarı dönünce (EMA20, EMA50'yi yukarı keserse) **al**; kısa vadeli yön aşağı dönünce (EMA20, EMA50'yi aşağı keserse) **sat**.

Neden EMA200 filtresi? Düşen bir piyasada da kısa süreli toparlanmalar olur ve EMA20 EMA50'yi keser. Bunlar genelde tuzak çıkar. Filtre "sadece genel trend yukarıyken oyna" der. Testlerde bunu kanıtladım: filtreyi koddan silince "düşüşte alma" testi kırmızı oldu.

**Rakamlar (20/50/200) neden bunlar?** Ölçülmüş değil, yaygın ve makul başlangıç değerleri. Faz 2'de geçmiş veride (sadece ayarlama diliminde) deneyeceğiz. Şimdi "en iyi" sayıyı aramak, ölçme düzeneği olmadan ezberlemeye (overfitting) davetiye olur.

## 3. Kod, parça parça

### 3.1 Ayarlar (dosyanın başı)

```python
FAST_EMA = 20
SLOW_EMA = 50
TREND_EMA = 200

STOPLOSS = -0.08
RISK_PER_TRADE = 0.01
MAX_STAKE_RATIO = 0.25
KILL_SWITCH_DRAWDOWN = 0.20
STALE_CANDLES = 2
```
Tüm sayılar tek yerde, büyük harfle (Python'da "sabit" geleneği). Bir sayıyı değiştirmek istediğinde kodun içinde aramazsın; testler de bu isimleri kontrol eder.

### 3.2 Yardımcı fonksiyonlar

```python
def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()
```
pandas (Python'da tablo verisi kütüphanesi) zaten EMA hesaplayabiliyor: `ewm` = exponentially weighted mean. Ayrı bir kütüphane (TA-Lib) yerine bunu seçtim çünkü tek satır, ne yaptığı görünür.

```python
def crossed_above(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))
```
"Şu an a, b'nin üstünde VE bir önceki mumda a, b'nin üstünde değildi." `shift(1)` = bir mum geriye kaydır. `&` = ikisi birden doğru olmalı. Sonuç her mum için True/False listesi; sadece kesişim mumunda True.

```python
def risk_based_stake(capital, risk_per_trade, stoploss, max_ratio):
    stake = capital * risk_per_trade / abs(stoploss)
    return min(stake, capital * max_ratio)
```
**Pozisyon boyutu** (bir işleme ne kadar para koyacağız) burada. Mantık tersten kurulu: önce "bu işlem kötü giderse en fazla ne kaybetmeye razıyım?" (sermayenin %1'i) sorusunu sabitliyoruz, işlem büyüklüğünü ondan hesaplıyoruz.
- 1000 USDT sermaye, %1 risk = 10 USDT kaybetmeye razıyız.
- Stoploss %8 → 10 / 0,08 = 125 USDT'lik işlem aç.
- Stoploss'a takılırsa 125'in %8'i = 10 USDT kaybedersin. Tam planladığın kadar.

Neden önemli? Art arda 10 kere stoploss olsa sermayenin ~%90'ı yerinde kalır. Bu, profesyonel risk yönetiminin temel kuralı.

```python
def drawdown_from_peak(starting, closed_profits):
```
**Drawdown (tepe noktadan düşüş).** Kapanmış işlemleri sırayla toplar, sermayenin gördüğü en yüksek değeri (peak) tutar, şu anki değerin o tepeden yüzde kaç aşağıda olduğunu verir. Örnek: 1000 → 1200 (tepe) → 900 ise düşüş 300/1200 = %25. Kill switch bunu kullanıyor.

### 3.3 Strateji sınıfı: `class TrendEma(IStrategy)`

`IStrategy` Freqtrade'in "strateji şablonu". Biz ondan türetiyoruz (inheritance: kalıtım), yani Freqtrade'in beklediği fonksiyonları doldurup gerisini ona bırakıyoruz.

| Satır | Anlamı |
|---|---|
| `timeframe = "1h"` | 1 saatlik mumlarla çalış |
| `can_short = False` | Düşüşten para kazanma (short) yok, sadece spot |
| `startup_candle_count = 400` | EMA200'ün güvenilir olması için önce 400 mum geçmiş veri yükle |
| `minimal_roi = {"0": 100}` | Sabit "%X kârda sat" hedefi yok (100 = %10.000, pratikte asla). Trend takibinde kazananı koşturuyoruz; çıkışı EMA kesişimi belirler |
| `stoploss = STOPLOSS` | -%8'de zorunlu satış |
| `process_only_new_candles = True` | Hesabı sadece yeni mum kapanınca yap, her 5 saniyede değil |
| `order_types` | Alım-satım limit emir (belirlediğimiz fiyattan), stoploss market emir (o anki fiyattan, hemen; kaçış garantisi için) |

### 3.4 `populate_indicators`: göstergeleri hesapla

Freqtrade her yeni mumda bize bir tablo (DataFrame) verir: her satır bir mum, sütunlar date/open/high/low/close/volume. Biz `ema_fast`, `ema_slow`, `ema_trend` diye 3 sütun ekliyoruz.

### 3.5 `populate_entry_trend`: ne zaman al?

```python
dataframe.loc[
    crossed_above(ema_fast, ema_slow)
    & (close > ema_trend)
    & (volume > 0),
    ["enter_long", "enter_tag"],
] = (1, "ema_cross_up")
```
`.loc[koşul, sütunlar] = değer`: koşulun doğru olduğu satırlara değer yaz. `enter_long = 1` Freqtrade'e "bu mumda al" demek. `enter_tag` işlemin neden açıldığını kaydeder; FreqUI'de ve raporlarda görürsün. `volume > 0`: o saatte hiç işlem olmadıysa (veri hatası) sinyal verme.

### 3.6 `populate_exit_trend`: ne zaman sat?

Aynı yapı, ters kesişim. EMA200 filtresi yok: trend döndüyse büyük resim ne derse desin çık.

### 3.7 `protections`: otomatik frenler

Freqtrade'in hazır koruma sistemi; biz hangi frenlerin hangi ayarla çalışacağını seçiyoruz. Sayılar mum cinsinden, 1 mum = 1 saat.

- **CooldownPeriod:** Bir coinde işlem kapandıktan sonra 2 saat o coine girme. "Kaybettim, hemen geri alayım" (intikam işlemi) engeli.
- **StoplossGuard:** 24 saatte 3 stoploss olduysa piyasa bize ters, 12 saat hiç işlem açma.
- **MaxDrawdown (24 mum, %3):** Günlük kayıp limiti. Son 24 saatte kapanan işlemlerden %3 düşüş varsa 24 saat dur.
- **MaxDrawdown (168 mum, %10):** Haftalık kayıp limiti. 7 günde %10 düşüş → 48 saat dur.
- **LowProfitPairs:** Bir coin son 3 günde 2+ işlemde toplam %5'ten fazla kaybettirdiyse sadece o coini 24 saat kapat.

Önemli: frenler **yeni** işlemi engeller, açık işlemi kapatmaz. Açık işlemi stoploss korur.

### 3.8 `custom_stake_amount`: ne kadar para koy?

Freqtrade her işlem öncesi bu fonksiyonu çağırır. `self.wallets.get_total_stake_amount()` = nakit + açık işlemlerdeki para (toplam sermaye). Bunu `risk_based_stake`'e veriyoruz. `max_stake` Freqtrade'in "en fazla bu kadar koyabilirsin" sınırı (cüzdandaki boş para); onu da aşmıyoruz.

### 3.9 `confirm_trade_entry`: son kontrol noktası

Freqtrade emri göndermeden hemen önce bunu çağırır. `False` dönersek işlem açılmaz. İki kontrol var:

1. **Kill switch:** Tüm kapanmış işlemleri kapanış sırasına göre alıp `drawdown_from_peak` ile düşüşü hesaplıyor. %20 veya fazlaysa uyarı loglayıp `False`. Geçmişten hesaplandığı için bot yeniden başlasa da kapalı kalır; restart ile kandırılamaz.
2. **Bayat veri:** Sadece canlı/dry-run modda. Son mumun tarihine bakar; 2 saatten eskiyse (internet kesik, borsa sorunlu) eski fiyatla işlem açma.

`logger.warning(...)`: loga sarı uyarı satırı yazar. `docker compose logs` ile görürsün.

## 4. Testler: `tests/test_trend_ema.py`

Gerçek veri olmadan stratejiyi nasıl test ettim? **Sahte fiyat serileri** ürettim, sonucunu önceden bildiğim durumlar:

| Test | Sahte veri | Beklenen |
|---|---|---|
| `test_entry_in_uptrend_after_dip` | 400 saat yükseliş, kısa düşüş, toparlanma | En az 1 alım, hepsi EMA200 üstünde |
| `test_no_entry_in_downtrend` | Sürekli düşüş + sert dalgalanmalar | EMA20 EMA50'yi kesiyor (kontrol ediliyor) ama **hiç alım yok** |
| `test_exit_when_trend_turns_down` | Yükseliş, sonra düşüş | En az 1 satış sinyali |
| `test_risk_based_stake_*` | 1000, %1, -%8 | 125; çok dar stop'ta tavan 250 |
| `test_drawdown_from_peak` | 1000 → 1200 → 900 | %25 |
| Kilit testleri | Kod sabitleri | stoploss ≥ -%8, risk ≤ %1, kill switch ≤ %20, short yok, 5 koruma yerinde, max 3 işlem |

**Testleri test ettim:** Testin işe yaradığından emin olmak için kodu bilerek bozdum:
- EMA200 filtresini sildim → `test_no_entry_in_downtrend` kırmızı.
- Stoploss'u -%15 yaptım → `test_stoploss_is_set_and_not_wider_than_8_percent` kırmızı.
- Geri aldım → 25 test yeşil.

`pytest.importorskip("freqtrade")`: freqtrade kurulu değilse bu dosyayı atla (hata verme). Bu yüzden `requirements-dev.txt`'ye freqtrade'i ekledim; Mac'inde de 25 test çalışsın.

## 5. Neyi bilmiyoruz?

Bu stratejinin para kazandırıp kazandırmadığını **bilmiyoruz.** Testler sadece "kod yazdığımız kuralı doğru uyguluyor mu" sorusunu cevaplıyor. "Kural iyi mi" sorusu Faz 1-2'de geçmiş veriyle, al-tut ile kıyaslanarak cevaplanacak.

---

## Anlaman gerekenler

1. Kural: büyük trend yukarıyken kısa trend yukarı dönünce al, aşağı dönünce sat. Rakamlar henüz ölçülmedi.
2. Her işlemde önce "en fazla %1 kaybederim" sabitleniyor, işlem büyüklüğü ondan hesaplanıyor.
3. Frenler ve kill switch yeni işlemi durdurur; açık işlemi stoploss korur.

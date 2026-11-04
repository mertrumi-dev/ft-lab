# Ana botun haritası

Ana bot `TrendEmaVolTarget`. Kuralları iki dosyada: `trend_ema.py` temel kuralları, `sizing.py` para miktarı ayarını tutuyor. `TrendEmaVolTarget`, `TrendEma`'dan miras alır (inheritance): girişi ve çıkışı aynen kullanır, sadece miktarı değiştirir.

Bir işlemin yolu: **giriş sinyali → koruma kontrolleri → miktar hesabı → alım → stop ya da çıkış sinyali → satım.**

Satır numaralarını `tests/test_learn_map.py` kontrol eder: kod kayarsa test kırılır ve bu dosya güncellenir.

## 1. Giriş: ne zaman alır?

Her saat kapanışında üç şartın üçüne birden bakar: hızlı ortalama (EMA20) yavaş ortalamayı (EMA50) tam o mumda aşağıdan yukarı kesmiş olmalı, kapanış uzun ortalamanın (EMA200) üstünde olmalı, mumda işlem hacmi sıfırdan büyük olmalı. "Kesti" ile "üstünde" farklı şeydir: `crossed_above` sadece kesişme anında True olur, sonraki mumlarda değil. Yani bot trendin ortasına atlamaz, yeni bir kesişme bekler. Sinyal alım garantisi de değildir: 5. ve 6. bölümdeki kontroller ve aynı anda en fazla 3 işlem sınırı alımı yine durdurabilir.

- `user_data/strategies/trend_ema.py:148` → `crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])`
- `user_data/strategies/trend_ema.py:149` → `dataframe["close"] > dataframe["ema_trend"]`
- `user_data/strategies/trend_ema.py:46` → `(a > b) & (a.shift(1) <= b.shift(1))`
- `user_data/config/config.json:9` → `"max_open_trades": 3`

**Kendi cümlenle cevapla:** EMA20 üç gündür EMA50'nin üstünde ve fiyat EMA200'ün üstünde. Bot şimdi alır mı? Neden?

## 2. Çıkış: ne zaman satar?

Sinyalle satış tek şarta bağlı: EMA20, EMA50'yi yukarıdan aşağı keser. Sabit kâr hedefi yok: `minimal_roi` değeri 100, yani pratikte %10.000 kârda satmak demek; bu da hiç devreye girmez. Amaç kazananı erkenden kesmemek. Bu kural kârını birkaç büyük trendden alıyor, ve T060, T109, T135, T153 işlemi erken kapatan kuralların bunu bozduğunu gösterdi. Giriş üç şarta bakıyor ama çıkış EMA200'e bakmıyor; fiyatın EMA200 altına inmesi tek başına sattırmaz.

- `user_data/strategies/trend_ema.py:157` → `crossed_below(dataframe["ema_fast"], dataframe["ema_slow"])`
- `user_data/strategies/trend_ema.py:104` → `minimal_roi = {"0": 100}`

**Kendi cümlenle cevapla:** Bir işlem %50 kârda ve fiyat düşmeye başladı. Botu ne sattırır? Kâr %50'de iken neden kendiliğinden satmıyor?

## 3. Stop: zararı nerede keser?

İşlem giriş fiyatının %8 altına inerse, EMA'lar ne derse desin satar. Bu sabit bir emniyet ağıdır: fiyat yükseldikçe yukarı taşınmaz (`trailing_stop = False`). Emir türü `market`: "fiyat ne olursa olsun hemen sat". Yani sert düşüşte %8'den kötü fiyata satabilir. Önemli bir ayrıntı: stop borsada durmuyor (`stoploss_on_exchange` False), botun kendisi izliyor. Bot uyuyorsa ya da kapalıysa stopu izleyen kimse yok (kart 39). Bu sahte parada bir ölçüm sorunu, gerçek parada ise gerçek risk olurdu; sunucuya geçmenin bir nedeni de bu.

- `user_data/strategies/trend_ema.py:32` → `STOPLOSS = -0.08`
- `user_data/strategies/trend_ema.py:107` → `stoploss = STOPLOSS`
- `user_data/strategies/trend_ema.py:108` → `trailing_stop = False`
- `user_data/strategies/trend_ema.py:117` → `"stoploss": "market"`
- `user_data/strategies/trend_ema.py:118` → `"stoploss_on_exchange": False`

**Kendi cümlenle cevapla:** %8'lik stop paranın %8'ini kaybetmek demek mi? 1000 USDT hesapta 125 USDT'lik işlem stopa takılırsa kaç USDT kaybedersin? (Bir sonraki bölümle bağla.)

## 4. Miktar: işleme ne kadar koyar?

İki adım var. Önce risk hesabı: stopa takılınca sermayenin en fazla %1'i gitsin; `sermaye × 0,01 / 0,08` sermayenin %12,5'ini verir, %25 tavanı da burada uygulanır. Sonra oynaklık ayarı: `min(1, %60 / coinin 30 günlük yıllık oynaklığı)`. Oynaklık %120 ise miktar yarıya iner; %40 ise 1'de kalır. Yani bu ayar miktarı sadece **küçültür**, asla büyütmez. Sermaye hesabı `get_total_stake_amount` ile yapılır: boştaki para artı açık işlemlerdeki para. Oynaklık henüz hesaplanamıyorsa (ilk 30 gün) oran 1 kabul edilir. VolTarget ile TrendEma'nın tek farkı bu ikinci adımdır.

- `user_data/strategies/trend_ema.py:60` → `stake = capital * risk_per_trade / abs(stoploss)`
- `user_data/strategies/trend_ema.py:33` → `RISK_PER_TRADE = 0.01`
- `user_data/strategies/trend_ema.py:34` → `MAX_STAKE_RATIO = 0.25`
- `user_data/strategies/sizing.py:44` → `return min(1.0, target / vol)`
- `user_data/strategies/sizing.py:66` → `stake = risk_based_stake(capital, RISK_PER_TRADE, self.stoploss, MAX_STAKE_RATIO)`
- `user_data/strategies/sizing.py:73` → `return min(stake * vol_scale(vol, self.target_vol), max_stake)`

**Kendi cümlenle cevapla:** Hesapta 1000 USDT var, coinin oynaklığı %120. Bot kaç USDT'lik alır? Stopa takılırsa kaç USDT kaybeder? Sonuç neden %1 değil?

## 5. Kill switch: ne zaman tamamen durur?

Bot her alımdan hemen önce `confirm_trade_entry` çalıştırır. Bu fonksiyon False dönerse alım olmaz. Kapanmış işlemlerin tarihinden gerçekleşmiş bakiyeyi yeniden hesaplar; bakiye herhangi bir zaman zirvesinden %20 düşmüşse yeni alım yapmaz. "Şu anki" düşüşe değil "en kötü" düşüşe baktığı için, sonradan toparlansa bile kapalı kalır ve yeniden başlatmak da sıfırlamaz: bir insanın yeni veritabanı açması gerekir. İki sınırı bil: açık işlemleri satmaz, sadece yeni alımı durdurur; ve sadece kapanmış işlemleri sayar, açık zararı görmez. Araştırma için kapatılabilir, ama kod bunu sadece backtest'te kabul eder; dry-run'da ayar ne derse desin açıktır.

- `user_data/strategies/trend_ema.py:35` → `KILL_SWITCH_DRAWDOWN = 0.20`
- `user_data/strategies/trend_ema.py:90` → `worst = max(worst, (peak - equity) / peak if peak > 0 else 0.0)`
- `user_data/strategies/trend_ema.py:216` → `if drawdown >= KILL_SWITCH_DRAWDOWN:`
- `user_data/strategies/trend_ema.py:192` → `return getattr(runmode, "value", None) not in ("backtest", "hyperopt")`

**Kendi cümlenle cevapla:** Bakiye zirveden %20 düştü, sonra açık işlemler kârla kapandı ve düşüş %12'ye indi. Bot yeniden alım yapar mı? Bot yeniden başlatılsa ne olur?

## 6. Korumalar: kısa süreli frenler

Kill switch kalıcıdır, bunlar geçicidir. **CooldownPeriod:** bir coinde işlem kapanınca o coinde 2 saat beklenir. **StoplossGuard:** 24 saatte herhangi coinlerde 3 stop olursa bütün yeni alımlar 12 saat durur. Bu sadece stop çıkışlarını sayar, EMA kesişmesiyle gelen zararları saymaz. Bir de bayat veri koruması var: dry-run'da son mum 2 saatten eskiyse (internet ya da borsa sorunu) alım reddedilir. Backtest bunu çalıştırmaz, çünkü geçmişte veri hep "taze"dir.

- `user_data/strategies/trend_ema.py:127` → `"method": "CooldownPeriod"`
- `user_data/strategies/trend_ema.py:128` → `"stop_duration_candles": 2`
- `user_data/strategies/trend_ema.py:132` → `"method": "StoplossGuard"`
- `user_data/strategies/trend_ema.py:134` → `"trade_limit": 3`
- `user_data/strategies/trend_ema.py:135` → `"stop_duration_candles": 12`
- `user_data/strategies/trend_ema.py:233` → `if current_time - last_candle > max_age:`

**Kendi cümlenle cevapla:** Bugün üç işlem zararla kapandı: ikisi stopla, biri EMA kesişmesiyle. StoplossGuard çalışır mı? Neden?

## 7 günlük plan

Günde bir parça, yaklaşık 20 dakika. Her gün: paragrafı oku, satırları kodda aç, soruyu **önce kendin** cevapla, sonra yaz.

| Gün | Konu | Kodda yap | Bitti sayılması için |
|---|---|---|---|
| 1 | Giriş | `populate_entry_trend` ve `crossed_above` fonksiyonlarını aç | Kesişme ile "üstünde olma" farkını anlatabilmek |
| 2 | Çıkış | `populate_exit_trend`'i girişle yan yana oku | Çıkışın neden EMA200'e bakmadığını söyleyebilmek |
| 3 | Stop | `order_types` bloğunu oku, kart 39'a bak | Mac uyurken stopa ne olduğunu anlatabilmek |
| 4 | Miktar | 1000 USDT ve %120 oynaklığı kâğıtta hesapla | Sonucu kodu açmadan bulabilmek |
| 5 | Kill switch | `worst_drawdown`'ı küçük bir listeyle kâğıtta çalıştır: 1000 başlangıç, kârlar [+100, -300, +150] | Sonucu bulup neden "en kötü" kullanıldığını söyleyebilmek |
| 6 | Korumalar | `protections` bloğunu ve bayat veri kontrolünü oku | Kill switch ile korumaların farkını söyleyebilmek |
| 7 | Hepsi | `python3 scripts/ft.py explain` çıktısından gerçek bir işlem seç, baştan sona anlat | Kuralları açmadan: neden aldı, ne kadar aldı, neden sattı |

Yedinci gün çıkış şartı: botu birine 5 dakikada kendi cümlelerinle anlatabilmek.

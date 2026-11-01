# Araştırma 11: Komisyonu kuralı değiştirmeden düşürmek (2026-11-01)

Neden: Komisyon, kayıpların büyük bir parçası. VolTarget final testte kaybın %27'si (52,7 / 198,4 USDT), yeni coin grubunda (alt2024b) kaybın %66'sı (60,2 / 91,2 USDT). Soru: kurala dokunmadan komisyon düşer mi?

Bu belge sadece araştırma ve öneri. **Çalışan botun ayarı değiştirilmedi.** `dry_run` her zaman true, anahtar yok.

## 1. Bugünkü maliyet varsayımımız

Backtest'te işlem başına (her yön) **%0,15** maliyet: %0,10 Binance komisyonu + %0,05 kayma payı (CLAUDE.md, R17). Gidiş-dönüş %0,30.

## 2. Bulgular (kaynaklı)

### a) Binance spot komisyonu: maker ve taker aynı

- Temel seviye (VIP 0): **maker %0,10, taker %0,10**. BNB ile ödenirse ikisi de **%0,075** (%25 indirim). Kaynak: Binance.US resmi destek sayfası ve 2025-26 üçüncü taraf özetleri. Global Binance'in güncel tablosu Binance'in kendi ücret sayfasından **teyit edilmeli**; bulunan resmi sayfa ABD şirketine ait.
- **Sonuç:** VIP 0'da "maker emir" komisyon oranını düşürmez. Kazancı **kayma ve spread** tarafında: emir karşı tarafa geçmeden, kendi tarafta bekler.

### b) Bizim bot zaten maker tarzı fiyat kullanıyor

`config.json`: `entry_pricing.price_side = "same"`, `use_order_book = true`, `order_book_top = 1`; exit için de `"same"`. Freqtrade kaynak kodu (`exchange.py`, `_get_price_side`) ve resmi belgesi: uzun pozisyonda alış **bid** fiyatından, satış **ask** fiyatından verilir. Yani emir spread'i geçmez, defterde bekler. Belgenin tablosu: "long / buy / same → 99 (bid), crosses spread: **no**".

Bedeli: Emir dolmayabilir. Ayarımızda dolmayan emir 10 dakikada iptal edilir (`unfilledtimeout` 10 dk). Dry-run bunu da taklit ediyor: alış emri, en iyi satış fiyatı bizim fiyatımıza inince dolmuş sayılıyor (`_dry_is_price_crossed`).

Stop emirleri **piyasa emri** (R16, `order_types.stoploss = "market"`): taker, ama nadir (final testte 176 çıkıştan 2'si).

### c) Dry-run ve backtest hangi komisyonu kullanıyor?

Freqtrade belgesi: "Backtesting / Hyperopt / Dry-run modlarında borsanın varsayılan (en düşük seviye) komisyonu kullanılır; canlıda borsanın uyguladığı komisyon (BNB indirimleri dahil) kullanılır." Kaynak kodda dry-run, `config.json`'da `fee` varsa onu, yoksa ccxt'nin market bilgisindeki oranı alıyor (`get_fee`). Bizim backtest'lerimiz ise `--fee 0.0015` ile bilerek daha temkinli.

### d) BNB ile ödeme: önemli bir çakışma

Freqtrade'in Binance notu: BNB ile komisyon ödenecekse **`BNB/USDT` kara listeye alınmalı.** Sebep: komisyon BNB pozisyonundan düşülür, botun aldığı BNB'nin tamamı satılamaz hale gelebilir. Ayrıca: "Freqtrade komisyon için asla BNB satın almaz; BNB'yi elle alıp takip etmek gerekir." BNB yetmezse indirim olmaz.

**Bizim ana 5 coinimizden biri BNB.** Yani BNB indirimi, kural setini (coin listesini) değiştirmeden doğrudan kullanılamıyor. Mini bot için de (kart 32) BNB komisyonu USDT'ye çevrilmiyor.

## 3. Ne kadar kazandırır? (mevcut sonuçlarla hesap, yeni test yok)

Maliyet işlem tutarıyla orantılı. Varsayım %0,15'ten aşağı inerse komisyon kalemi aynı oranda küçülür:

| Senaryo (her yön) | Oran | final test komisyonu (52,7) | alt2024b komisyonu (60,2) |
|---|---|---|---|
| Bugünkü varsayım (%0,10 + %0,05 kayma) | 1,00 | 52,7 | 60,2 |
| BNB indirimi (%0,075 + %0,05 kayma) | 0,83 | 43,9 | 50,2 |
| BNB + maker'da gerçekten kayma yok (%0,075) | 0,50 | 26,4 | 30,1 |

En iyimser durumda bile final test kaybı -198,4'ten yaklaşık **-172 USDT**'ye, alt2024b kaybı -91,2'den yaklaşık **-61 USDT**'ye iner. Komisyon kaybı büyütüyor ama **kaybın asıl kaynağı değil**. Sinyal o dönemde zaten kaybediyordu (araştırma 10).

## 4. Öneri

1. **Şimdi hiçbir ayar değişmesin.** Bot yeni başladı (Faz 0 sayacı sıfırlandı). Kural ve risk kuralları aynı kalsın.
2. **Backtest varsayımı %0,15 kalsın.** Temkinli olmak doğru; gerçek dolum verisi gelmeden düşürmek kendini kandırmak olur.
3. **Ölç:** Dry-run işlem yaptıkça `python3 scripts/ft.py execution` gerçek dolum oranını, kaymayı ve kaçan girişleri gösterecek. Faz 5'te (Binance demo, mini bot) aynısı gerçek emir defterinde ölçülecek. Kayma gerçekten ~0 ise varsayım ileride ön kayıtla düşürülebilir.
4. **BNB indirimi kararı ileriye, Kaan'a:** Canlıya yaklaşırken iki yol var: (a) BNB'yi işlem listesinden çıkarmak (kural değişikliği: ön kayıt + test gerekir), (b) BNB indirimini kullanmamak. Bugün öneri **(b)**: indirim küçük (%17 maliyet), çakışma riski gerçek.
5. **En büyük kaldıraç, işlem sayısı:** Bu gece yapılan denemeler (MinHold, Cooldown, FeeAware) işlem sayısını azaltmanın tek başına yetmediğini gösterdi (araştırma 10, journal).

## Kaynaklar

- Freqtrade, Bot basics / Fee handling: https://www.freqtrade.io/en/stable/bot-basics
- Freqtrade, Configuration / Prices used for orders: https://www.freqtrade.io/en/stable/configuration
- Freqtrade, Exchanges / Binance blacklist recommendation: https://www.freqtrade.io/en/stable/exchanges
- Freqtrade, FAQ (coin dust, BNB): https://www.freqtrade.io/en/stable/faq
- Freqtrade 2026.10 kaynak kodu (Docker image içinde): `freqtrade/exchange/exchange.py` (`_get_price_side`, `get_fee`, `_dry_is_price_crossed`)
- Binance.US, BNB ile ücret indirimi ve VIP tablosu: https://support.binance.us/hc/en-us/articles/360047428113-Binance-US-Launches-Trading-Fee-Discount-and-VIP-Program-With-BNB
- Binance.US, Using BNB to pay for fees: https://support.binance.us/hc/en-us/articles/360046786894-Using-BNB-to-Pay-for-Fees
- Üçüncü taraf özet (2025): https://cryptopotato.com/binance-fees/

## Anlaman gerekenler

- **Maker/taker:** Maker emir defterde bekler (likidite sağlar), taker hemen karşı taraftan alır. Binance'te temel seviyede ikisinin oranı aynı; fark kaymada.
- **Komisyon kaybı büyütür ama yaratmaz.** Komisyonu yarıya indirsek bile kötü dönemde kural yine kaybediyordu.
- **Bir indirim yeni bir risk getirebilir.** BNB ile ödeme, BNB işlemleriyle çakışıyor; "bedava" görünen her optimizasyonun yan etkisine bakılır.

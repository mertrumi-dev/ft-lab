# Öğretici kart 03: Deneme stratejileri (`trend_variants.py`)

Araştırmalarda (docs/research/01 ve 02) bulduğumuz iyileştirme fikirlerini **ayrı stratejiler** olarak yazdık. Canlı bot hâlâ `TrendEma` ile çalışıyor; bunlar sadece backtest için.

## Neden her biri sadece BİR şeyi değiştiriyor?

Diyelim stop'u da, mum süresini de, giriş kuralını da aynı anda değiştirdik ve sonuç iyileşti. Hangisi işe yaradı? Bilemezsin. Belki biri çok iyi, diğeri kötü ve birbirini götürüyor. Bilimde "tek değişken" kuralı: bir seferde tek şeyi değiştir, etkisini ölç.

Bu yüzden her deneme stratejisi `TrendEma`'dan **türetiliyor** (Python'da `class TrendEmaAtr(TrendEma)` = "TrendEma'nın her şeyini al, sadece şunları değiştir"). Risk kuralları (%1 risk, -%8 tavan, frenler, kill switch) hepsinde aynen duruyor; testler bunu kontrol ediyor.

## 4 deneme

### 1. `TrendEmaAtr`: coine göre ayarlanan, yukarı kayan stop

**ATR nedir?** "Bu coin bir mumda genelde ne kadar oynuyor?" sorusunun cevabı, fiyat cinsinden. Örnek: BTC 60.000 $ iken bir saatte genelde 300 $ oynuyorsa ATR = 300.

Hesap (`atr()` fonksiyonu): Her mum için "gerçek aralık" = şunların en büyüğü:
- mumun en yükseği − en düşüğü,
- en yüksek − bir önceki kapanış (arada fiyat sıçradıysa),
- en düşük − bir önceki kapanış.
Sonra son 14 mumun yumuşatılmış ortalaması.

**Stop:** fiyat − 2,5 × ATR. BTC örneğinde 60.000 − 750 = 59.250 (%1,25 aşağı). Çok oynak bir coinde aynı formül daha geniş stop verir. Ama asla %8'den geniş olmaz (`atr_stop_distance` tavanı).

**Yukarı kayma (trailing):** Her yeni mumda stop yeniden hesaplanır. Fiyat yükseldikçe stop da yükselir. Freqtrade bir stop'u asla aşağı indirmez; böylece kâr kilitlenir. Örnek: 100'den aldın, fiyat 130'a çıktı, stop 125'e geldi. Fiyat geri düşerse 125'te satarsın: %25 kâr cebinde.

**Pozisyon büyüklüğü:** %1 risk kuralı aynı, ama stop mesafesi artık ATR'den geliyor. Stop %2 uzaktaysa 1000 × 0,01 / 0,02 = 500 → tavan %25 → 250 USDT. Stop %8 uzaktaysa 125 USDT. Sonuç: her işlemin riski yine 10 USDT, ama sakin coinde daha büyük pozisyon.

Freqtrade'deki karşılıkları:
- `use_custom_stoploss = True`: "stop'u her mumda ben hesaplayacağım".
- `custom_stoploss(...)`: o hesap. `stoploss_from_absolute(stop_fiyatı, şu_anki_fiyat)` = "stop fiyatını Freqtrade'in istediği yüzde biçimine çevir".
- `self.dp.get_analyzed_dataframe(...)`: o coinin hesaplanmış son mumunu (ATR dahil) getirir.

### 2. `TrendEmaAtrTrail`: sadece takip eden stop ile çık

1 ile aynı, tek fark: `use_exit_signal = False`. Yani "EMA20, EMA50'yi aşağı kesince sat" kuralı kapalı; satışa sadece yukarı kayan stop karar verir. Fikir: trend devam ederken erken çıkmamak ("kazananı koştur"). Riski: trend dönünce stop'a kadar biraz kâr geri verilir.

### 3. `TrendEma4h`: 4 saatlik mum

Kurallar aynı, sadece mum 1 saat yerine 4 saat. Daha az işlem → daha az komisyon, daha az yalancı sinyal. Bedeli: trende daha geç girip daha geç çıkmak. Not: frenler mum sayısıyla tanımlı, burada 4 kat uzun sürerler (2 mum soğuma = 8 saat).

### 4. `TrendBreakout`: kırılım girişi (Turtle tarzı)

Giriş: "kapanış, önceki 20 mumun en yükseğini geçerse ve genel trend yukarıysa al". Çıkış ve risk aynı.

Kritik detay, `shift(1)`:
```python
dataframe["high"].rolling(20).max().shift(1)
```
`rolling(20).max()` = son 20 mumun en yükseği; ama **bu mum dahil**. Bu mumun kendisi de dahil olsaydı "kapanış en yüksekten büyük mü" sorusu neredeyse hiç doğru çıkmaz ya da backtest'te geleceği görmüş oluruz. `shift(1)` = bir mum geriye kaydır, yani sadece **önceki** 20 mum. Buna "lookahead bias'tan (geleceği görme hatası) kaçınmak" denir; testte kontrol ediliyor.

## Nasıl ölçeceğiz?

Veri gelince tek komut, hepsi yan yana:
```
.venv/bin/python scripts/ft.py backtest --slice train --strategy TrendEma TrendEmaAtr TrendEmaAtrTrail TrendEma4h TrendBreakout
.venv/bin/python scripts/benchmark.py --slice train
```
Kazanan: Calmar'ı en yüksek, en az 50 işlem yapan, düşüşü al-tut'un yarısından az olan. Train'de kazanan validation'da da kazanırsa canlı bota o geçer.

## Testler (`tests/test_trend_variants.py`, 10 test)

- ATR doğru mu: her mum tam 2 oynarsa ATR = 2; mumlar arası 10'luk sıçramalar ATR'ye sayılıyor mu.
- Stop mesafesi %8'i geçmiyor mu.
- Kırılım sadece önceki mumlara mı bakıyor (geleceği görme yok).
- Her varyant risk kurallarını aynen koruyor mu (stop tavanı, short yok, frenler, kill switch'i ezmemiş).

Toplam: 49 test.

---

## Anlaman gerekenler

1. Her deneme tek bir şeyi değiştiriyor ki etkisini net ölçelim.
2. ATR = coinin "normal oynaması"; stop'u ona göre koymak her coine uygun stop demek.
3. Hiçbiri canlıda değil; veri karar verecek.

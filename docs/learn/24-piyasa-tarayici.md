# 24: Piyasa tarayıcı (`ft.py scan`)

Bu kart `scripts/scan.py` dosyasını anlatıyor. Bu araç botun kuralını tek seferde 60 kadar coine uygular ve her biri için "kural şu an ne görüyor?" sorusunu cevaplar. Uzun vadeli hedefimiz "tüm coinleri tarayan sistem". Bu, o hedefin ilk adımı.

**Önemli:** Bot hâlâ sadece 5 coinde işlem yapıyor. Tarayıcı sadece bakar, hiçbir alım ya da satım yapmaz.

## Nasıl çalıştırılır

```bash
python3 scripts/ft.py scan                  # 'pool' grubundaki tüm coinler
python3 scripts/ft.py scan --universe core  # sadece botun 5 coini
```

`ft.py` önce coinlerin en son 1 saatlik mumlarını indirir. Daha önce indirilmiş veriler silinmez, sadece eksik kalan son mumlar eklenir. Sonra `scan.py` Docker içinde çalışır.

## Her coin için ne hesaplanıyor (`scan_one`)

1. **`bot_view(h)`**: Bu fonksiyon `chart.py` dosyasından geliyor. Botun kuralını, son kapanmış 1 saatlik muma uygular:
   - EMA20, EMA50'nin üstünde mi? Buna "kısa trend yukarı" diyoruz.
   - Fiyat EMA200'ün üstünde mi? Buna "uzun trend yukarı" diyoruz.
   - VolTarget payı: coin ne kadar oynaksa bot ona o kadar az para koyar.
2. **Durum (`state`)**: Coin şu dört gruptan birine girer. Liste en iyiden en kötüye sıralı:
   - `ENTRY NOW`: Bu mumda EMA20, EMA50'yi yukarı kesti ve fiyat EMA200'ün üstünde. Bot bu coinde olsaydı şimdi alırdı.
   - `in trend`: İki trend de yukarı. Bot bu coinde olsaydı muhtemelen elinde tutuyor olurdu.
   - `above EMA200, short trend down`: Uzun trend yukarı ama kısa trend aşağı dönmüş. Bot bekler.
   - `below EMA200`: Fiyat uzun trendin altında. Bot hiç almaz.
3. **`vs_ema200`**: Fiyat EMA200'den yüzde kaç uzakta? Artı değer, fiyatın çizginin üstünde olduğunu gösterir.
4. **`ret30`**: Son 30 günde fiyat yüzde kaç değişti?

## Tablo nasıl sıralanıyor (`scan`)

- Önce duruma göre sıralanır, `ENTRY NOW` en üstte olur.
- Aynı durumdaki coinler, EMA200'ün en çok üstünde olandan başlayarak sıralanır.
- Verisi olmayan ya da 30 günden az verisi olan coinler tabloya girmez. Bu coinler en altta "skipped" satırında yazar. Gizlenmezler.

## Alttaki özet satırı: piyasa genişliği

**Market breadth** (piyasa genişliği), coinlerin yüzde kaçının EMA200'ün üstünde olduğunu söyler.

- %20 gibi düşük bir değer: Piyasanın çoğu düşüşte demektir. Bot bu durumda çoğunlukla nakitte bekler.
- %70 gibi yüksek bir değer: Yükselişin geniş bir alana yayıldığını gösterir.

Bu sayı şimdilik sadece bilgi amaçlı. Bir gün kurala katılacaksa, önce geçme şartı yazılmalı ve diğer fikirler gibi train ve validation testlerinden geçmeli.

## Testler (`tests/test_scan.py`)

- Sürekli yükselen bir coinin durumu `in trend` çıkıyor ve tabloda üstte yer alıyor. Sürekli düşen bir coinin durumu `below EMA200` çıkıyor.
- Verisi olmayan ya da çok az verisi olan coin "skipped" listesine düşüyor.
- Çıktıda botun 5 coini `*` ile işaretleniyor, piyasa genişliği yazıyor ve "yatırım tavsiyesi değildir" uyarısı bulunuyor.
- `ft.py scan` komutu önce 1 saatlik veriyi indiriyor ve bunu yaparken eski verileri silmiyor (`--erase` yok).

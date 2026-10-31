# Öğretici kart 02: Ölçme araçları (Faz 1)

Bu kartta 3 yeni dosya var: `scripts/splits.py`, `scripts/benchmark.py`, `scripts/ft.py`. Amaç tek: **bir kuralın işe yarayıp yaramadığını dürüstçe ölçmek.**

---

## 1. Neden ölçme aracı?

Backtest (geriye dönük test): kuralı geçmiş fiyatlar üzerinde oynatıp "o zaman bu kuralla işlem yapsaydım ne olurdu" diye bakmak.

İki tuzak var:
1. **Kıyas olmadan sayı anlamsız.** "Bot %50 kazandı" iyi mi? Aynı dönemde coinleri alıp hiç dokunmasan %200 kazanıyorsan kötü. Bu yüzden her sonucun yanına **al-tut** sonucu koyuyoruz (`benchmark.py`).
2. **Ezberleme (overfitting).** Aynı veride kuralı defalarca kurcalarsan, sonunda o verinin tesadüflerine uyan bir kural bulursun. Yeni veride çöker. Bu yüzden veriyi 3'e bölüp en son parçayı saklıyoruz (`splits.py`) ve bu kuralı kodla zorluyoruz (`ft.py`).

## 2. `splits.py`: veriyi 3'e bölmek

```
2021-01-01 ──── train (%60) ──── 2024-06-13 ── validation (%20) ── 2025-08-07 ── test (%20) ── 2026-10-01
```

- **train (ayarlama):** Fikirleri burada deneriz. Kural kurcalamak serbest.
- **validation (kontrol):** Train'de işe yarayan, burada da işe yarıyor mu? Yaramıyorsa train'deki başarı muhtemelen tesadüftü.
- **test (final sınavı):** Her strateji için **bir kere**, en sonda bakılır. Sonucu ne çıkarsa o. Beğenmeyip kuralı değiştirip tekrar bakmak yasak.

Neden tarihler sabit (`DATA_END = 2026-10-01`)? Bitiş tarihi "bugün" olsaydı her gün dilimler kayardı; dün test diliminde olan gün bugün validation'a geçer, sınav soruları sızardı.

Neden 2021'den başlıyor? SOL Binance'te 2020 Ağustos'ta listelendi. 5 coinin hepsinin verisi olan ilk temiz tarih bu.

Bu 6 yıllık dönem kripto için farklı "hava durumları" içeriyor: 2021 büyük yükseliş, 2022 çöküş, 2023 toparlanma, 2024-25 yükseliş. Train diliminde hem yükseliş hem çöküş var; bu iyi, kural sadece bir havaya göre ayarlanmaz.

`@dataclass(frozen=True)`: Python'da sadece veri tutan küçük sınıf. `frozen` = oluşturulduktan sonra değiştirilemez (dilimler yanlışlıkla değiştirilmesin).

`timerange` özelliği tarihi Freqtrade'in istediği biçime çevirir: `20210101-20240613`.

## 3. `benchmark.py`: al-tut hesabı

Ne yapıyor:
1. Config'teki 5 coini okur.
2. Her coinin indirilmiş fiyat dosyasını (`user_data/data/binance/BTC_USDT-1h.feather`) açar. Feather: tabloları hızlı okuyup yazmak için bir dosya biçimi; Freqtrade veriyi böyle saklar.
3. Sadece seçilen dilimin tarihlerini alır.
4. Parayı 5'e böler, ilk mumda alır, son mumda satar, iki tarafta da %0,15 komisyon öder.
5. Raporlar:
   - **Toplam getiri:** başlangıçtan sona yüzde kaç kazanç/kayıp.
   - **CAGR (yıllık büyüme):** "her yıl ortalama yüzde kaç büyüdü". Farklı uzunluktaki dönemleri kıyaslamak için.
   - **Max drawdown (en büyük düşüş):** en yüksek noktadan sonra en kötü anda yüzde kaç aşağıdaydı. "En kötü günde ne kadar canın yanardı".
   - **Calmar:** CAGR / max drawdown. "Aldığın acı başına ne kadar kazandın". Bizim ana başarı ölçütümüz.

Önemli fonksiyonlar:

```python
units = weight * (1 - fee) / frame.iloc[0]
```
Her coine ayrılan paydan (ör. 0,2) komisyonu düş, ilk fiyata böl → kaç adet coin alındı.

```python
equity = (frame * units).sum(axis=1)
```
Her an: adet × o anki fiyat, 5 coin için topla → portföyün o anki değeri.

```python
(1 - equity / equity.cummax()).max()
```
`cummax()` = "o ana kadarki en yüksek değer". Her an için tepeden ne kadar aşağıda olduğumuzu hesapla, en kötüsünü al.

## 4. `ft.py`: güvenli komut aracı

Freqtrade komutları uzun ve hata yapmaya açık. Yanlış `--timerange` yazmak = test dilimini kazara görmek. Bu araç komutu senin yerine kurar:

| Komut | Ne yapar | Kilit |
|---|---|---|
| `ft.py download` | 2020 Ekim'den bugüne 1h ve 4h mumları indirir | Ekim 2020: EMA200'ün ısınması için 3 ay fazladan veri |
| `ft.py backtest --slice train` | Train diliminde backtest | Tarihler sadece `splits.py`'dan; komisyon hep %0,15 |
| `ft.py backtest --slice test` | **Reddeder** | `--final-test` eklemeden test dilimi açılmaz |
| `ft.py hyperopt` | Otomatik parametre arama | **Sadece train**; başka dilim seçeneği hiç yok |

Hyperopt: Freqtrade'in "bu kuraldaki sayıların binlerce kombinasyonunu dene, en iyisini bul" aracı. En tehlikeli araç budur (en çok ezberleyen), o yüzden kilidi en sıkı.

Her backtest/hyperopt çalıştırması `docs/experiments.md` dosyasına otomatik bir satır ekler. Neden: "kaç kere denedik" sayısı önemli. 100 deneme sonra bulunan "harika" sonuç, 3 denemede bulunandan çok daha şüphelidir.

`docker compose run --rm freqtrade ...`: Çalışan botun yanında, aynı image'dan geçici bir kutu açar, komutu çalıştırır, kutuyu siler (`--rm`). Çalışan bot etkilenmez.

## 5. Testler (`tests/test_scripts.py`, 13 test)

- Dilimler boşluksuz ve üst üste binmeden arka arkaya mı? Test dilimi %20 mi?
- Al-tut hesabı: 100 → 200 = 2 kat mı? Komisyon iki kere mi alınıyor? Eşit ağırlık doğru mu? Max drawdown doğru mu?
- Sahte fiyat dosyaları üretip `benchmark.py`'nin dosyayı doğru okuduğunu ve sadece dilim tarihlerini aldığını kontrol.
- `ft.py`: test dilimi bayraksız reddediliyor mu? Hyperopt hep train mi?

Toplam: 38 test.

---

## Anlaman gerekenler

1. Her sonuç al-tut ile yan yana okunur; ana ölçüt Calmar (acı başına kazanç).
2. Veri 3'e bölündü; son %20'ye her strateji için bir kere bakılır, kod bunu zorlar.
3. Her deneme sayılır; çok denemeden sonra gelen "harika" sonuç şüphelidir.

# Öğretici kart 09: Saat saat düşüş ve "paranın ne kadarı coinde"

## Sorun: Eski düşüş ölçümü iyimserdi

Freqtrade'in düşüş ölçümü sadece bir işlem **kapanınca** değişir.

Örnek:
- 100 USDT'lik BTC aldın.
- Fiyat bir hafta boyunca düşüp işlemin -%15'e kadar indi.
- Sonra toparlandı ve işlem -%2 ile kapandı.

Freqtrade'in hesabına sadece -%2 girer. Ama o hafta hesabın gerçekten -15 USDT eksikteydi. Gerçek hayatta o acıyı yaşardın.

Al-tut'un düşüşünü ise her saat ölçüyorduk. Yani iki tarafı farklı cetvelle ölçüyorduk. Haksız kıyas.

## Çözüm: "Mark to market"

Türkçesi: "piyasa fiyatından değerle". Her saat şunu hesapla:

```
hesap değeri = başlangıç parası
             + kapanmış işlemlerin kâr/zararı
             + açık işlemlerde: (elindeki coin adedi × şu anki fiyat − o işleme koyduğun para)
```

Kod: `scripts/equity.py`, `hourly_equity()`.

1. Her işlem için kapanış saatinden itibaren `profit_abs` (gerçekleşen kâr/zarar) eklenir.
2. İşlem açıkken, her saat `amount × fiyat − stake_amount` hesaplanır. `amount` coin adedi, `stake_amount` koyulan para.
3. Aynı saatte açık işlemlerin parası `invested` sütununda toplanır.

Sonra düşüş, al-tut'la aynı formülle hesaplanır: her saat, o ana kadarki zirveden ne kadar aşağıdayız, en kötüsünü al.

Küçük iyimserlik: açık işlemi satarken ödenecek komisyon henüz düşülmüyor. Etkisi işlem başına ~%0,15, çok küçük.

## "In coins": paranın ne kadarı gerçekten işlemde?

```
exposure = her saat (coinlerdeki para ÷ toplam hesap), tüm saatlerin ortalaması
```

Örnek: Bu oran %20 ise, paranın ortalama %80'i nakitte bekliyor demektir.

- **Yükselişte:** Al-tut'un çok gerisinde kalmamızın ana nedeni bu olabilir. Nakitteki para kazanmaz.
- **Çöküşte:** Bizi koruyan da bu. Nakitteki para kaybetmez.

## Rapor ne değişti?

- `MaxDD`: artık saat saat, açık işlemler dahil ölçülüyor.
- `Calmar` ve `PASS/FAIL`: bu yeni, daha dürüst düşüşe göre hesaplanıyor. Bazı eski PASS'ler FAIL'e dönebilir; bu iyi bir şey, kendimizi kandırmamış oluyoruz.
- `In coins`: yeni sütun.
- Kill switch işareti hâlâ **kapanmış** işlem düşüşüne bakıyor, çünkü gerçek bot da öyle çalışıyor.

## Testler (4 yeni, toplam 110)

- İşlem açıkken fiyat 70'e düşüp 98'de kapanınca saatlik düşüş %3 çıkıyor. Kapanmış işlem ölçümü ise sadece %0,2 gösterirdi.
- 6 saatin 3'ünde paranın %25'i coinde → ortalama %12,5.
- İki coin doğru toplanıyor. Fiyatı olmayan coin çökertmiyor.
- Calmar saatlik düşüşü, kill switch işareti kapanmış işlem düşüşünü kullanıyor.

---

## Anlaman gerekenler

1. Aynı cetvelle ölç: al-tut saat saat ölçülüyorsa bot da öyle ölçülmeli.
2. Paranın çoğu nakitteyse yükselişte az kazanırsın, çöküşte az kaybedersin.
3. Daha dürüst ölçüm bazı sonuçları kötüleştirebilir. Bu kötü haber değil, gerçek haber.

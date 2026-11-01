# 14. DCA: her hafta biraz almak (Faz 2, üçüncü aile)

## Fikir

DCA (Dollar Cost Averaging, maliyet ortalaması) en basit yatırım yöntemidir:

> Paranı bir kerede yatırmazsın. Her hafta aynı miktarı alırsın.

Fiyat düşükken aynı parayla daha çok coin, yüksekken daha az coin alırsın. Hiçbir tahmin, gösterge ya da kural yoktur.

## Neden ölçüyoruz?

1. **Dürüst bir rakip.** Botumuz parasının çoğunu nakitte tutuyor. DCA da başta parasının çoğunu nakitte tutar. Botun "akıllı" kuralları, aptalca düzenli alımı yenebiliyor mu?
2. **"Faiz de kazandırır" sorusu.** DCA'nın yıllık getirisini (CAGR) mevduat faiziyle yan yana koyabiliriz.

## Nasıl hesaplanıyor (`scripts/benchmark.py`, `dca_equity`)

Al-tut ile aynı koşullar geçerli. Başlangıç parası 1,0 kabul ediliyor.

1. Para başta nakit duruyor.
2. Dilimdeki takvim haftaları sayılıyor. Train diliminde yaklaşık 180 hafta var.
3. Her haftanın ilk saatinde paranın 1/180'i harcanıyor ve coinlere eşit bölünüyor.
4. Her alımda komisyon (%0,15) ödeniyor.
5. Dilimin sonunda her şey satılıyor ve bir kez daha komisyon ödeniyor.
6. Her saat değer şöyle hesaplanıyor: kalan nakit + (sahip olunan coin × o saatin fiyatı).

```python
buy_rows = ~periods.duplicated()            # her haftanın ilk mumu True
bought = (per_pair * (1 - fee) / frame).mul(buy_rows, axis=0)  # o mumda alınan coin
units = bought.cumsum()                     # o ana kadar biriken coin
cash = 1 - (alım sayısı / toplam alım)       # harcanmamış para
```

**Basitleştirme:** Nakit burada faiz kazanmıyor. Gerçekte bekleyen para mevduatta faiz kazanabilir. Bu DCA'yı biraz kötü gösterir. Aynı durum botun nakdi için de geçerli.

## Testler

- Fiyat hiç değişmezse ve komisyon yoksa para aynı kalıyor.
- 3 haftada 3 alım yapılıyor. 3. hafta fiyat ikiye katlanırsa sonuç 2/3 × 2 + 1/3 oluyor. Bu, son haftada da alındığını ve paranın tamamen harcandığını gösteriyor.
- İlk saatte çöküş olursa DCA, al-tut'tan az düşüyor. Çünkü parası henüz nakitteydi.
- Komisyon hem alımda hem de son satışta ödeniyor.

## Komut

```bash
python3 scripts/ft.py benchmark --slice train
```

Al-tut'un altına DCA satırları da yazılır.

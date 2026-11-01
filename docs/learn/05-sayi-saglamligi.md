# Öğretici kart 05: Sayı sağlamlığı testi

## Neden?

TrendEmaSlow iki dönemi de geçti. Ama 50, 200 ve 600 sayılarını biz seçtik. Şu soruyu sormamız lazım:

**"Bu sayılar şanslı mıydı?"**

Örnek: 50 yerine 40 veya 60 deyince sonuç çöküyorsa, kural aslında çalışmıyordu. Bu üç sayıya tesadüfen denk gelmiştik. Sağlam bir kural, sayılar biraz oynayınca da benzer sonuç verir.

Benzetme: Bir köprü sadece tam 50 kiloda ayakta duruyor ama 40 ya da 60 kiloda çöküyorsa, o köprüye güvenmezsin.

## Ne yaptık?

6 "komşu" strateji yazdık. Her biri TrendEmaSlow'dan **tek bir sayıyı** yaklaşık %25 oynatıyor:

| Sınıf | Hızlı | Yavaş | Trend |
|---|---|---|---|
| TrendEmaSlow (asıl) | 50 | 200 | 600 |
| SlowFast40 | **40** | 200 | 600 |
| SlowFast60 | **60** | 200 | 600 |
| SlowSlow150 | 50 | **150** | 600 |
| SlowSlow250 | 50 | **250** | 600 |
| SlowTrend450 | 50 | 200 | **450** |
| SlowTrend750 | 50 | 200 | **750** |

## Kod

Bunu yapabilmek için TrendEmaSlow'daki sabit sayıları sınıf özelliğine çevirdik:
```python
fast_len, slow_len, trend_len = 50, 200, 600
```
Komşu sınıf sadece bir sayıyı ezer:
```python
class SlowFast40(TrendEmaSlow):
    fast_len = 40
```
Kodun geri kalanı aynı kalıyor.

`startup_candle_count = 1500`: en uzun ortalama 750 saat. Doğru hesaplanması için en az bunun 2 katı ısınma mumu gerekir.

## Nasıl okuyacağız?

Sadece **train** diliminde bakıyoruz. Validation'a bir daha bakmıyoruz, çünkü o dilim zaten 2 kere kullanıldı.

- **Sağlam:** komşuların çoğu asıl stratejiye yakın (Calmar ~2-3) ve hâlâ al-tut'tan (1,69) iyi.
- **Kırılgan:** bir iki komşu çöküyor (Calmar 1'in altı).

Önemli: En iyi komşuyu seçip "o daha iyi" **demeyeceğiz**. Bu test seçim yapmak için değil, güven ölçmek için. En iyiyi seçmek ezberlemeye geri dönmek olur.

## Testler (12 yeni, toplam 77)

- Her komşu tam olarak bir sayıyı değiştiriyor.
- Sayıların sırası korunuyor: hızlı < yavaş < trend.
- Isınma mum sayısı yeterli.
- Risk kuralları (%8 tavan, frenler, kill switch) aynı.

---

## Anlaman gerekenler

1. Sağlam kural, sayılar biraz oynayınca çökmez.
2. Bu test seçim için değil, güven ölçmek için. En iyi komşuya geçmiyoruz.
3. Validation'a artık az bakıyoruz, bu yüzden bu test sadece train'de.

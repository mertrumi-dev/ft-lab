# Öğretici kart 08: Yıl yıl analiz

## Neden?

"3,5 yılda +%254" tek bir sayı. Ama içinde çok farklı piyasa havaları var:

| Yıl | Kripto piyasasının havası |
|---|---|
| 2021 | Büyük yükseliş (boğa piyasası) |
| 2022 | Büyük çöküş (ayı piyasası) |
| 2023 | Toparlanma |
| 2024 (Haziran'a kadar) | Yükseliş |

Bir kural mesela sadece 2021'de çok kazanıp diğer yıllarda zarar ediyorsa, aslında "iyi" değil, "2021'e denk gelmiş" demektir. Yıl yıl bakınca bunu görürüz. Ayrıca BTC filtresi gibi fikirlerin **hangi havada** işe yaradığını da görürüz.

Önemli: Bu yeni bir test değil. Elimizdeki eski backtest sonuçlarını yıllara bölüyoruz. Yeni deneme sayılmaz.

## Kod

**Al-tut için** (`benchmark.by_year`): Portföy değeri serisini yıllara böl (`groupby(index.year)`). Her yıl için:
- getiri = yıl sonu ÷ yıl başı − 1,
- en büyük düşüş = o yıl içindeki en kötü düşüş.

**Strateji için** (`report.strategy_by_year`):
1. İşlemleri kapanış tarihine göre sırala.
2. Bakiye 1000'den başlar. Her işlem kapanınca kârı/zararı (`profit_abs`) eklenir.
3. Her yıl için şunlar tutulur: yıl başı bakiyesi, yıl içindeki zirve, zirveden en kötü düşüş, işlem sayısı.
4. Getiri = yıl sonu bakiyesi ÷ yıl başı bakiyesi − 1.

Bileşik hesap: 2022'deki %10 kazanç 1000'in değil, 2022 başındaki bakiyenin %10'u.

Dikkat: Strateji düşüşü sadece **kapanmış** işlemlerden hesaplanıyor. Açık işlemin geçici düşüşü dahil değil, yani biraz iyimser.

Bir yılda hiç işlem yoksa tabloda "no trades" yazar.

## Komut

```
python3 scripts/ft.py report --slice train --by-year --strategy TrendEma TrendEmaSlow TrendEmaBtc
```
`--strategy`: tabloda sadece bu stratejiler görünsün (kalabalık olmasın).

## Testler (4 yeni, toplam 106)

- Al-tut: yıllar doğru ayrılıyor, getiri ve düşüş doğru.
- Strateji: bakiye bileşik büyüyor; 2022'deki -%20'lik düşüş doğru yakalanıyor.
- İşlemsiz yıl "no trades" yazıyor.
- `ft.py`, `--by-year` ve `--strategy` ayarlarını rapora aktarıyor.

---

## Anlaman gerekenler

1. Toplam sayı, kötü yılları gizleyebilir; her zaman yıl yıl bak.
2. Bu analiz yeni deneme değil, eski sonuçların yıllara bölünmüş hali.
3. Trend takibinin beklenen hali: yükselişte al-tut'tan az kazanmak, çöküşte çok daha az kaybetmek.

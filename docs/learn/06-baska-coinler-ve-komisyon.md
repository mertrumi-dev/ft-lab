# Öğretici kart 06: Başka coinler ve 2 kat komisyon

TrendEmaSlow iki sınavı ve sayı sağlamlığını geçti. Ama hâlâ iki açık soru var. Bu kartta bu iki soruyu ölçen araçları yazdık. Bunlar yeni kural denemesi değil; mevcut kurala "gerçekten sağlam mısın?" diye soruyoruz.

## Soru 1: "Sadece bu 5 coinde mi çalışıyor?"

**Sorun:** BTC, ETH, SOL, BNB ve XRP'yi 2026'dan geriye bakarak seçtik. Hepsi ayakta kalmış kazananlar. Bu yüzden sonuçlar olduğundan iyi görünebilir. Buna "hayatta kalan yanılgısı" (survivorship bias) deniyor.

Benzetme: Sadece piyango kazananlarıyla konuşup "piyango iyi yatırım" demek gibi.

**Çözüm:** Ocak 2021'de piyasa değeri en büyük ~25 coinin arasından 15 tanesi (`scripts/universe.py`). Seçimi 2021'de birinin bilebileceği şeye göre yaptık. Bu yüzden listede sonradan çok değer kaybedenler de var (EOS, THETA, FIL, VET...). Kural bu coinlerde de al-tut'tan iyi "acı başına kazanç" veriyorsa, başarı coin seçiminden değil kuraldan geliyor demektir.

- Ana 5 coin listede yok. Böylece iki grubun sonuçları raporda asla karışmaz (testte kontrol ediliyor).
- Binance'ten tamamen kaldırılmış (delist) bir coinin verisi indirilemez. Rapor bunu "No data (skipped)" diye yazar ve o coini atlar.
- Al-tut kıyası da aynı 15 coinle yapılır. Elma ile elma.

Komut:
```
python3 scripts/ft.py download --universe wide
python3 scripts/ft.py backtest --slice train --universe wide --strategy TrendEma TrendEmaSlow
python3 scripts/ft.py report --slice train --universe wide
```
`--pairs ...`: Freqtrade'e "config'teki coinler yerine bunları kullan" der. `ft.py` bunu senin yerine ekler.

## Soru 2: "Komisyon 2 katına çıkarsa?"

Şu an her alış ve satışta %0,15 düşüyoruz (gerçek %0,1 + kayma payı). `--fee-stress` bunu **%0,3** yapar. Kural bu kadar kötü maliyetle de ayakta kalıyorsa, komisyon konusunda içimiz rahat olur.

```
python3 scripts/ft.py backtest --slice train --fee-stress --strategy TrendEma TrendEmaSlow
python3 scripts/ft.py report --slice train --fee-stress
```

## Rapor neden değişti?

Eskiden rapor "bu tarih aralığındaki en son sonuç" diye bakıyordu. Artık aynı tarih aralığında 3 farklı tür sonuç olabilir:
- normal,
- başka coinler,
- 2 kat komisyon.

Bunlar karışırsa tablo yalan söyler. `report.matches()` artık 3 şeye birden bakıyor:
1. Aynı dilim mi? (`timerange`)
2. Aynı coin grubu mu? (`pairlist`: Freqtrade'in sonuç dosyasına yazdığı, verisi olan coinler)
3. Aynı komisyon mu? (ilk işlemin `fee_open` değeri)

İşlem yoksa komisyon bilinemez. O sonuç tabloya alınmaz.

## Testler (6 yeni, toplam 83)

- Normal komut: `--pairs` yok, komisyon %0,15.
- `--universe wide`: 15 coin ekleniyor, test dilimi kilidi hâlâ çalışıyor.
- Ana 5 coin ile geniş liste çakışmıyor.
- `--fee-stress`: sadece istenince %0,3.
- Rapor farklı dilim, coin grubu veya komisyonla alınmış sonuçları karıştırmıyor.
- Verisi olmayan coin atlanıyor. Ana 5'ten biri eksikse ise hata veriyor (orada eksik veri kabul edilemez).

---

## Anlaman gerekenler

1. Bunlar yeni kural değil, mevcut kuralın sağlamlık sınavları. Sonucu ne çıkarsa kuralı ona göre değiştirmiyoruz, sadece güvenimizi ölçüyoruz.
2. Başka coinlerde de çalışan kural, coin seçimi şansına dayanmıyor demektir.
3. Rapor artık sadece birbiriyle kıyaslanabilir sonuçları aynı tabloya koyuyor.

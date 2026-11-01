# Öğretici kart 21: Piyasa rejimi kapısı (TrendEmaBtcRising)

## Soru

Final sınavında (Ağu 2025 – Eki 2026) TrendEma'nın işlemlerinin çoğu kaybetti. Aklımıza gelen soru: "Bot, piyasanın genel havası kötüyken de alım yapıyor mu? O zamanlar mı kaybettiriyor?"

Kural: Final sınavı verisine bakıp kural değiştirmek yasak. Bu yüzden soruyu **sadece train dilimindeki** 638 işlemle cevapladık.

## Analiz (train, 2021-01 → 2024-06)

Her işlemin açıldığı günde piyasanın durumuna baktık. Sadece **o gün zaten bilinen** bilgiyi kullandık (önceki günün kapanışı):

| İşlem açılırken... | İşlem | Toplam |
|---|---|---|
| BTC'nin 50 günlük ortalaması (SMA50) **yükseliyor** (10 gün öncekinden yüksek) | 376 | **+2.837 USDT** |
| BTC'nin SMA50'si **düşüyor** | 262 | **−294 USDT** |
| BTC 200 günlük ortalamanın üstünde / altında | 411 / 227 | +1.973 / +569 |
| Oynaklık ve "testere" ölçüleri | çeyreklere böl | net bir desen yok |

En net ayrım SMA50'nin yönü: piyasa genel olarak aşağı giderken açılan işlemler toplamda zarar etmiş.

## Kural

`user_data/strategies/regime.py` → `TrendEmaBtcRising`: TrendEma aynen çalışır. Tek fark: **BTC'nin günlük SMA50'si 10 gün öncekinden yüksek değilse yeni alım yok.** Çıkış, stop, pozisyon büyüklüğü ve kill switch aynı.

### Geleceğe bakmama (lookahead)

Günlük mum "D günü" diye etiketlenir ama ancak D+1 00:00'da biter. Kod (`attach_btc_rising`) bu yüzden her günlük değeri **ertesi gece yarısından itibaren** kullanır. Testler bunu kilitliyor: dönüş günü boyunca bot hâlâ önceki günün değerini görür; gelecekteki mumları değiştirmek geçmiş kararları değiştirmez.

### Bulunan hata

İlk koşuda bot çöktü: Freqtrade saatlik veriyi milisaniye, günlük veriyi mikrosaniye zaman birimiyle verdi. `merge_asof` (iki tabloyu zamana göre birleştirme) farklı birimleri kabul etmiyor. Çözüm: ikisini de nanosaniyeye çevirmek. Hatayı yakalayan test de eklendi.

## Sonuçlar

**Dikkat:** Fikir train işlemlerine bakılarak bulundu, bu yüzden train'deki iyi sonuç **kanıt değil**. Kanıt, fikre hiç bakılmamış verilerden gelir.

| Veri | TrendEma | TrendEmaBtcRising | Not |
|---|---|---|---|
| Train 5 coin (fikrin kaynağı) | Calmar 2,70, DD %16,4 | 5,18, DD %9,5 | kanıt değil |
| **Train 14 coin** (fikre bakılmadı) | 0,76, DD %41,3 | **1,10, DD %32,9** | gerçek iyileşme |
| Taze veri, Ekim 2026 | −3,3% | −3,3% (aynı) | kapı hiç kapanmadı |

Ekim'de neden kapanmadı? BTC 86 bin dolardan 78 bine yavaşça düştü (−%10), ama 50 günlük ortalama hâlâ yükseliyordu. Altcoinler BTC'den çok daha sert düştü. Yani bu kapı "BTC'nin yavaş ortalaması aşağı dönene kadar" geç kalıyor.

## Anlaman gerekenler

- **Fikri bulduğun veride fikri test edemezsin.** Train'de 2,70 → 5,18 etkileyici görünüyor, ama fikir zaten oradan çıktı. Asıl bilgi 14 coin sonucunda: 0,76 → 1,10.
- **Yavaş göstergeler geç uyanır.** SMA50 gibi bir ortalama büyük düşüşlerden korur, ama yavaş ve sinsi düşüşlerde geç kalır.
- **Zaman birimlerine dikkat.** Aynı görünen iki tarih sütunu farklı tipte olabilir; birleştirmeden önce tipleri eşitle.

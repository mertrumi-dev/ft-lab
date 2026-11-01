# Araştırma 10: Final test otopsisi (VolTarget ve TrendEma, 2026-11-01)

Sadece analiz. Test dilimi (2025-08-07 → 2026-10-01) iki kural için de **kullanıldı**. Buradan çıkan hiçbir şey bu iki kuralı değiştiremez. Her fikir aşağıdaki listeye "ön kayıt + sadece taze veride doğrulama" notuyla gider.

Komut: `python3 scripts/ft.py postmortem` (sadece test dilimi, ay ay). Kill switch açık (canlıdaki gibi): TrendEma Nisan 2026'da, VolTarget Temmuz 2026 sonunda durdu.

## Aylık getiri (ay sonu değer, kill switch açık)

| Ay | BTC rejimi (boğa/yatay/ayı) | VolTarget | TrendEma | TSMOM | Haftalık DCA | Al-tut |
|---|---|---|---|---|---|---|
| 2025-08 | 100/0/0 | -4.8% | -5.5% | +5.9% | -0.0% | +7.4% |
| 2025-09 | 100/0/0 | -0.6% | -0.6% | +0.4% | +0.3% | +4.7% |
| 2025-10 | 87/13/0 | -2.0% | -2.1% | +0.7% | -1.1% | -4.6% |
| 2025-11 | 10/77/13 | -2.8% | -3.6% | +0.0% | -4.8% | -20.8% |
| 2025-12 | 0/0/100 | -4.6% | -5.2% | -0.3% | -1.4% | -4.7% |
| 2026-01 | 0/0/100 | +1.1% | +1.3% | -9.4% | -5.1% | -12.5% |
| 2026-02 | 0/0/100 | -0.5% | -0.7% | +0.0% | -6.9% | -18.8% |
| 2026-03 | 0/0/100 | -2.8% | -3.9% | -5.8% | +0.4% | +1.1% |
| 2026-04 | 0/0/100 | -2.1% | -1.6% | -1.1% | +2.1% | +4.0% |
| 2026-05 | 0/0/100 | +0.8% | +0.0% | +3.8% | -0.6% | +0.5% |
| 2026-06 | 0/0/100 | -0.8% | +0.0% | -2.6% | -13.6% | -20.1% |
| 2026-07 | 0/0/100 | -2.4% | +0.0% | -1.9% | +4.5% | +7.0% |
| 2026-08 | 0/39/61 | -0.2% | +0.0% | +11.2% | +25.1% | +27.8% |
| 2026-09 | 90/10/0 | +0.0% | +0.0% | +6.1% | +9.3% | +9.9% |

## TrendEmaVolTarget: kapanan işlemler (kapanış ayına göre)

| Ay | İşlem | K/Z USDT | Kazanan | Stop çıkışı | Sinyal çıkışı |
|---|---|---|---|---|---|
| 2025-08 | 20 | -46.9 | %15 | 1 | 19 |
| 2025-09 | 17 | -7.6 | %18 | 0 | 17 |
| 2025-10 | 13 | -18.9 | %23 | 0 | 13 |
| 2025-11 | 6 | -22.2 | %0 | 1 | 5 |
| 2025-12 | 20 | -44.2 | %10 | 0 | 20 |
| 2026-01 | 14 | +8.1 | %36 | 0 | 14 |
| 2026-02 | 4 | -4 | %0 | 0 | 4 |
| 2026-03 | 20 | -24.2 | %30 | 0 | 20 |
| 2026-04 | 21 | -17.4 | %29 | 0 | 21 |
| 2026-05 | 12 | -1.5 | %50 | 0 | 12 |
| 2026-06 | 6 | +1.1 | %67 | 0 | 6 |
| 2026-07 | 22 | -21.6 | %18 | 0 | 22 |
| 2026-08 | 1 | +0.9 | %100 | 0 | 1 |
| **Toplam** | 176 | -198.4 | | 2 | 174 |

## TrendEma: kapanan işlemler (kapanış ayına göre)

| Ay | İşlem | K/Z USDT | Kazanan | Stop çıkışı | Sinyal çıkışı |
|---|---|---|---|---|---|
| 2025-08 | 20 | -53.2 | %15 | 1 | 19 |
| 2025-09 | 17 | -7.2 | %18 | 0 | 17 |
| 2025-10 | 13 | -20.1 | %23 | 0 | 13 |
| 2025-11 | 6 | -28.8 | %0 | 1 | 5 |
| 2025-12 | 20 | -48.7 | %10 | 0 | 20 |
| 2026-01 | 14 | +8.8 | %36 | 0 | 14 |
| 2026-02 | 4 | -5.7 | %0 | 0 | 4 |
| 2026-03 | 20 | -32.8 | %30 | 0 | 20 |
| 2026-04 | 7 | -13 | %14 | 0 | 7 |
| **Toplam** | 121 | -200.6 | | 2 | 119 |

## Rejime göre (bütün test dilimi, saatlerin getirisi yıla çevrilmiş)

| | boğa | yatay/testere | ayı |
|---|---|---|---|
| zamanın payı | %27 | %10 | %63 |
| Buy & hold | -9% | +185% | -43% |
| Weekly DCA | +7% | +246% | -16% |
| TSMOM | +35% | +218% | -21% |
| TrendEmaVolTarget | -23% | -16% | -16% |
| TrendEma | -25% | -20% | -14% |

Ek ölçüm: VolTarget 176 işlemde **52,7 USDT komisyon** ödedi. Bu, 198,4 USDT'lik kaybın **%27**'si. Komisyonsuz da kaybederdi (-145,7). TrendEma: 121 işlem, 39,7 USDT komisyon (kaybın %20'si). Ortalama tutma süresi ~2 gün (VolTarget 45,7 saat).

## Ne oldu?

- **Bin küçük kesik:** 176 çıkışın 174'ü sinyalle (EMA20, EMA50'yi aşağı kesti), sadece 2'si stop'la. Kazanma oranı çoğu ay %10-30. Büyük bir çöküş yemedi; her işlem 1-3 USDT kaybettirdi ve bunlar birikti.
- **Her rejimde kaybetti:** Saatlik getirinin yıla çevrilmiş hali, boğa günlerinde -%23, yatayda -%16, ayıda -%16. Train/early'de (araştırma 06) zayıf yer sadece testereydi. Bu dönemde 1 saatlik grafikte **boğa ayları da testereydi**: Ağustos-Ekim 2025'te BTC rejimi %87-100 boğa iken coin tutmak +%7, +%5 getirdi, bot ise -%5, -%1, -%2.
- **Ayıda koruma kısmen çalıştı:** Zamanın %63'ü ayıydı. Coin tutmak yıllık -%43, VolTarget -%16. Ama bot ayı aylarında da durmadı: Aralık, Mart, Nisan ve Temmuz'da 20+ işlem yaptı. Ana kural coin bazında (coinin kendi EMA200'ü), BTC'nin ayısına bakmıyor.
- **Kill switch toparlanmayı kaçırttı:** Ağustos-Eylül 2026'da coin tutmak +%28 ve +%10, haftalık DCA +%25 ve +%9 yaptı. İki bot da o sırada kill switch nedeniyle kapalıydı. Bu R13'ün bilinen bedeli: güvenlik, getiriden önce gelir.

## TSMOM ve haftalık DCA neden artıda kaldı?

- **TSMOM** günlük grafikte, 28 günlük momentuma bakıyor. Çok daha az işlem yapıyor (131 gün değişimi, saatlik kesişme değil) ve saatlik testereden etkilenmiyor. Boğa aylarında (Ağustos-Ekim 2025) artıdaydı. Ayının ilk aylarında -%9, -%6 yedi, son iki ayın toparlanmasını yakaladı (+%11, +%6). Kill switch'i yok.
- **Haftalık DCA** hiçbir sinyale bakmadan her hafta alıyor. Ayıda ucuzdan biriktirdi; Ağustos-Eylül 2026'daki sert toparlanma bütün yılı artıya çevirdi (+%3,4). Düşüşü ise büyük (%31).
- İkisinin ortak noktası: **yavaşlar ve son toparlanmada piyasadaydılar.** Bizim iki bot hızlıydı (saatlik) ve sonda kapalıydı.

## 3 ders

1. **Saatlik EMA kesişmesi, trend olmayan bir yılda komisyon ve testere yüzünden ay ay kanar.** Kayıp stop'lardan değil, küçük sinyal çıkışlarının birikmesinden geldi. Komisyon kaybın dörtte biri. Boyut küçültme (VolTarget) bunu yavaşlattı, durdurmadı.
2. **"Rejim" ölçeğe bağlıdır.** BTC'nin günlük grafiği "boğa" derken saatlik grafik testere olabilir. Train/early'deki "boğada kazanır" sonucu bu yıl tutmadı. Kuralın zaman ölçeği (1 saat), piyasanın o yılki hareket ölçeğine uymadı.
3. **Kill switch, kaybı %20'de tuttu, ama yeniden başlama kararı insana kalıyor.** Bu dönemde fren tam işini yaptı (en kötü düşüş %21 iken coin tutmakta %64). Ama sonraki toparlanmayı kaçırttı. "Ne zaman ve nasıl yeniden açılır" sorusunun cevabı belirsiz; bu bir kural değil, insan kararı. Bunun için yazılı bir kontrol listesi gerekiyor.

## Fikir listesi (ÖN KAYIT + SADECE TAZE VERİDE DOĞRULAMA; test dilimi kullanıldı, train/validation'da da türetilemez)

- [ ] Günlük zaman diliminde trend kuralı (az işlem, düşük komisyon). TSMOM'a yakın ama bizim risk kurallarımızla. Ön kayıt şart; hüküm sadece taze veride.
- [ ] Komisyona duyarlı giriş filtresi (beklenen hareket < işlem başına maliyet ise girme). Ön kayıt şart; sadece taze veride.
- [ ] Kill switch sonrası **insan kontrol listesi** (kural değil, prosedür): neden düştü, rejim ne, hangi koşulda yeniden açılır, kim karar verir. `docs/risk-rules.md`'ye eklenebilir (Kaan'la).
- [ ] Haftalık DCA'yı bir "çekirdek" olarak bot ile birleştirmek (ör. sermayenin bir kısmı DCA). Ön kayıt şart; sadece taze veride.

## Anlaman gerekenler

- **Otopsi suçlu aramak değil, mekanizmayı görmektir.** "Kötü yıl" demek yetmez; kaybın stop'lardan mı, komisyondan mı, sinyalden mi geldiğini ayırmak gerekir. Burada cevap: çok sayıda küçük sinyal çıkışı + komisyon.
- **Kullanılmış veriden kural çıkarılmaz.** Bu yılı gördükten sonra kuralı ona göre ayarlamak, aynı sınava ikinci kez girmek olur. Fikirler sadece yeni (taze) veride sınanabilir.
- **Yavaş ve basit bazen kazanır.** TSMOM ve DCA bu yıl daha iyiydi. Ama train/validation'da daha kötüydüler. Hiçbir yöntem her yıl en iyi değil.

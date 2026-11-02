# AI grafik yorumları (araştırma, bota bağlı DEĞİL)

Kural (2026-11-01'de, ilk yorumdan önce yazıldı):
- Her gün 5 coin için sadece günlük kapanış, EMA20/50/200, 30 günlük oynaklık ve hacim oranına bakılarak yazılır. Haber yok.
- Her yorum 7 gün sonrası için bir yön tahmini içerir: yukarı / aşağı / yatay (yatay = ±%2 içinde). Güven 1-3.
- Puanlama: 7 gün sonraki günlük kapanış ile, yorumun dayandığı kapanış karşılaştırılır.
- Karşılaştırma ölçüleri: yazı-tura (%33, üç seçenek) ve "hep yukarı" tahmini.
- Bot bu yorumları ancak 50'den fazla tahminde ikisini de geçerse kullanmayı düşünür. O zamana kadar sadece kayıt tutulur.
- Neden sadece yeni veri: model geçmişi biliyor olabilir, eski grafiklerde test etmek kopya olur.

| Tarih (son mum) | Coin | Kapanış | Yorum | 7 gün tahmini | Güven | Gerçekleşen (7g) | İsabet |
|---|---|---|---|---|---|---|---|
| 2026-10-31 | BTC | 77582 | Kapanış EMA20 (80716) ve EMA50'nin (80466) altında, EMA200'ün (76476) hâlâ üstünde. 4 Ekim'deki 86530 zirvesinden beri tepeler alçalıyor. 29 Ekim'de %4 sert düşüş oldu. Oynaklık düşük (%28), hacim normal. Kısa vade zayıf ama uzun vade desteği yakın. | aşağı | 1 | | |
| 2026-10-31 | ETH | 2255.66 | Üç ortalamanın da altında (EMA200 2318). Eylül sonundaki 2776'dan beri düzenli düşüş var, hacim biraz azalıyor. | aşağı | 2 | | |
| 2026-10-31 | SOL | 95.54 | Üç ortalamanın da altında, 100 seviyesi kırıldı. 25 Eylül'deki 122'den beri %22 düştü. | aşağı | 2 | | |
| 2026-10-31 | BNB | 703.95 | EMA20/50'nin (~732) altında, EMA200'ün (693) hemen üstünde. 29 Ekim'de %8 düştü, sonra iki gün yatay seyretti. Uzun ortalama destek olabilir. | yatay | 1 | | |
| 2026-10-31 | XRP | 1.2519 | Üç ortalamanın da altında, en zayıf yapı bu coinde. Hacim belirgin düşük (30g/90g = 0,68): satış baskısı azalıyor olabilir, ama alıcı da yok. | aşağı | 1 | | |
| 2026-11-01 | BTC | 78354 | EMA200'ün (76495) %2,4 üstünde, EMA20 (80491) ve EMA50'nin (80383) altında; iki ortalama birbirine çok yakın, kısa vade yönsüz. 29 Ekim'deki 77369 dibinden küçük bir toparlanma var. Oynaklık düşük (%28,5, haftalık ~%4), hacim normal (0,94). Uzun ortalama destek, kısa ortalamalar direnç: bir hafta bu aralıkta kalma ihtimali yüksek. | yatay | 1 | | |
| 2026-11-01 | ETH | 2275.31 | Üç ortalamanın da altında (EMA200 2317, EMA50 2422). Eylül sonundaki 2776'dan beri alçalan tepeler; 2245'teki 60 günlük dipten sadece %1 yukarıda. Hacim düşüyor (0,88). Zayıf yapı devam ediyor. | aşağı | 1 | | |
| 2026-11-01 | SOL | 94.53 | Üç ortalamanın da altında ve son kapanış 60 günün en düşüğü (122'den %23 aşağıda). EMA20 (102) EMA50'nin (104) altında, ikisi de düşüyor. Hacim azalıyor (0,81). Beş haftadır süren düşüş trendi. | aşağı | 2 | | |
| 2026-11-01 | BNB | 712.69 | EMA200'ün (693) %2,9 üstünde, EMA20/50'nin (~731) altında. 29 Ekim'deki %8'lik düşüşten (760 → 698) sonra yavaş toparlanma. Hacim normal (0,95). Uzun vade sağlam, kısa vade zayıf; oynaklık yüksek (%41) olduğu için yatay band dar, hafif yukarı eğilimli. | yukarı | 1 | | |
| 2026-11-01 | XRP | 1.2507 | Üç ortalamanın da altında, EMA20 < EMA50 < EMA200 (tam düşüş dizilimi). Son dört gün 1,24-1,26 arasında, 60 günlük dibin hemen üstünde. Hacim çok düşük (0,63): ilgi yok. | aşağı | 1 | | |

Toplam: 0 puanlanmış tahmin. İlk puanlama 2026-11-08'de yapılacak.

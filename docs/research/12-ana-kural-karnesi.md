# Araştırma 12: Ana kuralın karnesi (2026-11-02)

Neden: Kaan'ın isteği: "8 Kasım'a kadar ana kural optimum hale gelsin; önce sadece fiyatla çalışan basit hali." Bu belge bugüne kadarki bütün kanıtı tek yerde topluyor: ana kuralın hangi parçası sağlam, hangisi kırılgan, ne denendi, ne kazandı.

Yeni test yok. Sadece mevcut sonuçlar (docs/journal.md, docs/trials.csv). **Çalışan botun ayarı değişmedi.**

## 1. Ana kural bugün (TrendEmaVolTarget)

| Parça | Ayar | Ne işe yarıyor |
|---|---|---|
| Giriş | EMA20, EMA50'yi yukarı keser **ve** kapanış > EMA200 | kısa yön döndü, büyük resim yukarı |
| Çıkış | EMA20, EMA50'yi aşağı keser | kısa yön bitti |
| Stop | -%8 | tek işlemde büyük kaybı keser |
| Boyut | işlem başına %1 risk, oynaklık hedefi %60 (30 günlük) | oynak coinde daha küçük alım |
| Korumalar | en fazla 3 açık işlem, 2 saat bekleme, 24 saatte 3 stop → 12 saat dur, kill switch %20 | risk kitabı R1-R13 |

Geçmiş (kill switch kapalı, komisyon %0,15): train 2021-24 Calmar **1,86**, validation 2024-25 **1,93**, 2018-20 **2,46**, yeni coinler 2024-25 **-0,46**. Son sınav (2025-08 → 2026-10): **-%19,9, kill switch çalıştı, KALDI.**

## 2. Hangi parça sağlam, hangisi kırılgan? (T115 ayar haritası)

Her ayar bugünkü değerin iki yanında denendi (train 2021-24). Calmar:

| Ayar | Düşük | **Bugünkü** | Yüksek | Yorum |
|---|---|---|---|---|
| Trend filtresi | EMA150: 1,22 | **EMA200: 1,86** | EMA250: 1,91 | sağlam (200-250 düz) |
| Stop | %6: 1,95 | **%8: 1,86** | %10: 1,86 | sağlam |
| Oynaklık hedefi | %50: 1,76 | **%60: 1,86** | %70: 2,01 | sağlam |
| Oynaklık penceresi | 20 gün: 1,63 | **30 gün: 1,86** | 45 gün: 1,73 | sağlam |
| EMA çifti (hızlı/yavaş) | 0,67 ile 1,88 arası | **20/50: 1,86** | | **KIRILGAN** |

Hızlı × yavaş EMA ızgarası (train Calmar):

| hızlı \ yavaş | 40 | 50 | 60 |
|---|---|---|---|
| 15 | 1,36 | 0,67 | 1,15 |
| 20 | 0,98 | **1,86** | 1,57 |
| 25 | 1,48 | 1,88 | 1,07 |

**En önemli bulgu:** EMA 20/50 düz bir "plato" üzerinde değil, engebeli bir yüzeyde yerel bir tepe. Komşu çiftler 0,67'ye kadar düşüyor. Yani geçmişteki iyi sonucun bir kısmı bu çiftin şansı olabilir. Bu, son sınavdaki düşüşle de uyumlu.

İkinci kontrol (walkforward, train içinde): "son 12 ayın en iyi ayarını seç, sonraki 6 ay kullan" Calmar **0,50**; "bugünkü ayarı hiç değiştirme" **0,92**. **Ayarları sık sık yeniden seçmek geleceği iyileştirmiyor, kötüleştiriyor.**

## 3. Bu gece denenenler (2026-11-01/02, hepsi önceden yazılı)

Ölçüt (T110+): eski 5 coin (train) en az %90'ı, yeni coinlerde daha iyi ve düşüş daha büyük değil, 2018-20'de en az %90'ı, 2024-25'te en az aynı. Sonra sağlamlık: komşu ayarlar + 2 kat komisyon.

| # | Fikir | Sonuç | Neden |
|---|---|---|---|
| T113 | Her zararı sayan kayıp freni | KALDI | 2020'de büyük trendin başını kaçırdı |
| T114 | Hacim onaylı giriş | KALDI (yeni coinler) | düşüşü her yerde azalttı → taze veride izleniyor (F007) |
| T115 | Ayar haritası | değişiklik yok | bugünkü ayarlar korunur (yukarıda) |
| T132 | 9 EMA çiftinin oylaması | dört sınavı GEÇTİ, sağlamlıkta KALDI | kırılganlık EMA'dan oy eşiğine taşındı → F008 |
| T135 | Kârdan sonra iz süren çıkış (chandelier) | çok kötü | kazananları erken kesiyor (tasarım hatası: günlük ayar saatlikte) |
| T136 | Kazananı uzun tut (+%8 sonrası EMA100) | KALDI (yeni coinler) | eski coinlerde iyi, yenilerde kötü → F009 |
| T139 | Aynı anda 5 işlem (risk sayısı) | KALDI | düşüş getiriden hızlı arttı; kural 3'te kalır |
| T140/141 | ADX20 adayının komşuları | plato YOK | ADX20'nin yeni coin başarısı tek nokta |
| analiz | zaman bazlı çıkış, stoptan sonra yeniden giriş | deneme gereksiz | train analizi kazanç olmayacağını gösterdi |

## 4. Bütün denemelerin özeti

`docs/trials.csv`: 141 satır. GEÇTİ 4, KALDI 57, İZLEMEDE 4, ELENDİ 9, KOMŞU (sağlamlık ölçümü) 66, ünlü bot kıyası 1. Deflated Sharpe için N = 140.

Aileler ve genel sonuç:

| Aile | Denenenler (örnek) | Genel sonuç |
|---|---|---|
| Giriş filtresi | ADX, momentum, hacim, korelasyon, komisyon, genişlik, BTC rejimi, geri çekilme | bazıları yeni coinlerde iyi, eski coinlerde kötü; hiçbiri her yerde sağlam değil |
| Çıkış | ATR iz, chandelier, başabaş stop, yarım kâr al, en az tutma, uzun tutma, EMA50 altı | kazananı erken kesen her şey zarar; uzun tutmak yeni coinlerde zarar |
| Boyut ve risk | oynaklık hedefi, yarım satış, 5 yuva, %2 risk | oynaklık hedefi kalıcı kazanç (VolTarget); diğerleri değil |
| Ayar | EMA çiftleri, trend, stop, hedef, pencere, oylama | EMA çifti kırılgan, diğerleri sağlam |
| Zaman dilimi | 2 saat, 4 saat, günlük | 1 saat kadar iyi değil |

## 5. Bugünkü durum ve öneri

1. **Ana kural değişmesin: TrendEmaVolTarget aynen.** Bu gece hiçbir değişiklik sağlamlık kontrolünü geçemedi. Ayarları geçmişe göre yeniden seçmenin geleceği kötüleştirdiği de ölçüldü.
2. **Bilinen zayıflık: EMA 20/50 seçimi kırılgan.** Bunu düzeltmeye çalışan oylama da kırılganlığı başka yere taşıdı. Fiyattan başka bilgi (hacim, duygu, haber) eklenmeden bu kuralın daha fazla "optimize" edilmesi, geçmişi ezberlemek demek olur.
3. **ADX20 paralel botta yargı için çalışmaya devam ediyor**, ama "VolTarget'tan daha iyi" kanıtı sanıldığından zayıf (komşuları yeni coinlerde kaybediyor).
4. **Taze veride izlenen 9 fikir var (F001-F009).** Her biri 6 ay (bazıları 1 yıl) sonra, sadece yeni fiyatlarla, önceden kilitlenmiş ölçütle yargılanacak. Bugün değiştirilemezler.
5. **8 Kasım'da gerçekçi beklenti:** 1 haftada botlar çok az işlem yapar (şu an 5 coinin hepsi EMA200 altında, sinyal yok). 1 haftalık canlı veriyle "hangisi daha iyi" kararı verilemez; istatistik için en az 50 kapanmış işlem gerekir.

## 6. Sıradaki adım (Kaan'ın yol haritası, 2. basamak)

**8 Kasım'a kadar sadece fiyat.** Sıradaki denemeler doğrudan kırılganlığa yönelik:
1. Sürekli oy ile boyut: eşik yok; işlem boyutu = VolTarget boyutu × "yukarıda olan EMA çiftlerinin payı". Oylamadaki eşik kırılganlığını hedefler.
2. Giriş onayı: EMA20 > EMA50 iki mum üst üste.
3. Daha büyük zaman diliminden trend filtresi: 1 saatlik EMA200 yerine 4 saatlik EMA50 (yaklaşık aynı süre), komşularıyla.

Her biri önce `trials.py --find` ile kontrol, sonra ön kayıt, sonra aynı ölçüt; geçerse komşular + 2 kat komisyon.

**8 Kasım'dan sonra (yol haritası 2. basamak):** hacim, sonra duygu (Fear & Greed, sadece bir önceki günün değeri), sonra haber. Bilinen tuzak: yeni listelenen coinlerde (alt2024b) her fikir ayrıca sınanır, çünkü bu gece iki fikir sadece orada kaldı.

## Anlaman gerekenler

- **Tek bir iyi sayı, iyi bir kural demek değildir.** Ayarın iki yanı da iyiyse ("plato") güvenilir; sadece kendisi iyiyse şans olabilir. Bu gece üç kez gördük: EMA 20/50, oy eşiği 5/3, ADX 20.
- **En iyi ayarı sürekli yeniden seçmek, sabit kalmaktan kötü çıktı.** Geçmişin en iyisi, geleceğin en iyisi değil.
- **"Değişiklik yok" da bir sonuçtur.** Bir sistemi geliştirmenin bir parçası, neyin değiştirilmemesi gerektiğini kanıtla bilmektir.

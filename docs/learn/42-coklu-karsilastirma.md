# Kart 42: Çoklu karşılaştırma (13 yazı tura)

## Benzetme

13 kişi birer kez yazı tura atsın. Yazı atan "kazandı" sayılsın. En az birinin yazı atma ihtimali:

`1 - (1/2)^13 = %99,99`

Yazı atan kişi usta mı? Hayır. Çok kişi denediği için biri mutlaka kazanır.

Bizde de 13 F satırı var. Her biri aynı botla yarışıyor. Hiçbiri gerçekten iyi olmasa bile, bazıları şansla geçebilir. Şans payının gerçekte kaç olduğunu bilmiyoruz, ama satır sayısı arttıkça şansla geçen satır sayısının da artacağını biliyoruz.

## Neyi değiştirmedik?

Kilitli şartlara ve hash'lere dokunmadık. Yeni kısım onların üstünde bir katman. Çünkü yazıldıktan sonra şart değiştirmek zaten yasak.

## İki aşama

| Durum | Anlamı |
|---|---|
| PASS → **ADAY** | Hüküm gününde geçti. Henüz kanıt değil |
| ADAY → 6 ay daha, **tek başına** aynı şartla | Pencere: `[judge, judge + 6 ay)`. Bu fiyatlar ilk hükümde yoktu |
| Yine geçti → **DOĞRULANDI** | İki ayrı dönemde geçti |
| Geçemedi → **ELENDİ** | Büyük ihtimalle şanstı |

Benzetmeyle: 13 kişiden yazı atanlar bir kez daha atar. Şansla iki kez üst üste kazanmak çok daha zordur, ama imkânsız değildir: yazı turada bir kişi için ihtimal %25. Yani DOĞRULANDI "kesin iyi" demek değil, "şansla açıklaması çok daha zor" demektir.

Durum dosyalardan hesaplanır (`prereg.stage`): `prereg-results.csv` ve `prereg-confirm.csv`. Kilitli alanlar hiç değişmez.

## p-değeri ve Holm

**Block bootstrap (bloklu yeniden örnekleme):** Satırın ve ana botun günlük getirilerini alır, 7 günlük bloklar halinde 2000 kez yeniden çeker ve kaçında satırın ana botu kilitli şartla geçemediğini sayar (Calmar yüksek VE düşüş daha büyük değil). İkisi için aynı günler çekilir, böylece piyasa şansı ikisine de aynı etki eder.

- Girdi: iki günlük getiri dizisi.
- Çıktı: p, geçemediği çekilişlerin payı. Düşük p = üstünlük dönem boyunca istikrarlı. Yüksek p = üstünlüğü birkaç gün yapmış.

**Holm düzeltmesi:** Çok satır varsa p'leri düzeltir. En küçük p'yi satır sayısıyla çarpar, sonrakini bir eksiğiyle, böyle gider. Sonuç geriye doğru küçülmez ve 1'i geçmez. Örnek: 0,01 / 0,03 / 0,04 → 0,03 / 0,06 / 0,06.

Bu ikisi **sadece bilgi**. Hükmü değiştirmez.

Sınır: 6 aylık kısa pencerede p kaba bir ölçüdür.

## Test bize bir şey öğretti

İlk sürüm p'yi sadece Calmar'la hesaplıyordu. Her gün %1 daha kötü olan aday "daha iyi" çıktı. Neden? Negatif getiride düşüş büyüdükçe Calmar sıfıra yaklaşır: -%97 / %80 = -1,2, ama -%60 / %25 = -2,4. Yani **negatif Calmar'da büyük olan her zaman iyi değildir.** Kilitli şartın düşüşe de bakması bu yüzden önemli.

## Akış

hüküm günü → backtest → `prereg_eval.py` (Calmar, düşüş, p) → `prereg.record` (PASS/FAIL) → rapor: "Aynı anda N satır yargılandı…" → ADAY ise 6 ay sonra `daily.py` otomatik olarak tek başına yeniden yargılar.

Burada N, ilk hükmü verilmiş bütün satırlar. Tarihleri birkaç gün ya da ay farklı olsa da hepsi aynı fikir ailesi.

## Anlaman gerekenler

- **Çok denersen şans da çok denemiş olur.** Tek başına "bir satır geçti" zayıf kanıttır.
- **Yeni veri en güçlü düzeltmedir.** İkinci aşama sayıları düzeltmez, şansa yeni bir sınav yaptırır.
- **Bilgi ile karar ayrı tutulur.** Holm sadece bilgi olduğu için, onu sonradan bahane edip hükmü değiştiremeyiz.

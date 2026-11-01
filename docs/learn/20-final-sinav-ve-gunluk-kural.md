# 20. Final sınavı ve günlük kurala geçiş

## Final sınavında ne oldu?

Veriyi en başta üçe ayırmıştık:

| Dilim | Dönem | Ne için |
|---|---|---|
| Train | 2021 - Haziran 2024 | Kural geliştirmek |
| Validation | Haziran 2024 - Ağustos 2025 | Kuralı seçmek |
| Test | Ağustos 2025 - Ekim 2026 | Final sınavı, her kural için bir kez |

TrendEmaPyramidBtc train ve validation'ı geçti. Final sınavında ise sonuç şöyle oldu:

- TrendEma ve PyramidBtc ikisi de yaklaşık **-%20** kaybetti ve kill switch'e çarptı.
- Al-tut -%27 kaybetti, yol boyunca %64 düştü.
- Önceki dönemlerde 1 dolarlık kayba karşı 1,6-1,9 dolar kazanıyorlardı. Final döneminde **0,3 dolar** kazandılar.

## Neden böyle oldu? (overfitting / aşırı uydurma)

Okul benzetmesi: Aynı deneme sınavını 30 kez çözüp her seferinde yöntemini biraz değiştirirsen, o deneme sınavında çok iyi olursun. Ama gerçek sınavda soruların farklı olduğunu görürsün.

Biz de bunu yaptık:

- Train'de 30'dan fazla deneme yaptık.
- Validation'a 4 kez baktık. Pyramid'in kıl payı kaldığını görünce bir değişiklik ekledik ve tekrar baktık.
- Validation'ı her kullanışımızda kural o döneme biraz daha uydu.

Final sınavı tam olarak bunu yakalamak için vardı. Görevini yaptı.

## Doğru giden şeyler

- **Kill switch kaybı sınırladı.** Botun kaybı %20'de kaldı, piyasa %64 düştü.
- **Kurallara sadık kaldık.** Test sonucuna bakıp kuralı ayarlamadık. Bunu yapsaydık son bağımsız kontrolümüzü de bozmuş olurduk.

## Yeni yön: günlük kural (TrendSmaDaily)

Kural çok basit:

- Günlük kapanış fiyatı, son **200 günün ortalamasının** üstündeyse coini al ve tut.
- Altına inerse sat.

**Kaynak:** Mebane Faber, 2007. Basit trend kurallarının en çok alıntılananı. Sayı (200 gün) kitaptaki sayı. Ayarlanmadı, bundan sonra da ayarlanmayacak.

**Neden günlük grafik?** Saatlik grafikte çok sayıda sahte kırılım oluyordu. Final dönemindeki kazanma oranı %8-19'du. Günlük grafikte sinyal az ve yavaş gelir.

**Risk kuralları aynı kalıyor:** -%8 stop, işlem başına %1 risk, en fazla 3 açık işlem, kill switch.

## Dürüstlük notu

Final döneminin düşen bir piyasa olduğunu artık biliyoruz. "Düşüşte nakde geç" diyen bir kuralı şimdi seçmek, bu bilgiden etkilenmiş olabilir.

Bu yüzden:

- Bu kuralın final sınavı **ileriye dönük** yapılacak: önümüzdeki haftalarda sahte parayla çalışacak.
- Geçmiş verideki test dilimi bu kural için de yalnızca bir kez kullanılabilir.

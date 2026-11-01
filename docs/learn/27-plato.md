# Öğretici kart 27: Plato nedir, neden önemli?

## Fikir

Bir kuralda sayılar var: 20 saatlik ortalama, 50 saatlik ortalama, -%8 stop... Bu sayıları geçmiş veride en iyi sonucu verecek şekilde seçersek, kural geçmişi **ezberlemiş** olabilir.

Bunu anlamanın yolu **komşulara bakmak**. Her sayıyı biraz oynatıp (20 yerine 15 ve 25 gibi) sonuca bakıyoruz:

- **Plato (düzlük):** Komşular da temele yakın sonuç veriyor. Sayının tam değeri önemli değil, kuralın kendisi çalışıyor. İyi işaret.
- **Sivri tepe:** Sadece seçilen sayı iyi, komşular çöküyor. Büyük ihtimalle şans. Kötü işaret.

Bir dağı düşün: Zirve geniş bir yayla ise biraz kaysan da yüksekte kalırsın. Zirve iğne gibi ise bir adım kayınca aşağı düşersin. Gerçek piyasa her zaman geçmişten biraz farklıdır, yani her zaman "biraz kayarız".

## VolTarget'in sonucu (2021 – 2024/06, 5 coin)

| Sayı | Küçük komşu | Temel | Büyük komşu |
|---|---|---|---|
| Kısa ortalama (20) | 15: 0,67 | 1,86 | 25: 1,88 |
| Orta ortalama (50) | 40: 0,98 | 1,86 | 60: 1,57 |
| Uzun ortalama (200) | 150: 1,22 | 1,86 | 250: 1,91 |
| Stop (-%8) | -%6: 1,95 | 1,86 | -%10: 1,86 |
| Oynaklık penceresi (30 gün) | 20 gün: 1,63 | 1,86 | 40 gün: 1,81 |

(Sayı = Calmar: yıllık getiri / en büyük düşüş; yüksek iyi.)

## Ne öğrendik?

- **Stop ve oynaklık penceresi sağlam:** oynatınca sonuç pek değişmiyor.
- **Ortalamaları kısaltmak kırılgan:** 15/40/150 gibi daha hızlı ayarlarda bot çok daha sık al-sat yapıyor, yalancı sinyaller ("testere") artıyor, sonuç çöküyor.
- **Uzatmak (25/250) zarar vermiyor.**

Bu yüzden kuralı değiştirmiyoruz. Ama "hızlandırma" yönündeki her fikre şüpheyle bakacağız.

## Anlaman gerekenler

- En iyi sayıyı bulmak kolay; asıl soru o sayının **etrafının** da iyi olup olmadığı.
- Kırılgan bir yön bulmak da değerli bilgi: kuralın nerede bozulacağını önceden biliyoruz.
- Bu kontrol sadece eğitim verisinde yapıldı; kontrol verisine (validation) bakılmadı, yani yeni bir "deneme" sayılmıyor, sadece sağlamlık ölçümü.

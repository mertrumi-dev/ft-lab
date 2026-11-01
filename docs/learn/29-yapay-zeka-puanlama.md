# Öğretici kart 29: Yapay zeka yorumlarının puanlanması (`ft.py ai-score`)

## Neden?

Her gün 5 coin için yapay zeka bir grafik yorumu yazıyor ve 7 gün sonrası için bir yön tahmin ediyor: yukarı, aşağı ya da yatay. Bir yorum ne kadar akıllıca görünürse görünsün, **işe yarayıp yaramadığını ancak sonuçlara bakarak** anlarız. Bu araç her tahmini 7 gün sonra otomatik puanlar.

## Kurallar (yorumlardan önce yazıldı, değiştirilmez)

- Tahmin: 7 gün sonraki günlük kapanış, yorumun dayandığı kapanışa göre.
- "Yatay" = %2'den az hareket (±%2).
- Kıyaslar:
  - **Yazı-tura:** üç seçenek olduğu için rastgele tahmin %33 tutar.
  - **"Hep yukarı":** her gün "yukarı" deseydik kaç tutardı?
- Yapay zeka ancak **50'den fazla** puanlanmış tahminde ikisini de geçerse bota bağlanmayı düşünürüz.

## Ne üretir?

- `docs/fresh/ai-scores.csv`: her tahmin için gerçekleşen hareket, sonuç ve isabet (1/0). Her çalıştırmada baştan yazılır; aynı gün iki kez çalışsa da aynı dosya çıkar.
- Günlük raporun 6. bölümünde tek satır: kaç tahmin puanlandı, isabet oranı, yazı-tura ve "hep yukarı" ile kıyas, **p değeri**.

## p değeri ne?

"Bu kadar isabeti şansla tutturma ihtimali." Mesela 50 tahminde 25 isabet: şansla (%33) bu kadar tutturmak zor, p küçük çıkar. p < 0,05 genelde "muhtemelen şans değil" demek. Az tahminde p büyük olur; bu yüzden 50'den fazla tahmin bekliyoruz.

## Kod

- `parse_views`: yorum tablosundan tarih, coin, kapanış, tahmin ve güveni okur.
- `classify`: gerçek hareketi yukarı/aşağı/yatay olarak sınıflar (±%2).
- `score`: 7 günü dolan her tahmini günlük kapanışla karşılaştırır.
- `binom_p_at_least`: binom dağılımıyla "en az bu kadar isabet" ihtimali.

## Anlaman gerekenler

- **Kuralı önce yaz, sonra ölç:** Puanlama kuralını tahminlerden önce sabitledik. Sonradan "aslında %3 yatay sayılsın" demek kendini kandırmak olur.
- **Az örnekle karar verilmez:** İlk haftanın 5 tahmini hiçbir şey kanıtlamaz.
- **Kıyas noktası şart:** %40 isabet iyi mi? "Hep yukarı" %55 tutuyorsa değil.

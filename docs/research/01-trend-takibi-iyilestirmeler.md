# Araştırma 01: Trend takibini profesyoneller nasıl yapıyor? (2026-10-31)

Soru: Başarılı trend takipçilerinin kurallarından TrendEma'ya ne alabiliriz?

**Önemli:** Bunlar "denenecekler listesi", hiçbiri henüz bota eklenmedi. Her biri Faz 2'de geçmiş veride (sadece ayarlama diliminde) mevcut kuralla yan yana ölçülecek. İşe yararsa kalır, yaramazsa atılır.

## Kime baktık?

"Dünyanın en iyi traderları"nın çoğu kendi kafasıyla (sezgiyle) işlem yapar; bunu bota kopyalamak mümkün değil. Kurallarını açıkça yazmış ve sonuçları ölçülmüş olanlar **sistematik trend takipçileri**:

- **Turtle Traders (1983-88):** Richard Dennis'in "trading öğretilebilir mi" deneyi. Sıfırdan eğitilen kişilere tamamen yazılı kurallar verdi. Kurallar sonradan yayımlandı ve bugün trend takibinin ders kitabı sayılıyor.
- **Trend takip fonları (CTA'lar):** Onlarca yıldır bu mantıkla çalışan profesyonel fonlar. Ortak noktaları: basit giriş kuralı, oynaklığa göre pozisyon ve stop, çok sıkı risk yönetimi.
- **Kripto çalışmaları:** Kriptoda "yükselen bir süre daha yükselir" etkisini ölçen akademik ve kurumsal çalışmalar.

## Öğrendiklerimiz ve bota uyarlanabilecekler

### 1. Stop'u oynaklığa göre ayarla (en önemli aday)

Şu an: her coinde sabit -%8.

Profesyoneller: Turtle'lar stop'u "N" denen oynaklık ölçüsüyle koyardı (N = ATR: bir mumun ortalama ne kadar oynadığı). Stop = giriş fiyatı − 2N. Sakin coinde dar, oynak coinde geniş stop.

Kanıt: Kripto üzerine 2026 tarihli bir çalışmada ATR'ye göre takip eden (fiyat yükseldikçe yukarı çekilen) stop çıkarıldığında sonuç belirgin kötüleşmiş: en büyük düşüş -%12,7'den -%22,4'e çıkmış.[^1]

Denenecek: Sabit -%8 yerine "giriş − 2×ATR" ve 2,5× / 3× varyasyonları.

### 2. Pozisyon büyüklüğünü de oynaklığa göre ayarla

Şu an: "%1 risk / %8 stop" → her coinde aynı büyüklük.

Profesyoneller: Turtle'lar her işlemde sermayenin %1'ini riske atar, büyüklüğü N'e göre hesaplardı. Oynak coinde küçük, sakin coinde büyük pozisyon; sonuçta her işlemin riski eşit.

Bizim avantajımız: Kodumuz zaten "%1 risk / stop mesafesi" formülüyle çalışıyor. Stop ATR'ye göre olursa pozisyon da otomatik oynaklığa göre ayarlanır. Ek kural gerekmez.

Kanıt: Aynı çalışmada oynaklığa göre ölçeklenen basit trend takibi, ölçeklenmeyen versiyona göre çok daha iyi risk-ayarlı sonuç vermiş (Sharpe 1,83'e karşı 0,65; en büyük düşüş -%16'ya karşı -%35).[^1]

### 3. Kazananı koştur: takip eden stop ile çık

Şu an: EMA20, EMA50'yi aşağı kesince çık.

Profesyoneller: Turtle'lar kısa vadeli dibin kırılmasıyla (ör. son 10-20 günün en düşüğü) ya da takip eden stop ile çıkardı. Fikir: trend sürdükçe stop da yukarı çıksın, kazanç kilitlensin.

Denenecek: EMA kesişimiyle çıkış vs ATR takip eden stop ile çıkış.

### 4. Alternatif giriş: kırılım (breakout)

Şu an: EMA kesişimi.

Profesyoneller: Turtle'ların girişi "fiyat son 20 (ya da 55) mumun en yükseğini geçerse al" idi (Donchian kanalı). EMA kesişimine benzer bir fikir, farklı bir ölçüm.

Denenecek: Aynı risk kurallarıyla "kırılım" girişini EMA girişiyle kıyaslamak. Hangisi daha az yalancı sinyal veriyor, veri söyleyecek.

### 5. Komisyon her şeyi yiyebilir: az işlem yap

Kanıt: Aynı çalışmada işlem başına maliyet 0'dan %0,12'ye çıkınca Sharpe 2,87'den 1,62'ye düşmüş.[^1] Bizim varsaydığımız maliyet daha da yüksek (%0,15).

Denenecek: 1 saatlik yerine 4 saatlik mum. Daha az işlem, daha az komisyon, daha az yalancı sinyal. Bedeli: trende daha geç girmek.

### 6. Coinler birlikte hareket ediyor

BTC, ETH, SOL, BNB, XRP genelde aynı yöne gider. Profesyoneller birbirine bağlı piyasaları tek bir pozisyon gibi sayar ve toplam riski sınırlar. Turtle'larda da "çok bağlı piyasalarda toplam risk tavanı" kuralı vardı.

Denenecek (Faz 3): "aynı anda en fazla 3 işlem" yerine "birbirine bağlı coinlerde toplam risk en fazla %2".

## Neye güvenmemeliyiz?

- Çalışma [^1] hakem kontrolünden geçmemiş bir ön yayın (arXiv). Tablosundaki bazı sayılar kendi içinde tutmuyor. Yön (ATR stop ve oynaklık ölçekleme işe yarıyor) başka kaynaklarla uyumlu, ama "Sharpe 2,4" gibi sayılara güvenmiyoruz. Ayrıca kaldıraçlı (futures) işlem ve short kullanıyor; bizim kurallarımıza birebir uymaz.
- Coinbase'in 2022 notu [^2] trend takibinin 2021-22'de al-tut'tan iyi olduğunu söylüyor, ama komisyonu hesaba katmamış ve sadece 20 ay. Aynı notta trend takibi son 7 çeyreğin 5'inde al-tut'un gerisinde kalmış.
- 2021 tarihli akademik çalışma [^3] kriptoda momentum stratejisinin al-tut'tan iyi risk-ayarlı getiri verdiğini söylüyor; tam metnine erişemedik, sadece özetini okuduk.
- Turtle kuralları 1980'lerin vadeli işlem piyasaları için yazıldı. Kripto 7/24 açık ve çok daha oynak; birebir çalışacağını varsaymıyoruz.

## Sıra (Faz 2'de)

1. Mevcut TrendEma'yı ölç (temel çizgi).
2. Tek tek değiştir ve her seferinde yalnızca bir şeyi değiştir: ATR stop (1) → takip eden stop çıkışı (3) → 4h mum (5) → kırılım girişi (4).
3. Her değişiklik: ayarlama diliminde daha iyi mi, kontrol diliminde de tutuyor mu? Test dilimine dokunulmaz.
4. Deneme sayısı `docs/journal.md`'de sayılır.

## Kaynaklar

[^1]: Bui, D. & Nguyen, T. (2026). *Systematic Trend-Following with Adaptive Portfolio Construction: Enhancing Risk-Adjusted Alpha in Cryptocurrency Markets.* arXiv:2602.11708. https://arxiv.org/html/2602.11708v1
[^2]: Duong, D. (2022). *Trend following in uncertain times.* Coinbase Institutional. https://www.coinbase.com/institutional/research-insights/research/monthly-outlook/trend-following-in-uncertain-times-september-2022
[^3]: Borgards, O. (2021). *Dynamic time series momentum of cryptocurrencies.* North American Journal of Economics and Finance, 57. https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000590

Turtle kuralları için genel kaynak: Curtis Faith, *Way of the Turtle* (2007) ve yayımlanmış "Original Turtle Trading Rules" belgesi.

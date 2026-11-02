# Araştırma 13: Haber, sosyal medya ve temel veri kaynakları (2026-11-02)

Neden: Kaan'ın yol haritasında fiyattan sonra sırayla hacim, duygu, haber ve "şirket bilgisi" (coin temel verisi) var. Hacim (T114/T143/T144) ve duygu (T145/T146) denendi. Bu belge sadece **haber, sosyal ve temel veri** için hangi kaynağın dürüstçe test edilebileceğini araştırıyor.

**Deneme yok, anahtar yok.** Hiçbir hesap açılmadı, hiçbir anahtar istenmedi. Ücretsiz bir anahtar gerektiren kaynaklar "Kaan karar verirse" diye işaretlendi.

## Neye bakıyoruz?

Bir kaynağın backtest'te kullanılabilmesi için dört şart:

1. **Geçmiş uzunluğu:** train (2021-24), validation (2024-25) ve early (2018-20) dilimlerini kapsamalı. Kapsamıyorsa sadece ileriye dönük (forward) toplanabilir.
2. **Anahtar:** anahtarsız mı? Anahtar isteyen her kaynak Kaan'ın kararı.
3. **Geleceği görme riski (lookahead):** veri, o anda gerçekten biliniyor muydu? Haber sonradan dizine eklenir, revize edilir; "o günün sayısı" o gün yayınlanmamış olabilir.
4. **Kullanım şartları:** ücretsiz kullanım ve atıf koşulları.

## Kaynaklar

| Kaynak | Ne verir | Geçmiş | Anahtar | Geleceği görme riski | Sonuç |
|---|---|---|---|---|---|
| **GDELT DOC 2.0** (timeline modları) | Bir aramayla ("bitcoin") eşleşen haber hacmi (tüm haberlerin yüzdesi) ve ortalama ton, zaman serisi | Timeline modları **2017-01-01'den bugüne** (resmi blog). Makale listesi modları sadece son 3 ay | Yok | Orta: haberler dizine gecikmeyle girer. Bir önceki günün değeri kullanılırsa düşük | **Test edilebilir** (train, validation; early 2018-20 için kısmen) |
| **Wikipedia sayfa görüntülemeleri** (Wikimedia REST API) | "Bitcoin", "Ethereum" vb. makalelerin günlük okunma sayısı: ilgi göstergesi | **2015-07'den bugüne**, günlük | Yok (tanıtıcı User-Agent isteniyor) | Düşük: bir önceki günün sayısı kullanılır | **Test edilebilir** (bütün dilimler) |
| **Fear & Greed** (alternative.me) | Günlük 0-100 duygu endeksi | 2018-02'den bugüne | Yok | Düşük (önceki gün) | Zaten kullanıldı (T021, T145, T146) |
| **CryptoPanic** | Kripto haber akışı + oy bazlı duygu | Ücretsiz plan **gerçek zamanlı**, arşiv yok (resmi sayfa) | Ücretsiz hesap ve token gerekli | — | **Sadece ileriye dönük.** Anahtar gerektiği için Kaan'ın kararı |
| **Santiment** (sosyal hacim vb.) | Sosyal medyada bahsedilme, duygu, zincir üstü ölçüler | Ücretsiz katman: **1 yıl, son 30 gün hariç** (resmi Academy) | Ücretsiz hesap ve anahtar | Düşük ama 30 gün gecikme | Backtest için yetersiz (train/validation/early'yi kapsamıyor) |
| **CoinGecko Demo** (piyasa değeri geçmişi) | Piyasa değeri, hacim | **Son 365 gün**; saatlik sadece son 100 gün (resmi doküman) | Ücretsiz demo anahtarı | Düşük | Backtest için yetersiz |
| **Google Trends** | Arama ilgisi | Uzun | Resmi API sadece onaylı test kullanıcılarına (alfa, 2025); gayriresmi pytrends 2025'te arşivlendi, 429 hatası veriyor | Orta (veri ölçekleniyor, sonradan değişebiliyor) | **Güvenilir değil**, atlandı |
| **Token kilit açılımları** (DefiLlama emissions) | Gelecekteki arz açılım takvimi | Ücretsiz kamu verisi (aracılar üzerinden); geçmiş takvimlerin revize edilmiş olma riski | Ücretsiz uç yok gibi; Pro API ücretli | **Yüksek**: bugünkü takvim geçmişte bilinenle aynı olmayabilir | Ana 5 coin için önemi düşük (BTC'de kilit yok). Ertelendi |

## Öneri

1. **Haber için tek aday: GDELT timeline** ("bitcoin" ve "cryptocurrency" haber hacmi ve tonu, bir önceki günün değeri). Train ve validation'ı kapsıyor, anahtar yok. early (2018-20) 2017'den başladığı için kapsanıyor.
2. **Sosyal ilgi için tek aday: Wikipedia sayfa görüntülemeleri.** 2015'ten beri, günlük, anahtarsız. Google Trends'in yerine geçebilecek temiz bir ilgi ölçüsü.
3. **Sadece ileriye dönük:** CryptoPanic (arşiv yok). Anahtar gerektirdiği için Kaan karar verirse ileride.
4. **Atla:** Santiment ve CoinGecko ücretsiz katmanları (geçmiş çok kısa), Google Trends (güvenilir erişim yok), token kilitleri (ana coinlerde önemi düşük, geçmiş takvim revizyon riski).

**Uyarı:** Duygu ve ilgi verilerinin önemli bir kısmı zaten fiyattan türetiliyor (Fear & Greed'in yarısı oynaklık ve momentum). Fiyat kuralına eklenen bilgi, fiyatın zaten söylediğini tekrar ediyor olabilir. Her deneme yine önceden yazılı, aynı ölçütle ve `ft.py trial` ile.

**Sıra (8 Kasım sonrası, koordinatör onaylarsa):** veriyi indiren stdlib bir script (sentiment.py gibi, `user_data/data/` altına, gitignore'da) + testi; sonra her kaynaktan tek bir ön kayıtlı fikir.

## Doğrulanamayanlar (açıkça)

- GDELT'in güncel resmi API sayfasını doğrudan okumadım; 2017 başlangıcı GDELT'in kendi blog yazısından. Üçüncü taraf kaynaklar hâlâ "3 ay" diyor (eski sınır ya da makale modları için).
- Wikimedia sayfa görüntüleme verisinin lisans ayrıntısını resmi sayfadan teyit etmedim; kullanmadan önce kontrol edilmeli.
- DefiLlama'nın ücretsiz API'sinde kilit takvimi uç noktası olup olmadığı net değil (fiyat sayfaları çelişkili).

## Kaynaklar

- GDELT, DOC 2.0 güncellemesi (2017'den arama, timeline modları): https://blog.gdeltproject.org/doc-2-0-updates-1-5-year-searching-and-updated-mobile-interface/
- GDELT DOC 2.0 tanıtımı: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- gdeltdoc (Python istemcisi, timelinevol/timelinetone): https://pypi.org/project/gdeltdoc/
- CryptoPanic API hakkında (ücretsiz plan, gerçek zamanlı): https://cryptopanic.com/developers/api/about
- Santiment, geçmiş ve gerçek zamanlı veri kısıtları: https://academy.santiment.net/sanapi/historical-and-realtime-data-restrictions/
- Santiment API planları: https://academy.santiment.net/products-and-plans/sanapi-plans
- CoinGecko Demo, market_chart (365 gün): https://docs.coingecko.com/demo/reference/coins-id-market-chart
- CoinGecko Demo, market_chart/range: https://docs.coingecko.com/demo/reference/coins-id-market-chart-range
- pytrends arşivlendi / 429 sorunu: https://dev.to/rimulabs/pytrends-is-archived-how-to-migrate-your-google-trends-code-no-more-429s-4e63
- Tokenomist CSV dışa aktarma (geçmiş plana bağlı): https://docs.tokenomist.ai/api-documents/csv-export
- DefiLlama Pro API: https://docs.llama.fi/pro-api
- Wikipedia sayfa görüntüleme istemcisi (uç nokta örneği): https://pypi.python.org/pypi/pageviewapi

## Anlaman gerekenler

- **Backtest'te kullanılan her veri, o anda gerçekten bilinmeli.** Bu yüzden hep "bir önceki günün değeri" kullanılıyor; aynı günün sayısı o an yayınlanmamış olabilir.
- **"Ücretsiz" her zaman "geçmişi var" demek değil.** Çoğu ücretsiz katman sadece son 1 yılı ya da sadece bugünü veriyor; geçmişle sınanamayan bir kaynak sadece ileriye dönük toplanabilir.
- **Yeni bilgi gerçekten yeni mi?** Birçok duygu endeksi fiyattan türetilir. Fiyat kuralına eklenince aynı şeyi iki kez saymış olabiliriz.

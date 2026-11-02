# Araştırma 14: Coin temel ve zincir üstü verisi (2026-11-02)

Neden: Kaan'ın yol haritasının son basamağı "şirket bilgisi", yani coinin kendi verisi: piyasa değeri, arz, ağ kullanımı, borsalara giriş-çıkış, kilit açılımları. Bu belge, ana 5 coin (BTC, ETH, SOL, BNB, XRP) için hangi kaynağın dürüstçe test edilebileceğini araştırıyor.

**Deneme yok, anahtar yok.** Kontrol için birkaç anahtarsız istek atıldı (Coin Metrics Community API, kendi limitinin çok altında). Hiçbir hesap açılmadı.

## Ölçütler

Araştırma 13 ile aynı: geçmiş uzunluğu, anahtar, lisans, **geleceği görme ve sonradan değişme (revizyon) riski**, 5 coinin hepsine uygulanıyor mu.

Revizyon zincir üstü veride özellikle önemli. Örnek: borsaya giriş-çıkış ölçüleri hangi adresin hangi borsaya ait olduğunu bilmeye dayanır. Yeni bir borsa adresi bulununca **geçmiş değerler de yeniden hesaplanır**. Bugün indirilen "2021'deki borsa girişi", 2021'de bilinen sayı değildir. Coin Metrics ve Glassnode bu yüzden ayrıca "point-in-time" (o an bilinen) veri satıyor; ücretsiz değil.

## Kaynaklar

| Kaynak | Ne verir | Geçmiş | Anahtar | Lisans | Revizyon / geleceği görme riski | 5 coin |
|---|---|---|---|---|---|---|
| **Coin Metrics Community API** | Aktif adres (AdrActCnt), piyasa değeri, arz, MVRV (CapMVRVCur), işlem sayısı | Günlük, **tam geçmiş** (ör. BTC aktif adres 2009-01-03'ten dün'e; ölçüldü) | Yok (sınır: IP başına 6 sn'de 10 istek) | CC BY-NC (ticari olmayan kullanım) | Adres ve işlem sayıları düşük risk (zincirden sayılır; sezgisel kuralları değişirse revize olabilir) | BTC, ETH, XRP, BNB evet; **SOL yok** (ücretsiz katmanda sadece fiyat ve hacim) |
| Coin Metrics, borsa akışları (FlowInEx/OutEx) | Borsalara giren/çıkan coin | Tam geçmiş | Yok | CC BY-NC | **Yüksek:** borsa adresleri bulundukça geçmiş yeniden yazılıyor (Coin Metrics'in kendi duyuruları) | Sadece **BTC ve ETH** |
| CryptoQuant ücretsiz | Borsa rezervleri/akışları | **Son 30 gün** | Ücretsiz hesap | Kendi şartları | Yüksek (aynı adres sorunu) | — |
| Glassnode | Her şey | Uzun | Ücretli (ücretsiz API teyit edilemedi) | — | Point-in-time ürünü var, ücretli | — |
| Blockchain.com grafikleri | BTC benzersiz adres vb. | Uzun | Teyit edilemedi | — | Düşük | Sadece BTC |
| CoinGecko Demo | Piyasa değeri, hacim | Son 365 gün | Ücretsiz demo anahtarı | — | Düşük | Hepsi, ama geçmiş kısa |
| CoinMarketCap ücretsiz | Güncel fiyatlar | Geçmiş yok (ücretsiz katmanda boş döner) | Ücretsiz hesap | — | — | — |
| Token kilit açılımları (araştırma 13) | Arz takvimi | Değişken | Pro ücretli | — | Yüksek (takvim revizyonu) | Ana 5'te önemsiz (BTC'de yok) |

### Ölçerken bulunan iki tuzak

1. **BNB'nin zincir değişikliği:** Coin Metrics'te BNB aktif adres serisi 2017-07'de başlıyor ama 2018-06-01'de sadece **185** adres gösteriyor. BNB 2019'a kadar Ethereum üzerinde bir ERC-20 tokendı, sonra kendi zincirine geçti. Seri gerçek kullanımı değil, **zincir değişikliğini** gösteriyor. Coin bazında karşılaştırma yanıltır.
2. **SOL'un ücretsiz ağ verisi yok:** ücretsiz katmanda SOL için sadece fiyat ve hacim var (Coin Metrics'in tam Solana geçmişi ücretli üründe).

Sonuç: **coin bazında temiz bir ağ verisi yok.** Temiz olan, piyasa geneli bir BTC (ve ETH) ölçüsü. Tıpkı Fear & Greed ve Wikipedia ilgisi gibi.

## Önerilen test edilebilir hipotezler (en fazla 2)

İkisi de piyasa geneli, sadece BTC zincir verisi, bir önceki günün değeri, anahtarsız, revizyon riski düşük:

1. **Değerleme aşırılığı (MVRV):** MVRV = piyasa değeri / "gerçekleşmiş değer" (her coinin en son el değiştirdiği fiyat üzerinden). Geleneksel okuma: MVRV yüksekken piyasa, ortalama sahibin çok kârda olduğu bir aşırı ısınma bölgesinde. Hipotez: BTC MVRV ders kitabı eşiğinin (≈3,5; 2018 MVRV makalesinden) üstündeyken yeni giriş yok. **Uyarı:** bu, T144 ve T147 ile aynı "geç heyecan" ailesi. İkisi de çalışmadı (T147 neredeyse hiç devreye girmedi); MVRV > 3,5 de yılda birkaç hafta görülen nadir bir durum. Önsel beklenti düşük.
2. **Ağ kullanım trendi:** BTC aktif adres sayısının 30 günlük ortalaması 365 günlük ortalamasının üstündeyken (ağı kullanan kişi sayısı artıyor) yeni girişe izin ver. Fiyattan bağımsız bir kullanım ölçüsü. **Uyarı:** borsa hacminden yapılan benzer "katılım" fikri (T144) çok kötü çıktı; aktif adres, hacimden farklı bir şey ölçüyor ama önsel yine temkinli.

**Önerilmeyenler:** borsa akışları (revizyon riski yüksek, sadece BTC/ETH), coin bazında ağ verisi (BNB zincir değişikliği, SOL yok), CryptoQuant/CoinGecko/CoinMarketCap ücretsiz katmanları (geçmiş yok ya da çok kısa), kilit açılımları.

**Not:** Coin Metrics topluluk verisinin lisansı CC BY-NC (ticari olmayan). Bu araştırma için uygun; bot ileride ticari bir ürüne dönüşürse lisans yeniden değerlendirilmeli.

## Kaynaklar

- Coin Metrics Community Data (anahtarsız uç nokta, sınırlar): https://docs.coinmetrics.io/packages/coin-metrics-community-data
- Coin Metrics kapsam ve lisans (CC BY-NC): https://docs.coinmetrics.io/service-and-support/coverage
- Coin Metrics adres ölçüleri (AdrActCnt vb.): https://docs.coinmetrics.io/network-data/network-data-overview/addresses
- Coin Metrics, Solana tam geçmiş (ücretli üründe): https://coinmetrics.io/?p=19160
- Borsa akış verisinin sonradan değişmesi (Ethereum akışlarının yeniden hesaplanması): https://cryptoslate.com/ethereums-past-outflow-charts-can-change-when-more-exchange-wallets-are-identified/
- Glassnode, point-in-time veri (revizyon sorunu): https://insights.glassnode.com/introducing-point-in-time-data
- CryptoQuant API planları (ücretsiz: 30 gün): https://cryptoquant.com/apis
- CoinMarketCap ücretsiz katmanda geçmiş yok: https://docs.coupler.io/sources/category/finance-and-accounting/coinmarketcap/common-issues
- CoinGecko geçmiş veri API karşılaştırması: https://www.coingecko.com/learn/best-historical-crypto-data-apis
- Blockchain.com BTC benzersiz adres grafiği: https://www.blockchain.com/charts/n-unique-addresses
- Kendi ölçümüm (2026-11-02, Coin Metrics Community API, anahtarsız): `catalog-v2/asset-metrics` ve `timeseries/asset-metrics` (BTC aktif adres 2009-01-03 → 2026-10-31; BNB 2018-06-01 = 185; SOL ağ ölçüsü yok; akışlar sadece BTC/ETH).

## Doğrulanamayanlar

- Blockchain.com grafik API'sinin anahtarsız olup olmadığı ve tam geçmişi (sayfada JSON indirme var, uç nokta belgesini okumadım).
- Glassnode'un ücretsiz API'si olup olmadığı (kaynaklar çelişkili).
- MVRV ≈3,5 eşiğinin kaynağı: hafızadan, 2018 MVRV yazısı (Mahmudov ve Puell); kullanmadan önce teyit edilmeli.

## Anlaman gerekenler

- **Geçmiş verinin kendisi değişebilir.** Borsa akışı gibi ölçüler sonradan yeniden hesaplanır; bugün indirilen geçmiş, o gün bilinen geçmiş değildir. Backtest'te bu, fark edilmeden geleceği görmek demektir.
- **Bir veri serisi, ölçtüğünü sandığın şeyi ölçmeyebilir.** BNB'nin 2018'deki 185 adresi kullanım değil, zincir değişikliği.
- **Aynı fikir farklı veriyle yine aynı fikirdir.** "Heyecan zirvesinde girme" fikri hacim (T144) ve ilgi (T147) ile çalışmadı; MVRV ile denemek üçüncü bakış olur ve N'i artırır.

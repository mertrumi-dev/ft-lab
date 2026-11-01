# Araştırma 07: Binance demo (Faz 5 hazırlığı, anahtarsız)

Tarih: 2026-11-01. Bu belge **hiçbir anahtar oluşturmaz, istemez**. Anahtar adımı ileride Kaan'ın açık onayıyla yapılır.

## Kısa cevap

- **Freqtrade 2026.10, Binance'in demo hesabına bağlanmayı bilerek desteklemiyor.** Kaynak kodda (`freqtrade/exchange/binance.py`) Binance için `"supports_demo_trading": False` yazıyor. Yanındaki not: Binance demosu "canlı piyasanın simülasyonu değil, ayrı bir piyasa". Desteklenen tek borsa Bybit (`freqtrade/exchange/bybit.py`).
- Freqtrade'in eski `"sandbox": true` ayarı da artık yok: 2026.10 kaynağında "sandbox" kelimesi hiç geçmiyor. İnternetteki `sandbox: true` örnekleri 2021 belgelerinden.
- Freqtrade ayrıca `demo_trading` ile `dry_run`'ın birlikte açılmasını reddediyor ("Demo trading cannot be used together with dry_run", `config_validation.py`). Bunu bizim config'imizle de denedik.
- **ccxt kütüphanesi (4.5.90) Binance demosunu destekliyor:** `enable_demo_trading(True)` → `https://demo-api.binance.com/api/v3`. Kendi mini botumuz ccxt kullandığı için Binance demosuna bağlanabilir.

## Demo, testnet, dry-run: farkları

| | Dry-run (şu an) | Binance Spot Testnet | Binance Demo Mode |
|---|---|---|---|
| Adres | yok (bot kendi içinde) | testnet.binance.vision | demo-api.binance.com |
| Para | sahte, botun içinde | sahte bakiye, ayda bir sıfırlanır | sahte bakiye, istenince sıfırlanır |
| Fiyat ve emir defteri | gerçek borsanın fiyatı | **ayrı, gerçekten bağımsız**; çoğu zaman çok sığ | gerçek borsaya **benzer** |
| Emir gerçekten borsaya gider mi | hayır | evet (test borsasına) | evet (demo borsasına) |
| Ne işe yarar | kuralın mantığını izlemek | yeni API özelliklerini denemek | gerçekçi piyasada emir davranışını ölçmek |

Kaynak: Binance geliştirici belgeleri, Demo Mode "General Info": testnet fiyatları ve emir defteri canlıdan bağımsız, Demo Mode'unki canlıya benzer, Demo Mode her zaman canlıyla aynı özelliklere sahip. Bizim amacımız (gerçekçi emir dolması) için **Demo Mode** doğru seçim; testnet değil.

## Dolum (fill) dry-run'dan nasıl farklı?

Dry-run emri borsaya göndermez; fiyat limit fiyatını geçtiyse emri "doldu" sayar. Demo'da emir gerçek bir eşleştirme motoruna gider:

- **Kısmi dolum:** emrin bir kısmı dolar, bir kısmı bekler.
- **Sıra:** limit emir tahtada başkalarının arkasında bekler; fiyat değse bile dolmayabilir.
- **Ret:** en küçük işlem tutarı (min notional), fiyat/miktar hassasiyeti, bakiye yetersiz gibi hatalar gerçekten olur.
- **Gecikme ve istek sınırı (rate limit):** ağ gecikmesi ve "çok fazla istek" hataları yaşanır.
- **Komisyon** borsanın kendi hesabıyla kesilir.

`ft.py execution` raporu (kart 25) bunları ölçmek için yazıldı. Demo, dry-run'ın göremediği bu farkları görünür yapar.

## Seçenekler ve karar

1. **Mini bot + Binance Demo Mode (ÖNERİ).** ccxt demo modunu doğrudan destekliyor; kodu biz yazdık, aynı VolTarget kuralını oynuyor (eşlik testi var). Değişiklik küçük: `public_exchange()` yanına sadece demo anahtarıyla çalışan, `enable_demo_trading(True)` çağıran bir bağlantı. Freqtrade botu bu arada dry-run'da kalır; iki sonuç karşılaştırılır.
2. **Freqtrade + Bybit demo.** Freqtrade'in resmi desteklediği tek yol. Dezavantajı: farklı borsa (komisyon, likidite, coin listesi biraz farklı). Freqtrade'in kendisi gerçek demo emri görmek istenirse ikinci adım olabilir.
3. **Freqtrade + Binance, ccxt adreslerini elle değiştirerek.** Reddedildi: Freqtrade geliştiricilerinin bilerek kapattığı bir yolu zorlamak olur, desteklenmiyor, sessizce yanlış çalışabilir. Freqtrade çekirdeği de değiştirilmez (CLAUDE.md).

Karar: Faz 5 = **seçenek 1** (Binance Demo Mode, mini bot ile), Freqtrade dry-run'da devam. Gerekirse sonra seçenek 2.

## Repoda hazırlananlar (anahtarsız)

- `user_data/config/config.demo.json`: `dry_run: true`, spot, `exchange.key/secret` boş, `demo_trading: false`, `ftlab_demo.status` = "NOT READY" ve nedeni. Freqtrade'in kendi doğrulamasından geçiyor (config.json ile birlikte yüklendi, şema + tutarlılık kontrolü OK).
- `deploy/preflight.py` → `check_demo_config`: dosyada anahtar varsa, spot değilse, ya da `dry_run: false` iken desteklenen bir demo borsası (`demo_trading: true` + Bybit) yoksa **FAIL**. Yani bu dosya asla "dry-run kapalı + gerçek hesap" haline gelemez.
- Testler (`tests/test_preflight.py`, `tests/test_config_safety.py`): anahtarlar boş, spot, kaldıraç yok, gerçek hesapla `dry_run: false` kombinasyonu FAIL.

## Kaan'ın ileride yapacağı adımlar (onay verdiği gün)

1. binance.com'da giriş yap → **Demo Trading** (Demo Mode) bölümüne geç. Gerçek hesabın anahtar sayfasında **değil**, demo hesabın API yönetiminde anahtar oluştur.
2. İzinler: sadece **okuma + spot işlem**. Para çekme (withdraw) iznini **asla** açma. Mümkünse IP kısıtlaması koy (sunucunun IP'si).
3. Anahtarı ve gizli anahtarı **sadece `.env`'ye** yaz; config dosyalarına, sohbete, ekran görüntüsüne asla. `.env` git'e girmez (`.gitignore`, test zorunlu).
4. Claude mini botun demo bağlantısını ekler (ayrı commit, test: anahtarlar sadece ortam değişkeninden okunur, adres `demo-api.binance.com` değilse bot başlamaz).
5. 4 hafta: mini bot demo'da, Freqtrade dry-run'da; her gün `execution` raporuyla dolum oranı, kayma, ret sayısı karşılaştırılır.

**Gerçek hesabın anahtarı hiçbir aşamada kullanılmaz.** Gerçek paraya geçiş bu planın parçası değil; ayrı bir karar, ayrı bir onay.

## Kaynaklar

- Freqtrade 2026.10 kaynağı (Docker image içinde): `freqtrade/exchange/binance.py` (supports_demo_trading False ve gerekçesi), `freqtrade/exchange/bybit.py` (True), `freqtrade/exchange/exchange.py` (`validate_demo_trading`, `enable_demo_trading`), `freqtrade/configuration/config_validation.py` (`_validate_demo_trading`).
- Binance Developers, Demo Mode General Info: https://developers.binance.com/docs/binance-spot-api-docs/demo-mode/general-info
- Eski Freqtrade sandbox sayfası (artık geçerli değil, 2021.2): https://www.freqtrade.io/en/2021.2/sandbox-testing
- ccxt 4.5.90 (`binance.enable_demo_trading`, `set_sandbox_mode`), image içinde denendi.

## Anlaman gerekenler

- **Demo ≠ testnet.** Testnet'in fiyatları gerçek piyasayla ilgisiz; demo gerçek piyasaya benziyor. Bizim ölçmek istediğimiz şey gerçekçi dolum olduğu için demo.
- **Belgeye değil koda bak.** İnternetteki `sandbox: true` örnekleri eski sürümden. Kullandığımız sürümün kaynak kodu, Binance demosunun bilerek kapatıldığını gösterdi.
- **Güvenlik kuralını test yapar, insan hatırlamaz.** `config.demo.json` gerçek hesapla dry-run kapalı hale gelirse test ve preflight FAIL verir.

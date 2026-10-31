# Öğretici kart 00: Faz 0 kurulumu

Bu kart Faz 0'da eklenen her dosyayı ve her önemli satırı açıklıyor. Sıra: önce büyük resim, sonra dosya dosya.

---

## 1. Büyük resim: hangi parça ne yapıyor?

```
Binance (gerçek fiyatlar)
      │  internetten fiyat verisi
      ▼
┌────────────── Docker container "ft-lab" ──────────────┐
│ Freqtrade                                               │
│   ├─ config.json  → hangi borsa, hangi coinler, ne kadar sahte para │
│   ├─ SampleStrategy → "ne zaman al, ne zaman sat" kuralları │
│   ├─ sqlite dosyası → yapılan (sahte) işlemlerin kaydı  │
│   └─ API server   → FreqUI web arayüzü (port 8080)      │
└─────────────────────────────────────────────────────────┘
      │
      ▼
Tarayıcın: http://127.0.0.1:8080
```

- **Freqtrade**: botun motoru. Borsaya bağlanır, fiyatları çeker, stratejiye sorar, işlemi yapar, kaydeder. Biz motoru değiştirmiyoruz, sadece stratejiyi (karar kısmını) yazacağız.
- **Dry-run (kuru çalıştırma)**: Freqtrade gerçek fiyatları izler ama emri borsaya göndermez; "bu fiyattan aldım" diye kendi defterine yazar. Para hayalî: 1000 USDT.
- **USDT**: Dolara sabitlenmiş kripto para (1 USDT ≈ 1 dolar). Coinleri USDT ile alıp satıyoruz. "BTC/USDT" = "Bitcoin'in USDT cinsinden fiyatı".

## 2. Docker nedir, neden kullanıyoruz?

Freqtrade'in çalışması için Python'un belirli bir sürümü, onlarca kütüphane ve TA-Lib gibi derlenmesi zor parçalar gerekiyor. Bunları Mac'ine tek tek kurmak hem zor hem de bilgisayarını kirletir.

Docker şunu yapar: Freqtrade ekibi her şeyin kurulu olduğu hazır bir "kutu" hazırlamış. Biz o kutuyu indirip çalıştırıyoruz.

- **Image (imaj)**: Kutunun kalıbı. Değişmez. `freqtradeorg/freqtrade:2026.10` bir image'ın adı. `2026.10` sürüm etiketi.
- **Container (konteyner)**: Kalıptan üretilen, çalışan kutu. Silip yeniden oluşturabilirsin; image aynı kalır.
- **Volume (bağlanmış klasör)**: Container silinince içindeki her şey gider. Bunu istemiyoruz (işlem kayıtları, loglar). O yüzden Mac'indeki `user_data` klasörünü container'ın içine "bağlıyoruz". Container o klasöre yazınca aslında senin diskine yazıyor.
- **Docker Compose**: Container'ı nasıl çalıştıracağımızı bir dosyaya (`docker-compose.yml`) yazıp tek komutla (`docker compose up`) başlatmamızı sağlar. Uzun komutları ezberlemene gerek kalmaz.

## 3. `docker-compose.yml` satır satır

```yaml
services:
  freqtrade:                                   # servisin adı; komutlarda bu adı kullanırız
    image: freqtradeorg/freqtrade:2026.10      # hangi image
```
Resmi örnek `:stable` kullanıyor. Ben sabit sürüm (`2026.10`) seçtim. Neden: `stable` etiketi her yeni sürümde değişir; bir gün `docker compose pull` yapınca bot farklı davranmaya başlayabilir ve sebebini bulamayız. Sabit sürümle, güncellemeyi bilerek ve test ederek yaparız. M2 işlemcin için `arm64` sürümü var, kontrol ettim.

```yaml
    restart: unless-stopped
```
Bot çökerse veya Mac yeniden başlarsa Docker botu kendisi tekrar başlatır. Sen `docker compose down` ile durdurursan başlatmaz.

```yaml
    container_name: ft-lab
```
Çalışan kutunun adı. `docker ps` yazınca bu adı görürsün.

```yaml
    env_file:
      - .env
```
`.env` dosyasındaki değişkenleri container'a verir. Şifreler buradan gelir (aşağıda 5. bölüm). Resmi örnekte yok; ben ekledim çünkü şifreleri `config.json`'a yazarsak GitHub'a gider.

```yaml
    volumes:
      - "./user_data:/freqtrade/user_data"
```
Format: `mac'teki_yol:container'daki_yol`. Mac'indeki `ft-lab/user_data`, container içinde `/freqtrade/user_data` olarak görünür.

```yaml
    ports:
      - "127.0.0.1:8080:8080"
```
Container içindeki 8080 portunu Mac'indeki 8080'e açar. Baştaki `127.0.0.1` çok önemli: "sadece bu bilgisayardan erişilsin" demek. Bunu yazmasak aynı Wi-Fi'daki herkes FreqUI'ye ulaşmayı deneyebilirdi.

```yaml
    command: >
      trade                                                       # botu çalıştır
      --logfile /freqtrade/user_data/logs/freqtrade.log           # log nereye yazılsın
      --db-url sqlite:////freqtrade/user_data/tradesv3.dryrun.sqlite  # işlem kayıtları
      --config /freqtrade/user_data/config/config.json            # ayar dosyası
      --strategy SampleStrategy                                   # hangi strateji sınıfı
```
- `sqlite`: tek dosyadan oluşan küçük bir veritabanı. Her sahte işlem buraya kaydedilir. Dosya adına `dryrun` koydum ki ileride demo borsa kayıtlarıyla karışmasın.
- `sqlite:////` içindeki 4 eğik çizgi hata değil: `sqlite:///` öneki + mutlak yolun başındaki `/`.
- Config yolunu brief'teki klasör yapısına (`user_data/config/`) göre değiştirdim; resmi örnek `user_data/config.json` kullanıyor.

## 4. `user_data/config/config.json` alan alan

| Alan | Değer | Anlamı |
|---|---|---|
| `dry_run` | `true` | Sahte para modu. **Bu projede asla false olmaz.** Test bunu zorluyor. |
| `dry_run_wallet` | `1000` | Sahte cüzdanda 1000 USDT ile başla. |
| `trading_mode` | `spot` | Sadece elindeki parayla al-sat. Kaldıraç (borç parayla büyütülmüş işlem) yok. |
| `stake_currency` | `USDT` | İşlemler USDT ile yapılır. |
| `stake_amount` | `unlimited` | Her işleme ne kadar para koyulsun? `unlimited` = cüzdanı açık işlem hakkına eşit böl. 1000 USDT / 3 ≈ 333 USDT. |
| `max_open_trades` | `3` | Aynı anda en fazla 3 açık işlem. Riski dağıtır. |
| `tradable_balance_ratio` | `0.99` | Paranın %99'unu kullan, %1'i komisyon vb. için kenarda kalsın. |
| `unfilledtimeout` | 10 dk | Verilen emir 10 dakikada gerçekleşmezse iptal et. |
| `entry_pricing` / `exit_pricing` | `same`, order book | Alırken/satarken fiyatı emir defterinden (o anki alıcı-satıcı listesi) al. Resmi örnekteki değerler. |
| `exchange.name` | `binance` | Fiyatları Binance'ten çek. |
| `exchange.key` / `secret` | `""` | Borsa API anahtarları. Dry-run'da gerekmez, boş kalır. |
| `pair_whitelist` | 5 pair | Botun bakacağı coinler. Neden bunlar: en büyük ve en likit (çok alıcı-satıcı olan) coinler, Binance'te en uzun geçmiş verisi olanlar. Likit coinde kayma (beklediğin fiyattan farklı fiyata alma) az olur. |
| `pairlists` | `StaticPairList` | Listeyi sabit tut, otomatik değiştirme. Testlerin tekrarlanabilir olması için şart. |
| `telegram.enabled` | `false` | Faz 5'te açacağız. |
| `api_server.enabled` | `true` | FreqUI için web sunucusunu aç. |
| `api_server.listen_ip_address` | `0.0.0.0` | Container içinde "her yerden dinle". Korkma: dışarıya açılış `docker-compose.yml`'deki `127.0.0.1` ile zaten kısıtlı. Container içinde `127.0.0.1` yazsaydık Mac'inden bile ulaşamazdın. |
| `api_server.username/password/jwt_secret_key/ws_token` | `""` | Boş. Gerçek değerler `.env`'den gelir. |
| `initial_state` | `running` | Başlar başlamaz işlem aramaya başla. |
| `force_entry_enable` | `false` | FreqUI'den elle "şimdi al" butonunu kapalı tut. |
| `process_throttle_secs` | `5` | Bot her 5 saniyede bir döngüsünü çalıştırır. |

`timeframe` (mum süresi) config'de yok, çünkü strateji kendi belirliyor. SampleStrategy 5 dakikalık mum kullanıyor. Kendi stratejilerimizde 1h kullanacağız.

## 5. `.env` ve `.env.example`: şifreler nerede durur?

Freqtrade'in bir özelliği: `FREQTRADE__BÖLÜM__ALAN` şeklinde bir ortam değişkeni (environment variable: programa dışarıdan verilen ayar) görürse, config'teki o alanı bu değerle ezer.

```
FREQTRADE__API_SERVER__PASSWORD=gizli123
         ↓ eşdeğeri
config.json → "api_server": { "password": "gizli123" }
```

Böylece:
- `config.json` GitHub'a gider ama içinde şifre yoktur.
- `.env` sadece senin bilgisayarında durur; `.gitignore` onu GitHub'dan saklar.
- `.env.example` ise "hangi değişkenler lazım" listesidir, şifresiz; GitHub'a gider.

Bunu burada denedim: `.env` değerleriyle Freqtrade config'i doğru okudu, şifre `REDACTED` olarak gizlendi.

`openssl rand -hex 32`: 64 karakterlik rastgele bir metin üretir. `jwt_secret_key` FreqUI'ye giriş yaptığında verilen "giriş biletini" imzalamak için kullanılır; tahmin edilemez olmalı.

## 6. `.gitignore`

Git'e "bu dosyaları hiç takip etme" der.

- `.env`: şifreler.
- `user_data/data/*`: indirilen fiyat verisi. Yüzlerce MB olabilir, istediğimizde tekrar indiririz.
- `user_data/logs/*`, `*.sqlite`: botun çalışırken ürettiği dosyalar. Kişisel ve sürekli değişir.
- `!user_data/data/.gitkeep`: Git boş klasörü saklamaz. İçine boş `.gitkeep` dosyası koyup "bunu hariç tutma" (`!`) diyoruz ki klasör repoda var olsun. Log klasörü yoksa Freqtrade başlarken hata verebilir.

## 7. `tests/test_config_safety.py`

pytest: Python'da test yazma aracı. `test_` ile başlayan her fonksiyonu çalıştırır; içindeki `assert` yanlışsa testi "FAILED" yapar.

Bu dosya botun **emniyet kemeri**:

- `test_dry_run_is_on`: config'te `dry_run` true değilse kırmızı.
- `test_spot_only`: futures/kaldıraç açılırsa kırmızı.
- `test_no_secrets_in_config`: key/secret/şifre alanlarından biri doluysa kırmızı.
- `test_env_file_is_ignored`: `.gitignore` içinde `.env` yoksa kırmızı.

`@pytest.mark.parametrize`: aynı testi farklı girdilerle tekrar çalıştırır. Burada `user_data/config/` içindeki **her** json dosyası için ve **her** şifre alanı için ayrı test üretiyor. İleride yeni bir config eklersek otomatik kontrol edilir. Toplam 11 test.

Testin gerçekten işe yaradığını görmek için `dry_run`'ı geçici olarak `false` yaptım: test kırmızı oldu (`1 failed`), geri aldım: `11 passed`.

## 8. `SampleStrategy` (bizim değil, sadece boru hattını test etmek için)

Freqtrade'in kendi örnek stratejisi, değiştirmeden kopyaladım (dosyanın başında kaynak ve lisans: GPL-3.0). Bunu ayarlamayacağız; görevi sadece "sistem uçtan uca çalışıyor mu" testi.

Ne yapıyor, kabaca:
- **RSI** (göreceli güç endeksi, 0-100 arası; düşükse "çok satılmış", yüksekse "çok alınmış") 30'un üstüne çıktığında
- ve fiyatın yumuşatılmış hali (TEMA) yükseliyorsa ve Bollinger bandının ortasının altındaysa → **al**.
- RSI 70'in üstüne çıkınca → **sat**.
- `minimal_roi`: kâr hedefi. İşlem açılır açılmaz %4 kârdaysa sat; 30 dk sonra %2 yeter; 60 dk sonra %1 yeter.
- `stoploss = -0.10`: %10 zarara düşerse zararına sat (kaybı sınırla).
- Kodda "short" (düşüşten para kazanma) kısımları var ama `can_short = False` ve spot modda olduğumuz için hiç çalışmaz.

Burada doğruladım: Freqtrade stratejiyi hatasız yükledi (`list-strategies` → `SampleStrategy ... OK`).

## 9. Neyi doğrulayamadım?

Benim çalıştığım bulut ortamı Binance'e bağlanamıyor. Bu yüzden botun gerçekten fiyat çekip dry-run işlem yaptığını **senin Mac'inde** göreceğiz. Doğrulananlar: config geçerli, strateji yükleniyor, docker-compose dosyası geçerli, güvenlik testleri geçiyor.

---

## Anlaman gerekenler

1. Freqtrade motor, strateji karar mekanizması. Biz sadece stratejiyi yazacağız.
2. Şifreler `.env`'de, ayarlar `config.json`'da. `config.json` GitHub'a gider, `.env` asla.
3. `dry_run: true` bu projenin emniyet kemeri; test bunu her seferinde kontrol ediyor.

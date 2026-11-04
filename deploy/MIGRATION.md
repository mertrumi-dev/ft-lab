# Mac'ten sunucuya taşıma planı (2026-11-02)

`deploy/README.md` sunucunun nasıl kurulacağını anlatıyor. Bu belge **geçişin sırasını** anlatıyor: iki bot (ana bot VolTarget + paralel ADX20) Mac'ten sunucuya, geçmişleri kaybolmadan ve iki cüzdan aynı anda çalışmadan nasıl geçer.

Hepsi **sahte para (dry-run)**. Borsa anahtarı yok, kaldıraç yok. `deploy/preflight.py` bunları her seferinde kontrol eder.

## Kaan'dan gerekenler (kısa liste)

| # | Ne | Neden | Örnek |
|---|---|---|---|
| 1 | Sunucunun işletim sistemi | Kurulum komutları buna göre | Ubuntu 24.04 (önerilen) |
| 2 | RAM / disk | Ölçüldü: her bot ~400-420 MB RAM (2026-11-02), iki bot ~0,85 GB; işletim sistemiyle birlikte | en az 2 GB RAM (rahatı 4 GB), 20 GB disk |
| 3 | SSH ile nasıl giriliyor | Kurulumu ve kontrolü SSH ile yapacağız | `ssh kullanici@1.2.3.4` + **SSH anahtarı** (şifre değil) |
| 4 | `sudo` yetkisi var mı | Docker kurulumu ve saat ayarı için | evet / hayır |
| 5 | Sunucu Türkiye dışında mı | Binance bazı ülkelerden erişimi engelliyor (ABD gibi) | Almanya, Hollanda: sorun yok |
| 6 | GitHub erişimi | Repo özel; sunucunun `git pull` yapabilmesi için | sunucuda `gh auth login` veya salt-okunur deploy key |

**Bizim istemediğimiz şeyler:** borsa API anahtarı, şifre, `.env` içeriği. `.env`'i Kaan kendisi `scp` ile kopyalar (README adım 4); biz içeriğini hiç görmeyiz. SSH anahtarını Kaan kendi Mac'inde oluşturur; özel anahtar Mac'ten hiç çıkmaz.

## Geçiş sırası

Altın kural: **aynı veritabanını kullanan iki bot asla aynı anda çalışmaz.** Aynı anda çalışırlarsa iki ayrı sahte cüzdan oluşur ve sonuçlar karışır.

### 1. Sunucuyu hazırla (botlar Mac'te çalışmaya devam eder)

README adım 1-3: SSH, Docker, repo. Ek olarak:

```bash
sudo timedatectl set-ntp true     # saat senkronu: borsa isteklerinde zaman damgası var
sudo ufw allow OpenSSH && sudo ufw enable
```

Ubuntu Server'da güvenlik güncellemeleri (`unattended-upgrades`) varsayılan olarak açık; değiştirmiyoruz.

**Not:** Docker yayınladığı portlar için ufw'yi atlar (kendi iptables kurallarını ufw'den önce yazar). Bizim portlarımız sadece `127.0.0.1`'e bağlı, bu yüzden dışarıdan zaten erişilemez. `preflight.py` bunu kontrol eder. Port satırını asla `8080:8080` (adres olmadan) yapma.

### 2. Docker log sınırı (bir kere)

Linux'ta Docker'ın varsayılan log sürücüsü (`json-file`) logu sınırsız büyütür. Aylar içinde diski doldurabilir. `local` sürücüsü kendiliğinden döner: 20 MB × 5 dosya, konteyner başına en fazla ~100 MB.

```bash
echo '{"log-driver": "local"}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

Bu ayar sadece **yeni oluşturulan** konteynerlere uygulanır. Botları bu adımdan sonra başlatıyoruz, sorun yok.

### 3. Ön kontrol (veritabanları olmadan)

```bash
python3 deploy/preflight.py
```

Bu aşamada iki WARN beklenir: `.env` eksikse FAIL, veritabanları eksikse WARN ("NEW empty dry-run wallet"). Geri kalan her şey PASS olmalı.

### 4. Kesinti: Mac'i durdur, durumu taşı, sunucuyu başlat

Bu adım ~5 dakika sürer. Botlar 1 saatlik mumla çalıştığı için bu sürede kaçan bir sinyal pratikte olmaz (sinyal saat başı kontrol edilir; saat başını kaçırmamak için :05-:50 arasında yap).

**Mac'te:**

```bash
cd ~/ft-lab
docker compose --profile forward down          # iki botu da durdur (veritabanları yerinde kalır)
scp user_data/tradesv3.voltarget.dryrun.sqlite user_data/tradesv3.adx20.dryrun.sqlite \
    kullanici@sunucu-adresi:~/ft-lab/user_data/
scp .env kullanici@sunucu-adresi:~/ft-lab/.env
```

**Sunucuda:**

```bash
cd ~/ft-lab
chmod 600 .env
python3 deploy/preflight.py                     # artık READY ve iki DB "present" olmalı
docker compose up -d freqtrade
docker compose --profile forward up -d --no-deps forward-adx20
```

Neden önce durdurup sonra kopyalıyoruz: çalışan bir SQLite dosyasını kopyalamak yarım yazılmış bir kopya üretebilir. Bot durunca dosya kapanır ve kopya tutarlı olur.

### 5. Doğrula

```bash
python3 scripts/health.py
python3 scripts/health.py --service forward-adx20
docker compose --profile forward logs --tail 50 | grep -iE "strategy|dry run|error"
```

İkisinde de "Dry run is enabled", doğru strateji adı, 0 hata. İşlem sayıları Mac'teki son durumla aynı olmalı (geçmiş taşındı).

### 6. Mac'te ne kalır?

- **Botlar Mac'te bir daha başlatılmaz.** Başlatılırsa iki cüzdan olur.
- Araştırma (backtest, denemeler, `daily.py`) Mac'te kalır. Backtest'ler 2 GB'lık bir sunucu için ağır; Mac'te 17 GB RAM var.
- Günlük rapor, sunucudaki botların veritabanını okumalı. Seçenek: her gün `scp` ile veritabanının bir kopyasını Mac'e çekmek (salt okunur, botu etkilemez). Bu, geçişten sonra ayrı bir işte yapılacak.

### Geri dönüş (bir şey ters giderse)

Sunucuda `docker compose --profile forward down`, veritabanlarını Mac'e geri `scp` et, Mac'te iki botu başlat. Veritabanları her an tek bir yerde çalıştığı için hiçbir şey kaybolmaz.

## Stop borsada kalmalı (demo ve sunucu)

Mac'teki dry-run botlarında -%8 stopu botun kendisi izliyor (5 saniyede bir). Mac uyurken kimse izlemiyor (öğretici kart 39). Demo (Faz 5) ve sunucu için kontrol listesi:

- [ ] Demo ya da sunucu Freqtrade ayarında `order_types.stoploss_on_exchange: true`, `stoploss: "limit"` (Binance spotta `stop_loss_limit`), `stoploss_on_exchange_interval: 60`, `stoploss_on_exchange_limit_ratio: 0.99`. Hazır şablon: `user_data/config/config.demo.json`.
- [ ] `python3 deploy/preflight.py` → "config.demo.json: stop lives on the exchange" PASS olmalı (kapatılırsa FAIL verir).
- [ ] Mini bot demoda zaten borsada stop kuruyor (minibot/demo.py, `place_stop`).
- Çalışan Mac dry-run botlarının ayarı **bilerek değiştirilmedi**: kalıcı çözüm, hiç uyumayan sunucu.

## Sunucuda tekrar denenecek

- [ ] GDELT DOC API bu Mac'in IP'sinden HTTP 429 veriyor (28 saat sessizlikten sonra bile; araştırma 13, journal 2026-11-04). Sunucunun IP'sinden bir kez dene: `curl -s -A "ft-lab-research/0.1" "https://api.gdeltproject.org/api/v2/doc/doc?query=bitcoin&mode=timelinetone&format=json&timespan=7d" | head -c 200`. Çalışırsa haber denemesi ön kayıtla açılabilir.

## Faz 0 sayacı

Taşıma kesintisi Faz 0'ın "24 saat kesintisiz" sayacını sıfırlar. Bu beklenen bir durum. Sunucuda sayaç bir kez başlar ve Mac uykusu artık onu kesmez; zaten taşımanın amacı bu.

## Kaynaklar

- Docker, local logging driver (varsayılan 20 MB × 5): https://docs.docker.com/engine/logging/drivers/local/
- Docker portlarının ufw'yi atlaması: https://github.com/docker/docker/issues/4737 ve https://www.ssdnodes.com/learn/docker-ports-bypass-ufw
- Freqtrade log dosyası kendisi döner (10 MB × 10): `freqtrade/loggers/__init__.py`, Docker image 2026.10

## Anlaman gerekenler

- **Durum (state) taşınır, kod değil.** Kod GitHub'dan gelir; botun hafızası veritabanı dosyasındadır. Taşıma = o dosyanın tek kopyasını bir yerden alıp öbürüne koymak.
- **Tek yazar kuralı:** Bir veritabanına aynı anda sadece bir program yazmalı. Önce durdur, sonra kopyala.
- **Güvenlik katmanları üst üste:** 127.0.0.1 bağlama + ufw + SSH anahtarı. Biri yanlış ayarlansa bile diğerleri korur.

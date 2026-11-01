# Botu 7/24 sunucuya taşıma

## Neden?

Bot şu an Mac'te çalışıyor. Mac'in kapağı kapanınca Mac uyuyor, internet kopuyor ve bot duruyor. 31 Ekim akşamı tam olarak bu oldu: logda 249 bağlantı hatası var, hepsi bu uykudan.

Faz 0'ın şartı "24 saat kesintisiz". Mac'te bu sayaç her kapak kapanışında sıfırlanıyor. Sunucu hiç uyumayan bir bilgisayar; bot orada 7/24 çalışabilir.

Bu rehber **sadece sahte parayla (dry-run)** çalışan botu taşır. Gerçek para, borsa anahtarı, kaldıraç yok; `deploy/preflight.py` bunları kontrol eder.

## Sunucu ne olmalı?

- Linux, tercihen **Ubuntu 22.04 veya 24.04**.
- En az **2 GB RAM, 20 GB disk**. Bot az kaynak yer; backtest'leri yine Mac'te yaparız.
- Sunucuya **SSH** ile bağlanabiliyor olmalısın. SSH, başka bir bilgisayarın terminaline güvenli şekilde girmek demek.

## Adım adım

### 1. Sunucuya bağlan

Mac'te Terminal'i aç:

```bash
ssh kullanici@sunucu-adresi
```

`kullanici` ve `sunucu-adresi` senin sunucunun bilgileri. Bundan sonraki komutlar sunucunun terminalinde çalışır.

### 2. Docker'ı kur (bir kere)

Docker'ın kendi resmi kurulum scripti:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
less get-docker.sh          # ne yaptığına göz at, q ile çık
sudo sh get-docker.sh
sudo usermod -aG docker $USER   # docker'ı sudo'suz kullanmak için
exit                            # çık ve tekrar ssh ile bağlan (grup değişikliği için)
```

Kontrol:

```bash
docker compose version
```

### 3. Repoyu indir

```bash
git clone https://github.com/mertrumi-dev/ft-lab.git
cd ft-lab
```

Repo özelse önce `gh auth login` gerekir (README'deki gibi).

### 4. `.env` dosyasını taşı (elle, ekrana yazdırmadan)

`.env` şifrelerini tutuyor ve GitHub'a hiç gitmiyor; bu yüzden repoyla gelmez. Mac'ten sunucuya doğrudan kopyala. Bu komut **Mac'te** çalışır:

```bash
scp ~/ft-lab/.env kullanici@sunucu-adresi:~/ft-lab/.env
```

Sonra **sunucuda** sadece senin okuyabileceğin hale getir:

```bash
chmod 600 ~/ft-lab/.env
```

`cat .env` gibi komutlarla içeriği ekrana yazdırma: terminal geçmişine ve ekran görüntülerine düşebilir.

### 5. Hazır mı? Kontrol et

```bash
python3 deploy/preflight.py
```

Her satır PASS / WARN / FAIL. Sonda `READY` yazmalı. FAIL varsa botu başlatma, önce düzelt.

### 6. Geçmiş veriyi indir ve botu başlat

```bash
docker compose pull
docker compose up -d
```

`restart: unless-stopped` ayarı sayesinde sunucu yeniden başlasa bile bot kendiliğinden tekrar açılır.

Bu komut **sadece ana botu** başlatır. İleri test botu (`forward-pyramidbtc`, yeni fiyatlarla deneme, yine sahte para) bilerek ayrı bir "profile" arkasında. Onu da istersen:

```bash
docker compose --profile forward up -d forward-pyramidbtc
```

FreqUI'si `127.0.0.1:8081` adresinde (tünel komutunda 8080 yerine 8081 kullan). `preflight.py` ekstra botların profile arkasında ve sadece 127.0.0.1'de kaldığını kontrol eder.

### 7. Sağlık kontrolü

```bash
python3 scripts/health.py
```

Heartbeat, hatalar, işlemler, kill switch ve Faz 0 durumu (kart 18). 24 saat sonra `Faz 0: PASS` görmelisin.

### 8. FreqUI'ye bağlan (SSH tüneliyle)

FreqUI (botun web arayüzü) bilerek sadece sunucunun kendisinden erişilebilir (`127.0.0.1:8080`); internete açık değil. Mac'ten görmek için **Mac'te** bir tünel aç:

```bash
ssh -N -L 8080:127.0.0.1:8080 kullanici@sunucu-adresi
```

Bu komut açıkken Mac'te tarayıcıda http://127.0.0.1:8080 adresi sunucudaki FreqUI'yi gösterir. Ctrl+C ile tüneli kapatırsın; bot çalışmaya devam eder.

Neden tünel? Port'u internete açarsak dünyadaki herkes giriş sayfasını görür ve şifreyi denemeye başlar. Tünelde sadece SSH anahtarı olan sen girebilirsin.

### 9. Güncelleme

Kod değişince sunucuda:

```bash
cd ~/ft-lab
git pull
docker compose up -d     # değişen ayar/strateji ile yeniden başlatır
python3 scripts/health.py
```

## Mac'teki bot ne olacak?

Sunucudaki bot `READY` ve sağlıklı olunca Mac'tekini durdur (`docker compose down`). İkisi aynı anda çalışırsa iki ayrı sahte cüzdan olur ve sonuçlar karışır.

## Anlaman gerekenler

- **Sunucu = hiç uyumayan bilgisayar.** Bot için önemli olan donanım değil, kesintisizlik.
- **Sırlar ayrı yoldan taşınır.** Kod GitHub'dan gelir, `.env` doğrudan senden. Böylece şifre hiçbir zaman ortak bir yerde durmaz.
- **İnternete açık port = saldırı yüzeyi.** Arayüzü tünelle kullanmak, kapıyı kilitli tutup anahtarı cebinde taşımak gibi.

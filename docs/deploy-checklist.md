# Sunucu kontrol listesi: 7/24 dry-run

**Bu liste sahte para (dry-run) içindir.** Gerçek para, borsa anahtarı ve kaldıraç yok. Her adımı Kaan yapar; Claude sunucuya bağlanmaz. Ayrıntılı anlatım: `deploy/README.md`, geçiş sırası: `deploy/MIGRATION.md`.

**Başlamadan:** Mac'te `python3 deploy/preflight.py` → `READY` (son ölçüm 2026-11-05: 24 PASS, 0 WARN, 0 FAIL). Bu ölçüm Mac içindir; sunucuda yeniden çalışır.

## 1. Sunucu

- [ ] Ubuntu 22.04 veya 24.04, en az 2 GB RAM (rahatı 4 GB), 20 GB disk
- [ ] Sunucu ABD'de değil (Binance bazı ülkeleri engelliyor)
- [ ] SSH **anahtarla** giriş çalışıyor; özel anahtar Mac'ten çıkmıyor: `ssh kullanici@sunucu-adresi`

## 2. Docker

- [ ] Kur: `curl -fsSL https://get.docker.com -o get-docker.sh`, `less get-docker.sh`, `sudo sh get-docker.sh`
- [ ] Grup: `sudo usermod -aG docker $USER`, sonra çıkıp yeniden bağlan
- [ ] Açılışta başlasın: `sudo systemctl enable docker`
- [ ] Kontrol: `docker compose version`

## 3. Log döndürme (bot başlamadan ÖNCE)

Linux'ta varsayılan sürücü logu sınırsız büyütür. Ayar sadece yeni konteynerlere uygulanır, bu yüzden sıra önemli.

- [ ] `echo '{"log-driver": "local"}' | sudo tee /etc/docker/daemon.json`
- [ ] `sudo systemctl restart docker`
- [ ] Kontrol: `docker info --format '{{.LoggingDriver}}'` → `local`

## 4. Saat ve saat dilimi

Freqtrade UTC ile çalışır (konteynerin içi de UTC). Sunucuyu da UTC yapınca log ve cron saatleri aynı dili konuşur.

- [ ] `sudo timedatectl set-timezone UTC`
- [ ] `sudo timedatectl set-ntp true`
- [ ] Kontrol: `timedatectl` → `Time zone: UTC`, `System clock synchronized: yes`

## 5. Güvenlik duvarı

- [ ] `sudo ufw allow OpenSSH`, `sudo ufw enable`
- [ ] **8080 ve 8081 için ufw kuralı açma.** Docker yayınladığı portlarda ufw'yi atlar; asıl koruma 6. adımdaki 127.0.0.1 bağlamasıdır

## 6. Repo ve FreqUI'nin kapalı olması

- [ ] `gh auth login` (repo özel), `git clone https://github.com/mertrumi-dev/ft-lab.git`, `cd ft-lab`
- [ ] `docker-compose.yml` port satırları `127.0.0.1:8080:8080` ve `127.0.0.1:8081:8080`. **Asla adressiz `8080:8080` yapma**
- [ ] Dışarıdan kapalı mı? Sunucuda: `ss -tlnp | grep -E ':808[01]'` → sadece `127.0.0.1` görünmeli (botlar başladıktan sonra)
- [ ] FreqUI'ye sadece tünelle gir. **Mac'te:** `ssh -N -L 8080:127.0.0.1:8080 kullanici@sunucu-adresi`, sonra http://127.0.0.1:8080

Not: Freqtrade ayarında `listen_ip_address: 0.0.0.0` yazıyor. Bu konteynerin **içi** içindir; dışarıya kapıyı açan şey compose'daki port satırıdır.

## 7. `.env` (Kaan kendisi taşır)

İçeriği kimseye gösterme, ekrana yazdırma, sohbete yapıştırma.

- [ ] **Mac'te:** `scp ~/ft-lab/.env kullanici@sunucu-adresi:~/ft-lab/.env`
- [ ] **Sunucuda:** `chmod 600 ~/ft-lab/.env`

## 8. Dosya izni

Freqtrade imajı `ftuser` (uid 1000) olarak çalışır ve `user_data/` içine yazar (2026-11-05'te imajda doğrulandı).

- [ ] `id -u` çıktısı 1000 değilse: `sudo chown -R 1000:1000 ~/ft-lab/user_data`

## 9. Geçiş

`deploy/MIGRATION.md` adım 4. Özet:

- [ ] **Mac'te** botları durdur. Mac botları şu an zaten kapalı (2026-11-02'den beri); kapalıysa bu adım atlanır
- [ ] **Mac'te** iki veritabanını `scp` ile kopyala: `tradesv3.voltarget.dryrun.sqlite`, `tradesv3.adx20.dryrun.sqlite`
- [ ] **Sunucuda:** `python3 deploy/preflight.py` → `READY`. FAIL varsa başlatma
- [ ] **Sunucuda:** `docker compose up -d freqtrade`, `docker compose --profile forward up -d --no-deps forward-adx20`
- [ ] Bundan sonra botlar **Mac'te bir daha başlatılmaz**: iki yerde çalışırsa iki ayrı sahte cüzdan olur

## 10. Otomatik yeniden başlama

`restart: unless-stopped` iki serviste de var (`docker-compose.yml`; `tests/test_preflight.py` kontrol ediyor). Sunucu açılınca botlar kendiliğinden kalkar; elle `docker compose down` yapılmışsa kalkmaz.

- [ ] Dene: `sudo reboot`, yeniden bağlan, `docker ps` → iki konteyner `Up`

## 11. Saatlik sağlık kaydı (cron)

- [ ] `crontab -e` ile ekle (`kullanici` yerine kendi kullanıcı adın):

```
PATH=/usr/local/bin:/usr/bin:/bin
0 * * * * cd /home/kullanici/ft-lab && { date -u; python3 scripts/health.py; python3 scripts/health.py --service forward-adx20; } >> /home/kullanici/ft-lab-health.log 2>&1
```

- [ ] Log büyümesin. `sudo nano /etc/logrotate.d/ft-lab-health`:

```
/home/kullanici/ft-lab-health.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
```

- [ ] Bir saat sonra: `tail -40 ~/ft-lab-health.log`

**Bu cron haber vermez, sadece kaydeder.** `health.py` bot ölü olsa bile çıkış kodu 0 döner, yani bildirimi çıkış koduna bağlama. Bildirim (Telegram) Faz 5'te. O zamana kadar günde bir kez bu dosyaya bakılır.

Log dosyası repo dışında, çünkü `user_data/` izinleri konteynere ait olabilir.

## 12. Doğrulama

- [ ] `python3 scripts/health.py` ve `python3 scripts/health.py --service forward-adx20`: konteyner çalışıyor, 0 "other" hata
- [ ] `docker compose --profile forward logs --tail 50 | grep -iE "strategy|dry run|error"`: "Dry run is enabled", doğru strateji adı
- [ ] İşlem sayıları Mac'teki son durumla aynı (geçmiş taşındı)
- [ ] 24 saat sonra `Faz 0: PASS`

## Sonra

- [ ] GDELT'i sunucu IP'sinden bir kez dene (`deploy/MIGRATION.md`, "Sunucuda tekrar denenecek"). Çalışsa bile haber denemesi için Kaan'ın onayı gerekir: denemeler donduruldu
- [ ] Kod güncelleme: `git pull`, `docker compose up -d`, `python3 scripts/health.py`

## Geri dönüş

Sunucuda `docker compose --profile forward down`, veritabanlarını Mac'e `scp`, Mac'te botları başlat. Veritabanı her an tek yerde çalıştığı için hiçbir şey kaybolmaz.

## Anlaman gerekenler

- **Sıra önemli.** Log ayarı botlardan önce, `.env` ve veritabanı preflight'tan önce gelir.
- **Çok katmanlı güvenlik.** SSH anahtarı, 127.0.0.1 bağlaması ve `.env` izni birbirinden bağımsız korur.
- **Kayıt tutmak uyarmak değildir.** Cron kaydeder; bakan yoksa bot günlerce ölü kalabilir.

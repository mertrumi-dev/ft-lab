# ft-lab

Freqtrade tabanlı kişisel kripto trading botu. **Sadece sahte parayla** (dry-run / demo) çalışır.
Proje kuralları: [CLAUDE.md](CLAUDE.md). Öğretici notlar: [docs/learn/](docs/learn/). Yol haritası: [docs/roadmap.md](docs/roadmap.md).

## Kurulum (macOS, Apple Silicon)

Bir kere yapılır.

1. **Docker Desktop** kur: https://www.docker.com/products/docker-desktop → "Download for Mac – Apple Silicon". Aç, üst menüde balina ikonu "running" olana kadar bekle.
2. **Homebrew** yoksa kur (Mac için paket yöneticisi): https://brew.sh sayfasındaki tek satırı Terminal'e yapıştır.
3. **GitHub CLI** kur ve giriş yap:
   ```bash
   brew install gh
   gh auth login        # GitHub.com → HTTPS → Login with a web browser
   ```
4. Repoyu indir:
   ```bash
   cd ~
   gh repo clone mertrumi-dev/ft-lab
   cd ft-lab
   ```
5. `.env` dosyasını oluştur ve doldur:
   ```bash
   cp .env.example .env
   openssl rand -hex 32     # çıkan değeri JWT_SECRET_KEY'e yapıştır
   openssl rand -hex 32     # çıkan değeri WS_TOKEN'a yapıştır
   open -e .env             # TextEdit'te açar; şifreni de değiştir, kaydet
   ```
6. Testleri çalıştır (Docker içinde; Mac'in python3'ünde pandas/freqtrade yok, gerekmez de):
   ```bash
   export PATH=$HOME/.docker/bin:$PATH     # Docker Desktop'ın docker komutu (zsh'de ~/.zshrc'ye ekle)
   python3 scripts/ft.py test --build      # ilk sefer: test image'ını tests/Dockerfile'dan kurar
   python3 scripts/ft.py test              # sonrakiler
   ```
   Hepsi `passed` olmalı (2026-11-01: 444). İsteğe bağlı: `requirements-dev.txt` ile bir `.venv` kurup `.venv/bin/python -m pytest` da çalışır.

## Botu çalıştırma

```bash
docker compose pull          # Freqtrade image'ını indir (ilk sefer birkaç dakika)
docker compose up -d         # botu arka planda başlat
docker compose logs -f       # logları izle; Ctrl+C sadece izlemeyi bırakır
```

Tarayıcıda **http://127.0.0.1:8080** aç → `.env`'deki kullanıcı adı ve şifreyle giriş yap (FreqUI).

Durdurmak için: `docker compose down`.

## Ölçme (Faz 1)

```bash
python3 scripts/splits.py                      # veri dilimlerini göster
python3 scripts/ft.py download                 # geçmiş fiyatları indir (bir kere)
python3 scripts/ft.py benchmark --slice train     # al-tut sonucu
python3 scripts/ft.py backtest --slice train --strategy all   # tüm stratejiler
python3 scripts/ft.py report --slice train     # kısa tablo: stratejiler vs al-tut
```
Test dilimi (`--slice test`) her strateji için sadece bir kere, en sonda. Açıklama: [docs/learn/02-olcme-araclari.md](docs/learn/02-olcme-araclari.md).

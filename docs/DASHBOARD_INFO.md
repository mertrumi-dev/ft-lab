---
project: ft-lab
repo: mertrumi-dev/ft-lab
type: bot
language: Python 3 + Freqtrade 2026.10 (Docker image `freqtradeorg/freqtrade:2026.10`), ccxt (minibot), pandas (sadece backtest/araştırma scriptleri); izleme scriptleri (`scripts/health.py`) sadece standart kütüphane (sqlite3, subprocess)
runs_on: bilgisayar (Kaan'ın Mac'i, macOS M2). Sunucuya taşıma planlı ama yapılmadı (`deploy/MIGRATION.md`); sunucunun işletim sistemi BİLİNMİYOR
run_method: Docker Compose (`restart: unless-stopped`)
status: durdu (botlar 2026-11-02'den beri kapalı; proje 2026-11-06'dan beri askıda)
---

## 1. Ne yapıyor
Freqtrade tabanlı, **sadece sahte parayla (dry-run)** çalışan spot kripto trading botu. Binance'ten 1 saatlik fiyatları okur, 5 coinde (BTC, ETH, SOL, BNB, XRP / USDT) trend kuralına göre sanal alım-satım yapar; başlangıç sanal cüzdanı 1000 USDT. İki bot var: ana bot `TrendEmaVolTarget` ve yan yana ileriye dönük test botu `TrendEmaVolTargetAdx`. Borsa anahtarı yok, gerçek emir gönderilmez.

## 2. Nerede ve nasıl çalışıyor
- **Klasör:** Mac'te `~/ft-lab` (repo kökü). `docker` Mac'te PATH'te değil: önce `export PATH=$HOME/.docker/bin:$PATH`.
- **Servisler** (`docker-compose.yml`):

| Compose servisi | Container adı | Strateji | Port (sadece 127.0.0.1) | Log dosyası |
|---|---|---|---|---|
| `freqtrade` | `ft-lab` | `TrendEmaVolTarget` | 8080 | `user_data/logs/freqtrade.log` |
| `forward-adx20` (profile `forward`) | `ft-lab-fwd-adx20` | `TrendEmaVolTargetAdx` | 8081 | `user_data/logs/forward-adx20.log` |

- **Başlatma:** `docker compose up -d freqtrade` ve `docker compose --profile forward up -d forward-adx20`
- **Durdurma:** `docker compose --profile forward down`
- **Yeniden başlatma:** `docker compose restart freqtrade` (veya `forward-adx20`). Docker kendisi de `unless-stopped` ile çöküşten sonra yeniden başlatır; Mac uyursa botlar durur.
- **Canlı log:** `docker compose logs -f freqtrade`
- **Ayarlar:** `user_data/config/config.json` (+ ikinci bot için `user_data/config/forward-adx20.json`)
- Sunucu kurulumu ve taşıma: `deploy/README.md`, `deploy/MIGRATION.md`, `docs/deploy-checklist.md`, ön kontrol `python3 deploy/preflight.py`.

## 3. Sakladığı veriler
- **SQLite (Freqtrade'in kendi şeması):**
  - Ana bot: `user_data/tradesv3.voltarget.dryrun.sqlite`
  - İleri test botu: `user_data/tradesv3.adx20.dryrun.sqlite`
  - Eski TrendEma botu (sadece analiz): `user_data/tradesv3.dryrun.sqlite`
  - Önemli tablo: `trades` (alanlar: `id`, `pair`, `is_open`, `open_date`, `close_date`, `open_rate`, `close_rate`, `stake_amount`, `close_profit`, `close_profit_abs`, `exit_reason`, `strategy`). Ayrıca `orders` (emirler). `health.py` sadece `is_open` ve `close_profit_abs` okuyor.
  - `*.sqlite` git'e girmez (`.gitignore`).
- **Loglar:** `user_data/logs/*.log` (git'e girmez).
- **Mini bot (kağıt üstünde):** `minibot/state.json`, demo için `minibot/state.demo.json` (JSON, git'e girmez). Şema: BİLİNMİYOR (bu dosyada incelenmedi).
- **Günlük raporlar (git'te):** `docs/fresh/YYYY-MM-DD.md`, `docs/fresh/latest.md`, `docs/fresh/breadth.csv` (sütunlar: `date,n_coins,breadth,n_in_trend,n_entry_now,BTC,ETH,SOL,BNB,XRP`), `docs/fresh/preregistered.csv`, `docs/fresh/ai-scores.csv`. Son rapor: 2026-11-04.

## 4. Dashboard'da gösterilebilecek canlı bilgiler

| Bilgi | Şu an nereden okunur | Ne sıklıkla değişir |
|---|---|---|
| Çalışıyor mu | `docker compose --profile forward ps` (health.py `container_status`) veya REST `GET /api/v1/ping` | anlık |
| Son aktivite (heartbeat) | Logda `Bot heartbeat` satırı (health.py 5 dakikadan eskiyse FAIL der) | ~1 dakikada bir |
| Son 24 saat hata sayısı (ağ / diğer) | `python3 scripts/health.py` (logu `docker compose logs` ile okur) | saniyeler-saatler |
| Açık / kapanmış işlem sayısı | `trades` tablosu: `is_open = 1` / `is_open = 0`; REST `GET /api/v1/count`, `/api/v1/status` | 1h mum kapanışında (saat başı) |
| Gerçekleşen kâr/zarar (USDT) | `sum(close_profit_abs)` where `is_open = 0`; REST `GET /api/v1/profit` | işlem kapanınca |
| Kill switch'e yakınlık (zirveden düşüş, sınır %20) | health.py `drawdown_from_peak` (trades tablosundan hesap) | işlem kapanınca |
| Faz 0 kararı (24 saat temiz çalışma) | health.py çıktısı | saatlik |
| Hangi strateji / dry-run mı | logda `Dry run is enabled` + strateji adı; REST `GET /api/v1/show_config` | başlatmada |
| Günlük rapor özeti, coinlerin trend durumu | `docs/fresh/latest.md`, `docs/fresh/breadth.csv` (`scripts/daily.py` yazar, elle çalıştırılır) | günde bir (askıda: 2026-11-04'ten beri yok) |

## 5. Şu an dışarıya veri veriyor mu?
**Dışarıya: yok.** Webhook, heartbeat dosyası veya merkezi bir adrese gönderim yok. Telegram kapalı (`config.json` → `telegram.enabled: false`).

Yerel olarak: Freqtrade'in kendi REST API'si + FreqUI açık (`api_server.enabled: true`), ama portlar sadece `127.0.0.1:8080` / `127.0.0.1:8081` (dışarıdan erişilemez, bu bilerek böyle). `GET /api/v1/ping` girişsiz `{"status":"pong"}` döner; diğer uçlar kullanıcı adı/şifre veya JWT ister (değerler `.env`'de). Botlar kapalı olduğu için şu an hiçbiri yanıt vermez.

## 6. Dashboard'a bağlamak için önerin
**En az değişiklik: bot koduna dokunmayan, ayrı bir "nabız" scripti.** `scripts/` altına küçük bir script (veya `health.py`'ye `--json` çıktısı): her 30-60 saniyede bir, Freqtrade'in yerel REST API'sine (`127.0.0.1:8080` ve `:8081`, `/api/v1/ping`, `/count`, `/profit`) sorar ya da SQLite'ı salt okunur açar, sonucu merkezi dashboard adresine HTTPS POST ile yollar (çalışıyor mu, son heartbeat, açık/kapanmış işlem, kâr/zarar, zirveden düşüş, hata sayısı).
- **Neden bu:** Strateji ve config değişmez; Freqtrade çekirdeğine dokunulmaz (proje kuralı). Portu dışarıya açmaya gerek kalmaz, veri içeriden dışarıya gider.
- **Gereken:** dashboard adresi + token için `.env`'e iki yeni değişken (isim önerisi: `DASHBOARD_URL`, `DASHBOARD_TOKEN`), bir compose servisi veya cron/launchd girişi.
- **Riskler:** (1) FreqUI şifresini nabız scriptine vermek gerekir; SQLite'ı salt okunur okumak bunu önler. (2) Token `.env` dışına sızmamalı (`tests/test_config_safety.py` sadece config.json'ı kontrol ediyor). (3) Mac uyurken nabız da durur; "nabız gelmedi" = "bot veya Mac durdu" diye yorumlanmalı. (4) Proje askıda: kurmak için Kaan'ın onayı gerekir.
- Alternatif: Freqtrade'in yerleşik `webhook` ayarı (config.json'a ekleme). İşlem açılış/kapanışında POST atar ama periyodik nabız göndermez ve config değişikliği ister.

## 7. Bağımlılıklar ve erişim
- **Dış servisler:** Binance (sadece herkese açık fiyat verisi; anahtar yok). Telegram: planlı (Faz 5), şu an kapalı. GDELT haber API'si: sadece araştırma, Mac IP'sinden HTTP 429 alıyor. Binance demo (Faz 5, `minibot/demo.py`): henüz kullanılmadı.
- **VPN/Tailscale:** kodda/configte yok. FreqUI'ye sadece aynı bilgisayardan erişilir; uzaktan erişim yöntemi BİLİNMİYOR (kurulmadı).
- **Env değişkenleri** (`.env`, şablon `.env.example`):
  - `FREQTRADE__API_SERVER__USERNAME`
  - `FREQTRADE__API_SERVER__PASSWORD`
  - `FREQTRADE__API_SERVER__JWT_SECRET_KEY`
  - `FREQTRADE__API_SERVER__WS_TOKEN`
  - `FREQTRADE__EXCHANGE__KEY`, `FREQTRADE__EXCHANGE__SECRET` (bilerek boş; Faz 5'e kadar kullanılmaz)
  - `FTLAB_DEMO_KEY`, `FTLAB_DEMO_SECRET` (sadece `minibot/demo.py`, Binance demo hesabı; tanımlı mı BİLİNMİYOR)

## 8. Bilinen sorunlar
- Proje 2026-11-06'dan beri askıda; botlar 2026-11-02'den beri kapalı. Son günlük rapor (2026-11-04): "not running", Faz 0 "FAIL: no heartbeat in the log".
- Mac uyuyunca (özellikle pilde) botlar ve heartbeat durur; Faz 0'ın 24 saat sayacı bu yüzden tamamlanamadı. Kalıcı çözüm sunucuya taşıma (yapılmadı).
- Dry-run'da -%8 stopu borsada değil, botun kendisi izliyor; bot durursa stop da izlenmez (`deploy/MIGRATION.md`).
- Ana strateji final testte FAIL verdi (-%19,9, kill switch tetiklendi); bot sadece öğrenme/ölçüm amaçlı çalışıyor (`docs/results.md`, `docs/journal.md`).
- Kill switch tetiklenirse bot yeni alım yapmaz ve kendiliğinden açılmaz; yeniden başlatma adımları `docs/proposals/kill-switch-restart.md`.

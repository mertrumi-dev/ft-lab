# Dashboard bilgi dosyası (ft-lab)

Bu repodaki çalışan/çalışacak ürünler. Hepsi **sahte parayla** (dry-run / kağıt üstünde); gerçek emir yok, borsa anahtarı yok.

Ürün olmayanlar (dashboard'a bağlanacak bir şey yok):
- **Kıyas botları** (haftalık DCA, grid, DCA bot, NFI X8, TSMOM; `python3 scripts/ft.py bots`): sadece backtest'te çalışan karşılaştırmalar, sürekli çalışan süreç değil.
- **Telegram:** kodda/configte kapalı (`config.json` → `telegram.enabled: false`), Faz 5'te planlı.

Genel durum: botlar 2026-11-02'den beri kapalı, proje 2026-11-06'dan beri askıda. Sunucuya taşıma planlı ama yapılmadı (`deploy/MIGRATION.md`).

---

---
product: ft-lab ana bot (TrendEmaVolTarget)
repo: mertrumi-dev/ft-lab
type: diğer (kripto trading botu, dry-run)
language: Python 3 + Freqtrade 2026.10 (Docker image `freqtradeorg/freqtrade:2026.10`); izleme scripti `scripts/health.py` sadece standart kütüphane (sqlite3, subprocess)
runs_on: bilgisayar (Kaan'ın Mac'i, macOS M2)
run_method: Docker Compose (`restart: unless-stopped`)
status: durdu
---

## 1. Ürün ne yapıyor
Binance'ten 1 saatlik fiyatları okur, 5 coinde (BTC, ETH, SOL, BNB, XRP / USDT) trend kuralına göre sanal alım-satım yapar (spot, başlangıç sanal cüzdanı 1000 USDT, en fazla 3 açık işlem). Kullanan: sadece Kaan (öğrenme ve ileriye dönük ölçüm).

## 2. Nerede ve nasıl çalışıyor
- Klasör: Mac'te `~/ft-lab`. `docker` Mac'te PATH'te değil: `export PATH=$HOME/.docker/bin:$PATH`.
- Compose servisi `freqtrade`, container adı `ft-lab`, strateji `TrendEmaVolTarget` (`user_data/strategies/sizing.py`).
- Başlat: `docker compose up -d freqtrade` · Durdur: `docker compose --profile forward down` · Yeniden başlat: `docker compose restart freqtrade` (Docker çöküşte kendisi de yeniden başlatır; Mac uyursa bot durur).
- Log: `user_data/logs/freqtrade.log`; canlı: `docker compose logs -f freqtrade`.
- Ayar: `user_data/config/config.json`. FreqUI / REST API: `127.0.0.1:8080` (sadece aynı bilgisayardan).

## 3. Sakladığı veriler
- SQLite (Freqtrade şeması): `user_data/tradesv3.voltarget.dryrun.sqlite` (eski TrendEma botu, sadece analiz: `user_data/tradesv3.dryrun.sqlite`).
- Tablo `trades`: `id`, `pair`, `is_open`, `open_date`, `close_date`, `open_rate`, `close_rate`, `stake_amount`, `close_profit`, `close_profit_abs`, `exit_reason`, `strategy`. Tablo `orders`: emirler.
- `*.sqlite` ve loglar git'e girmez (`.gitignore`).

## 4. Dashboard'da gösterilebilecek canlı bilgiler

| Bilgi | Şu an nereden okunur | Sıklık |
|---|---|---|
| Çalışıyor mu | `docker compose --profile forward ps` (health.py `container_status`) veya REST `GET /api/v1/ping` | anlık |
| Son aktivite | logdaki `Bot heartbeat` satırı (health.py 5 dk'dan eskiyse FAIL der) | ~1 dk |
| Son 24 saat hata sayısı (ağ / diğer) | `python3 scripts/health.py` (logu `docker compose logs` ile okur) | anlık |
| Açık / kapanmış işlem | `trades` → `is_open = 1` / `0`; REST `GET /api/v1/count`, `/api/v1/status` | saat başı (1h mum) |
| Gerçekleşen kâr/zarar (USDT) | `sum(close_profit_abs)` where `is_open = 0`; REST `GET /api/v1/profit` | işlem kapanınca |
| Kill switch'e yakınlık (zirveden düşüş, sınır %20) | health.py `drawdown_from_peak` (trades'ten hesap) | işlem kapanınca |
| Faz 0 kararı (24 saat temiz çalışma) | health.py çıktısı | saatlik |
| Strateji adı, dry-run mı | logda `Dry run is enabled`; REST `GET /api/v1/show_config` | başlatmada |

## 5. Şu an dışarıya veri veriyor mu?
**Dışarıya: yok** (webhook, heartbeat dosyası, merkezi POST yok). Yerelde Freqtrade REST API + FreqUI açık ama sadece `127.0.0.1:8080`. `GET /api/v1/ping` girişsiz `{"status":"pong"}` döner; diğer uçlar kullanıcı adı/şifre veya JWT ister (`.env`). Bot kapalı olduğu için şu an yanıt yok.

## 6. Dashboard'a bağlamak için önerin
Bot koduna dokunmayan ayrı bir **nabız scripti** (`scripts/` altında, veya `health.py`'ye `--json` çıktısı): her 30-60 saniyede SQLite'ı salt okunur açar + container durumuna bakar, sonucu merkezi adrese HTTPS POST ile yollar (çalışıyor mu, son heartbeat, açık/kapanmış işlem, kâr/zarar, zirveden düşüş, hata sayısı). Aynı script ileri test botunu da kapsar.
- Neden: strateji/config değişmez, Freqtrade çekirdeğine dokunulmaz (proje kuralı), port dışarı açılmaz; veri içeriden dışarı gider.
- Gereken: `.env`'e iki yeni değişken (öneri: `DASHBOARD_URL`, `DASHBOARD_TOKEN`), çalıştırmak için bir compose servisi veya cron (sunucu için zaten saatlik health cron'u planlı: `docs/deploy-checklist.md` §11).
- Riskler: REST API kullanılırsa FreqUI şifresi scripte gerekir (SQLite okumak bunu önler); token `.env` dışına sızmamalı (`tests/test_config_safety.py` sadece `config.json`'ı kontrol ediyor); Mac uyurken nabız da durur ("nabız yok" = bot veya Mac durdu); proje askıda, kurulum Kaan'ın onayıyla.
- Alternatif: Freqtrade'in yerleşik `webhook` ayarı. Sadece işlem açılış/kapanışında POST atar, periyodik nabız göndermez, config değişikliği ister.

## 7. Bağımlılıklar ve erişim
- Dış servis: Binance (herkese açık fiyat verisi, anahtarsız).
- VPN/Tailscale: kodda/configte yok. Uzaktan erişim yöntemi BİLİNMİYOR (kurulmadı).
- Env değişkenleri (`.env`, şablon `.env.example`): `FREQTRADE__API_SERVER__USERNAME`, `FREQTRADE__API_SERVER__PASSWORD`, `FREQTRADE__API_SERVER__JWT_SECRET_KEY`, `FREQTRADE__API_SERVER__WS_TOKEN`; `FREQTRADE__EXCHANGE__KEY`, `FREQTRADE__EXCHANGE__SECRET` (bilerek boş, Faz 5'e kadar).

## 8. Bilinen sorunlar
- 2026-11-02'den beri kapalı. Son günlük rapor (2026-11-04, `docs/fresh/latest.md`): "not running", Faz 0 "FAIL: no heartbeat in the log".
- Mac uyuyunca (özellikle pilde) bot ve heartbeat durur; Faz 0'ın 24 saat sayacı bu yüzden tamamlanamadı. Kalıcı çözüm sunucu (yapılmadı).
- -%8 stopu borsada değil, botun kendisi izliyor; bot durursa stop izlenmez (`deploy/MIGRATION.md`).
- Strateji final testte FAIL verdi (-%19,9, kill switch tetiklendi; `docs/results.md`). Bot sadece ölçüm için.
- Kill switch tetiklenirse bot yeni alım yapmaz ve kendiliğinden açılmaz: `docs/proposals/kill-switch-restart.md`.

---

---
product: ft-lab ileri test botu (TrendEmaVolTargetAdx)
repo: mertrumi-dev/ft-lab
type: diğer (kripto trading botu, dry-run)
language: Python 3 + Freqtrade 2026.10 (ana botla aynı image)
runs_on: bilgisayar (Kaan'ın Mac'i, macOS M2)
run_method: Docker Compose, profile `forward` (`restart: unless-stopped`)
status: durdu
---

## 1. Ürün ne yapıyor
Ana botun yanında, aynı coinler ve aynı risk kurallarıyla ikinci bir sanal cüzdanda `TrendEmaVolTargetAdx` kuralını oynar. Amaç sadece yeni fiyatlarda iki kuralı yan yana kıyaslamak. Kullanan: sadece Kaan.

## 2. Nerede ve nasıl çalışıyor
- Compose servisi `forward-adx20`, container `ft-lab-fwd-adx20`. Düz `docker compose up -d` bunu başlatmaz.
- Başlat: `docker compose --profile forward up -d forward-adx20` · Yeniden başlat: `docker compose --profile forward restart forward-adx20`.
- Log: `user_data/logs/forward-adx20.log`. Ayar: `config.json` + `user_data/config/forward-adx20.json`. FreqUI / REST: `127.0.0.1:8081`.

## 3. Sakladığı veriler
SQLite `user_data/tradesv3.adx20.dryrun.sqlite`; tablolar ana botla aynı (`trades`, `orders`).

## 4. Dashboard'da gösterilebilecek canlı bilgiler
Ana botla aynı liste; kaynak `python3 scripts/health.py --service forward-adx20`, kendi DB'si ve `:8081`. Ek: iki botun kâr/zarar ve işlem sayısı yan yana.

## 5. Şu an dışarıya veri veriyor mu?
Yok. Yerelde sadece `127.0.0.1:8081` REST API.

## 6. Dashboard'a bağlamak için önerin
Ana botun nabız scripti ikinci servis olarak bunu da okusun (`health.py`'deki `SERVICES` sözlüğü zaten iki botu tanıyor). Ek risk yok.

## 7. Bağımlılıklar ve erişim
Ana botla aynı (Binance açık veri, aynı `.env` değişkenleri).

## 8. Bilinen sorunlar
Ana botla aynı (Mac uykusu, kapalı). Kural ayrılmış hakemde PASS, train'de FAIL verdi; üstünlüğü kanıtlı değil (DSR 0,34).

---

---
product: ft-lab mini bot
repo: mertrumi-dev/ft-lab
type: diğer (sıfırdan yazılmış kağıt üstünde trading botu)
language: Python 3 + ccxt
runs_on: bilgisayar (Kaan'ın Mac'i), Docker içinde
run_method: elle (`python3 scripts/ft.py minibot`, `docker run --rm` ile)
status: geliştirmede (şu an çalışıp çalışmadığı BİLİNMİYOR; proje askıda olduğu için büyük ihtimalle kapalı, doğrulanmadı)
---

## 1. Ürün ne yapıyor
Freqtrade olmadan, ccxt ile yazılmış küçük bot (Faz 4). Saatte bir Binance'ten açık fiyatları çeker, ana botla aynı VolTarget kuralını kağıt üstünde uygular. Kullanan: Kaan (öğrenme).

## 2. Nerede ve nasıl çalışıyor
- Kod: `minibot/` (`bot.py`, `paper.py`, `signals.py`, `demo.py`).
- Tek tur: `python3 scripts/ft.py minibot --once`; sürekli (saatte bir tur): `python3 scripts/ft.py minibot [--rule voltarget|trendema]`.
- Log dosyası yok; her turda ekrana `cash`, açık pozisyonlar, kapanmış işlem sayısı yazar. Servis/otomatik yeniden başlatma yok.

## 3. Sakladığı veriler
JSON `minibot/state.json` (demo modu: `minibot/state.demo.json`), git'e girmez. Alanlar: `cash`, `start`, `positions` (coin → `entry`, `amount`, …), `closed` (kapanmış işlemler listesi), `peak`, `realized`.

## 4. Dashboard'da gösterilebilecek canlı bilgiler
- Nakit, açık pozisyonlar, kapanmış işlem sayısı: `state.json` → `cash`, `positions`, `len(closed)`; saatte bir değişir.
- Zirveden düşüş (kill switch %20): `peak` ve `realized` alanlarından.
- Son aktivite: `state.json` dosyasının değişme zamanı (saatte bir yazılır).

## 5. Şu an dışarıya veri veriyor mu?
Yok.

## 6. Dashboard'a bağlamak için önerin
Aynı nabız scripti `minibot/state.json`'ı okuyup gönderebilir; mini botun koduna dokunmak gerekmez. Risk: dosya `state.tmp` üzerinden atomik yazılıyor (`save_state`), okuma güvenli. Sürekli çalışması için önce bir servis haline getirilmesi gerekir (bu ayrı bir iş).

## 7. Bağımlılıklar ve erişim
Binance açık veri. Demo modu (`--demo`, Faz 5, henüz kullanılmadı): `FTLAB_DEMO_KEY`, `FTLAB_DEMO_SECRET` (sadece Binance demo hesabı; tanımlı mı BİLİNMİYOR).

## 8. Bilinen sorunlar
Servis olarak tanımlı değil; terminal kapanınca durur.

---

---
product: ft-lab günlük rapor (daily.py + AI grafik yorumları)
repo: mertrumi-dev/ft-lab
type: otomasyon
language: Python 3 (standart kütüphane; işi `scripts/ft.py` üzerinden Docker içindeki Freqtrade'e yaptırır)
runs_on: bilgisayar (Kaan'ın Mac'i)
run_method: elle (`python3 scripts/daily.py`, 00:00 UTC sonrası; Mac'te cron/launchd tanımı repoda yok)
status: durdu (son rapor 2026-11-04)
---

## 1. Ürün ne yapıyor
Günde bir: yeni mumları indirir, adayları ve kıyas botlarını "taze" veride (testten sonraki gerçek fiyatlar) backtest eder, bot sağlığını ekler ve sade Türkçe bir rapor yazar. Ayrıca her gün 5 coin için 7 günlük yön tahmini (AI yorumu) kaydedilir ve 7 gün sonra puanlanır; bota bağlı değil. Kullanan: Kaan.

## 2. Nerede ve nasıl çalışıyor
- Komut: `python3 scripts/daily.py` (`--no-download` ile indirmesiz). Puanlama: `python3 scripts/ft.py ai-score`.
- AI yorumları `docs/fresh/ai-views.md`'ye Claude tarafından yazılıyordu (kod değil); otomatik üretimi BİLİNMİYOR.
- Log dosyası yok; çıktı rapor dosyalarına yazılır.

## 3. Sakladığı veriler (git'te)
- `docs/fresh/YYYY-MM-DD.md`, `docs/fresh/report-YYYY-MM-DD.md`, `docs/fresh/latest.md`
- `docs/fresh/breadth.csv`: `date,n_coins,breadth,n_in_trend,n_entry_now,BTC,ETH,SOL,BNB,XRP`
- `docs/fresh/ai-scores.csv`: `date,coin,base_close,call,confidence,due,close_7d,move,actual,hit`
- `docs/fresh/preregistered.csv` (ön kayıtlı taze-veri satırları)

## 4. Dashboard'da gösterilebilecek canlı bilgiler
- Son rapor tarihi ve özeti: `docs/fresh/latest.md` (günde bir).
- Piyasa genişliği (havuzdaki coinlerin yüzde kaçı EMA200 üstünde): `breadth.csv` son satır (günde bir).
- AI tahmin isabeti: `ai-scores.csv` → `hit` sütunu (7 günde bir dolar; şu an 0 puanlanmış tahmin).

## 5. Şu an dışarıya veri veriyor mu?
Yok (sadece git'e commit edilen dosyalar).

## 6. Dashboard'a bağlamak için önerin
Dashboard repodaki `docs/fresh/latest.md` ve CSV'leri GitHub üzerinden okuyabilir; ürüne hiç değişiklik gerekmez. Dezavantaj: sadece push edildiğinde güncellenir (günde bir), repo private olduğu için okuma tokenı gerekir.

## 7. Bağımlılıklar ve erişim
Binance açık veri (indirme), Docker. GDELT haber API'si sadece araştırmada denendi, Mac IP'sinden HTTP 429 alıyor. Env değişkeni kullanmıyor.

## 8. Bilinen sorunlar
- Elle çalıştırılıyor; zamanlayıcı yok. 2026-11-04'ten beri rapor yok, AI tahmin puanlaması (ilk: 2026-11-08) yapılmadı.

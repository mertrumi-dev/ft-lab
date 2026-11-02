# Öğretici kart 34: Binance demo anahtarı nasıl oluşturulur (Faz 5)

Bu kart sadece **Binance Demo Trading** (sahte para, gerçek emir defteri) içindir. Gerçek hesap anahtarı **asla** oluşturulmaz, botun hiçbir yerine girilmez.

Kural: Anahtarı **sen** oluşturursun, **sen** `.env` dosyasına yazarsın. Claude anahtarı görmez, istemez, `.env`'i açmaz ve okumaz. Anahtarı sohbete, Telegram'a, e-postaya ya da ekran görüntüsüne asla koyma.

## Neden demo?

Demo Mode, Binance'in gerçek borsasıyla aynı özelliklere sahip ama parası sahte. Fiyatlar ve emir defteri gerçeğe çok yakın, birebir aynı değil. Botun emirlerinin gerçekten dolup dolmadığını, ne kadar kaydığını burada ölçeriz (Faz 5, 4 hafta). Binance'in kendi uyarısı: demoda çalışan bir strateji gerçekte çalışmayabilir.

## Adım adım

### 1. Demo hesabına gir

1. Tarayıcıda Binance hesabına giriş yap.
2. **Binance Demo Trading** sayfasına geç (Binance'in resmi demo sayfası). Adres çubuğunda `demo.binance.com` görmelisin.
3. Sayfanın demo olduğundan emin ol: bakiyen sahte bir başlangıç bakiyesi olmalı.

### 2. API anahtarı oluştur

1. Sağ üstteki hesap simgesi → **API Management** (API Yönetimi).
2. **Create API** → bir isim ver: `ft-lab-demo`.
3. Güvenlik doğrulamasını tamamla.

### 3. İzinleri ayarla (en önemli adım)

Anahtar oluşunca **Edit restrictions** (kısıtlamaları düzenle):

| İzin | Ayar | Neden |
|---|---|---|
| Enable Reading (okuma) | **açık** | bakiye ve emir durumunu görmek için |
| Enable Spot & Margin Trading | **açık** (sadece spot kullanılacak) | bot emir verebilsin |
| Enable Withdrawals (para çekme) | **KAPALI** (görünürse) | bot asla para çekmez |
| Futures / Margin / diğer her şey | **kapalı** | kaldıraç yok, sadece spot |
| IP kısıtlaması | **Restrict access to trusted IPs only**, Mac'inin dış IP adresi | anahtar çalınsa bile başka yerden kullanılamaz |

Dış IP adresini öğrenmek için Mac'te Terminal'e yaz:

```bash
curl -s https://ifconfig.me
```

Not: Ev internetinde IP adresi bazen değişir. Değişirse bot "IP not allowed" hatası verir; o zaman Binance'te listeye yeni IP'yi eklersin. Sunucuya geçince sunucunun sabit IP'si yazılır.

### 4. Anahtarı `.env` dosyasına yaz (sadece sen)

Binance anahtarı ve gizli anahtarı (secret) **sadece bir kez** gösterir. Kopyala ve hemen:

1. Terminal'de dosyayı metin düzenleyiciyle aç:

   ```bash
   open -e ~/ft-lab/.env
   ```

2. Dosyanın sonuna iki satır ekle (tırnak yok, boşluk yok):

   ```
   FTLAB_DEMO_KEY=buraya_api_key
   FTLAB_DEMO_SECRET=buraya_secret_key
   ```

3. Kaydet, kapat. Dosya izinlerini kontrol et (sadece sen okuyabil):

   ```bash
   chmod 600 ~/ft-lab/.env
   ```

`.env` GitHub'a hiç gitmez (`.gitignore`'da). `cat .env` gibi komutlarla ekrana yazdırma.

### 5. Bana sadece "yazdım" de

Anahtarı değil, sadece "demo anahtarını .env'e yazdım" de. Ben şunları yaparım:

1. `python3 deploy/preflight.py`: anahtarın dosyalara sızmadığını, sadece `demo-*.binance.com` adreslerinin kullanıldığını kontrol eder.
2. Mini bot `--demo` modunda başlarken kod kendisi kontrol eder: borsa adreslerinden biri bile demo değilse **hiçbir şey yapmadan durur** (minibot/demo.py, `assert_demo_urls`). Bu kontrol gerçek ccxt sürümüyle test edildi (ccxt 4.5.90: demo modunda bütün adresler `demo-api` / `demo-fapi` / `demo-dapi.binance.com`).
3. Faz 5 için senin ayrıca "başla" demen gerekir.

## Bir şey ters giderse

- Anahtarın başkasının eline geçtiğinden şüphelenirsen: Binance → API Management → anahtarı **Delete**. Demo olduğu için gerçek para riski yok, ama alışkanlık doğru olsun.
- Yanlışlıkla gerçek hesapta anahtar oluşturduysan: hemen sil ve bana söyle (anahtarı değil, sadece "yanlışlıkla gerçek hesapta oluşturdum, sildim" de).

## Anlaman gerekenler

- **En az yetki ilkesi:** Bir anahtar sadece işini yapmaya yetecek kadar izin almalı. Bot sadece okur ve spot emir verir; para çekme izni hiçbir zaman gerekmez.
- **Sırlar koddan ayrı durur:** Kod GitHub'da herkese açık olabilir; anahtar sadece senin Mac'indeki `.env` dosyasında. Program anahtarı "ortam değişkeni"nden (environment variable) okur, dosyanın içeriği hiçbir yere yazılmaz.
- **İki kat koruma:** IP kısıtlaması (anahtar çalınsa da işe yaramaz) + koddaki demo adres kontrolü (yanlış borsaya bağlanmaz).

## Kaynaklar

- Binance, Demo Mode genel bilgi ve API anahtarı oluşturma: https://developers.binance.com/docs/binance-spot-api-docs/demo-mode/general-info
- Binance SSS, Demo Trading API: https://www.binance.com/en/support/faq/9be58f73e5e14338809e3b705b9687dd
- ccxt Binance, enableDemoTrading: https://docs.ccxt.com/docs/exchanges/binance

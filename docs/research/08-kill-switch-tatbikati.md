# Araştırma 08: Kill switch tatbikatı (2026-11-01)

Amaç: Uydurma (sentetik) bir çöküş senaryosunu **iki bota birden** vermek: Freqtrade backtest'i (kill switch AÇIK) ve mini bot (demo döngüsü, replay ile). Sonra şunları kontrol etmek:

1. Gerçekleşmiş sermaye zirveden %20 düşünce yeni işlem duruyor mu?
2. O anda açık olan işlemlere risk kurallarının dediği oluyor mu? (R13: zorla kapatılmaz, kendi stop'u veya çıkışıyla kapanır.)
3. Bot yeniden başlarsa kill switch açık kalıyor mu?
4. İki bot aynı saatte mi duruyor?

Komut: `python3 scripts/ft.py drill`. Veri `user_data/data/drill/` klasörüne, 2029-2030 tarihli yazılır (gerçek veriyle karışmaz, git'e girmez).

## Senaryo (`scripts/drill.py`)

| Bölüm | Ne oluyor | Beklenen |
|---|---|---|
| Isınma | 75 gün sakin yükseliş | işlem yok (yeni kesişme yok) |
| Çöküş haftası | kısa düşüş, yükseliş (giriş), sonra **5 günde %35 düşüş** | kill switch **tetiklenmemeli** |
| Testere | 30 kez: yükseliş (giriş), sonra tek mumda %20 düşüş (stop), toparlanma | kayıplar birikip %20'ye ulaşınca kill switch **tetiklenmeli** |

Coinler arasında 13 saat kayma var. Neden 13: bir coinin çöküş mumu başka bir coinin giriş mumuna denk gelmesin (aşağıda "aynı mumda yer açma"). 3/5/9/11/13/17 saat denendi; çakışma olmayan ve kill switch'e ulaşan tek değer 13.

## Sonuçlar

| | Freqtrade | Mini bot | Mini bot + yeniden başlatma |
|---|---|---|---|
| İşlem | 145 | 127 | 127 (aynısı) |
| Çöküş haftası | 3 işlem, **+11,86 USDT** | 3 işlem, +11,86 USDT | aynı |
| Kill switch | 2030-04-10 01:00, düşüş %20,1 | 2030-03-21 01:00, düşüş %20,2 | aynı |
| Kill'den sonra giriş | **0** (log: 77 kez "KILL SWITCH ... refused") | **0** | **0** |
| O an açık işlem | 0 | 1 → sonra kendi **stop**'uyla kapandı | aynı |

### 1. Yavaş çöküş kill switch'i tetiklemez; bu tasarım gereği

5 günde %35 düşüşte EMA20, EMA50'yi erken aşağı kesiyor. Bot stop'a gelmeden **sinyalle çıkıyor**: üç işlem toplam +11,86 USDT kârla kapandı. Sert bir düşüşte bile en fazla 3 işlem açık ve her biri sermayenin %1'ini riske ediyor; tek bir çöküş en fazla ~%3 kaybettirir. %20'ye ulaşmak için uzun bir kayıp serisi gerekir (testere bölümü: 91 stop).

### 2. BULUNAN HATA: kill switch tekrar açılabiliyordu (iki botta da)

Kill switch o anki düşüşe bakıyordu (`drawdown_from_peak`). Kill'den önce açılmış işlemler sonradan kârla kapanınca düşüş %20'nin altına iniyor ve **yeni işlemler yeniden başlıyordu**. Mini botta ölçüldü: kill 2030-04-20'de tetiklendi, 04-23'te 3 yeni giriş yapıldı. Freqtrade'in `confirm_trade_entry`'si aynı hesabı kullanıyordu.

Bu, R13'ün yazılı kuralına ("yeni işlem yok, **insan bakana kadar**") aykırıydı.

Düzeltme:
- Freqtrade: `trend_ema.worst_drawdown`. Kill switch, işlem geçmişindeki **en büyük** düşüşe bakar; bir kez %20'ye ulaştıysa açık kalır. Hâlâ sadece işlem geçmişinden hesaplanıyor, yani yeniden başlatma sıfırlamaz. İnsanın sıfırlama yolu aynı: yeni veritabanı.
- Mini bot: `paper.kill_switch_hit` bir kez tetiklenince `kill_switch: true` yazar ve kayıt dosyasında saklar.
- `health.py` ve günlük rapor artık hem "şu an" hem "en kötü" düşüşü gösteriyor; tetiklendiyse "insan bakana kadar" yazıyor.
- Risk sayısı (%20) değişmedi. Kural sadece yazıldığı gibi uygulanır hale geldi; sadece daha az işleme izin verebilir.
- **Çalışan dry-run botu bu kodu bir sonraki yeniden başlatmada alır.** Bu akşamki VolTarget geçişi bu yeniden başlatmadır.

### 3. Yeniden başlatma

Mini bot kill'den 24 saat sonra "durduruldu": durumu `state.demo.json`'a yazıldı, yeni bir süreç sadece dosyayı okuyup devam etti. İşlem listesi birebir aynı, kill switch açık, kill'den sonra giriş yok. Borsadaki stop emirleri borsada kaldığı için yeniden başlatmadan etkilenmiyor.

Freqtrade'de kill switch zaten veritabanındaki kapanmış işlemlerden hesaplanıyor; test (`test_confirm_trade_entry_refuses_after_a_recovered_kill`), geçmişte %21 düşüşten sonra kârla toparlanmış bir hesapta girişin reddedildiğini gösteriyor.

### 4. İki bot aynı saatte duruyor mu? HAYIR (açık konu)

İşlem listeleri kill'den önce ayrışıyor: aynı saatte 118 giriş, sadece Freqtrade'de 27, sadece mini botta 9. Bu yüzden kill zamanları farklı: 03-21'e karşı 04-10.

Bulunanlar:
- **Aynı mumda yer açma (Freqtrade backtest'ine özgü):** Backtest, bir coinin stop'unu mumun içinde işler ve boşalan yere aynı mumun açılış fiyatından başka bir coini sokar. Gerçek zamanda bu imkansız: giriş mumun başında, stop mumun ortasında olur. Canlı dry-run botu da bunu yapmaz. Mini bot gerçeğe uygun davranıyor. 13 saatlik kayma bu çakışmayı senaryodan çıkardı.
- **Çözülmeyen:** 2030-02-04 05:00'te iki bot da XRP için aynı alım sinyalini görüyor (EMA farkı birebir aynı: 0,007989). Freqtrade XRP'yi **tek başına** test edince bu işlemi açıyor, 5 coinle test edince açmıyor. O saatte açık işlem 2 (sınır 3); bekleme süresi, stop freni, kill switch yok; log'da başka ret nedeni yok. Neden, Freqtrade backtest motorunun coinler arası bir etkileşimi (ör. `stake_amount: unlimited` iken işlem başına bakiye hesabı). **Kanıtlanmadı.**
- Gerçek veride (fresh 17/17, validation 217/217) bu ayrışma görülmedi. Ayrışma sadece bütün coinlerin art arda çöktüğü bu aşırı senaryoda çıkıyor.

## Sonraki adım (açık)

- XRP 02-04 farkının kök nedeni: Freqtrade backtest'ini `--export signals` ile koşup reddedilen sinyallerin listesine bakmak, gerekirse cüzdan/bakiye hesabını adım adım izlemek.

## Anlaman gerekenler

- **Tatbikat, gerçek bir hatayı yakaladı.** Kill switch'in "tetiklenip tekrar açılması" ancak tetiklendikten sonra kârla kapanan bir işlem olunca ortaya çıkıyor; normal backtest'lerde görünmüyordu.
- **"Şu anki düşüş" ile "en kötü düşüş" farklı şeyler.** Fren, en kötüsüne bakmalı. Yoksa açık işlemlerin şansı freni kendiliğinden bırakır.
- **Backtest de bir model, gerçeğin kendisi değil.** "Aynı mumda yer açma", backtest'in gerçekte olamayacak bir şeyi yapabildiğini gösteriyor.

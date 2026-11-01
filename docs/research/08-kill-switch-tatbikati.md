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

Coinler arasında 13 saat kayma var. Neden 13: bir coinin çöküş mumu başka bir coinin giriş mumuna denk gelmesin (aşağıda "aynı mumda yer açma"). 3/5/9/11/13/17 saat denendi; çakışma olmayan ve kill switch'e ulaşan tek değer 13. Fiyat seviyeleri gerçekçi (BTC 50.000 ... XRP 1); nedeni aşağıda.

## Sonuçlar (son koşu: gerçekçi fiyat seviyeleri)

| | Freqtrade | Mini bot | Mini bot + yeniden başlatma |
|---|---|---|---|
| İşlem | 129 | 127 | 127 (aynısı) |
| Aynı saatte giriş | 127 ortak; 2 sadece Freqtrade'de, 0 sadece mini botta | | |
| Çöküş haftası | 3 işlem, **+11,82 USDT** | 3 işlem, +11,86 USDT | aynı |
| Kill switch | 2030-03-21 14:00, işlem #127 sonrası, düşüş %20,0 | 2030-03-21 01:00, işlem #126 sonrası, düşüş %20,2 | aynı |
| Kill'den sonra giriş | **0** (log: "KILL SWITCH ... refused") | **0** | **0** |
| O an açık işlem | 2 → sonra kendi çıkışıyla (EMA, stop) | 1 → sonra kendi **stop**'uyla | aynı |

### 1. Yavaş çöküş kill switch'i tetiklemez; bu tasarım gereği

5 günde %35 düşüşte EMA20, EMA50'yi erken aşağı kesiyor. Bot stop'a gelmeden **sinyalle çıkıyor**: üç işlem toplam ~+11,8 USDT kârla kapandı. Sert bir düşüşte bile en fazla 3 işlem açık ve her biri sermayenin %1'ini riske ediyor; tek bir çöküş en fazla ~%3 kaybettirir. %20'ye ulaşmak için uzun bir kayıp serisi gerekir (testere bölümü).

### 2. BULUNAN HATA: kill switch tekrar açılabiliyordu (iki botta da)

Kill switch o anki düşüşe bakıyordu (`drawdown_from_peak`). Kill'den önce açılmış işlemler sonradan kârla kapanınca düşüş %20'nin altına iniyor ve **yeni işlemler yeniden başlıyordu**. Mini botta ölçüldü: kill tetiklendi, 3 gün sonra 3 yeni giriş yapıldı. Freqtrade'in `confirm_trade_entry`'si aynı hesabı kullanıyordu.

Bu, R13'ün yazılı kuralına ("yeni işlem yok, **insan bakana kadar**") aykırıydı.

Düzeltme (commit 5a48527):
- Freqtrade: `trend_ema.worst_drawdown`. Kill switch, işlem geçmişindeki **en büyük** düşüşe bakar; bir kez %20'ye ulaştıysa açık kalır. Hâlâ sadece işlem geçmişinden hesaplanıyor, yani yeniden başlatma sıfırlamaz. İnsanın sıfırlama yolu aynı: yeni veritabanı.
- Mini bot: `paper.kill_switch_hit` bir kez tetiklenince `kill_switch: true` yazar ve kayıt dosyasında saklar.
- `health.py` ve günlük rapor artık hem "şu an" hem "en kötü" düşüşü gösteriyor; tetiklendiyse "insan bakana kadar" yazıyor.
- Risk sayısı (%20) değişmedi. Kural sadece yazıldığı gibi uygulanır hale geldi; sadece daha az işleme izin verebilir.
- Koordinatör inceledi; bu akşamki VolTarget geçişiyle (yeniden başlatma) canlı dry-run botuna geçiyor.

### 3. Yeniden başlatma

Mini bot kill'den 24 saat sonra "durduruldu": durumu `state.demo.json`'a yazıldı, yeni bir süreç sadece dosyayı okuyup devam etti. İşlem listesi birebir aynı, kill switch açık, kill'den sonra giriş yok. Borsadaki stop emirleri borsada kaldığı için yeniden başlatmadan etkilenmiyor.

Freqtrade'de kill switch zaten veritabanındaki kapanmış işlemlerden hesaplanıyor; test (`test_confirm_trade_entry_refuses_after_a_recovered_kill`), geçmişte %21 düşüşten sonra kârla toparlanmış bir hesapta girişin reddedildiğini gösteriyor.

### 4. İki bot aynı saatte mi duruyor? Aynı gün, 13 saat farkla; nedeni ölçüldü

Kill ikisinde de 2030-03-21'de geliyor. Freqtrade'in düşüşü işlem #126'dan sonra **%19,78** (sınırın hemen altında), mini botunki **%20,16**. Bütün dönemde mini bot toplam 4,01 USDT (sermayenin %0,4'ü) daha fazla kaybetti; işlem başına fark ortanca 0,03 USDT. Bu küçük fark, %20 çizgisini bir işlem önce geçmeye yetiyor. Freqtrade'in fazladan 2 işlemi (BTC 02:00, XRP 05:00), henüz %20'nin altındayken yaptığı girişler. Bu bir davranış farkı değil, eşik kenarı etkisi.

Yol boyunca bulunan iki **backtest'e özgü** etki (canlıda olmaz):

- **Aynı mumda yer açma:** Freqtrade'in backtest'i, bir coinin stop'unu mumun içinde işler ve boşalan yere aynı mumun açılış fiyatından başka bir coini sokar. Gerçek zamanda bu imkansız: giriş mumun başında, stop mumun ortasında olur. Canlı dry-run botu da bunu yapmaz. Senaryoda coinler arası 13 saatlik kayma bu çakışmayı önlüyor (3/5/9/11/13/17 denendi).
- **Uydurma fiyat × gerçek borsa limiti (XRP 2030-02-04):** İlk koşuda bütün coinler 100 fiyatından başlıyordu. Backtest gerçek Binance limitlerini kullanır: XRP'de en az 0,1 adet. 440 fiyatında bu, Freqtrade'in hesabıyla **en az 46,20 USDT**'lik emir demek (gerçek fiyat ~2,5'ta 5,53 USDT). Freqtrade'in kuralı: istenen tutar × 1,3 bu minimumun altındaysa işlem **sessizce atlanır**. Backtest'te cüzdan log yazmaz, "reddedilen sinyaller" listesine de girmez (o liste sadece "yer yok" retlerini kaydediyor). VolTarget'in ~34 USDT'lik pozisyonu 34 × 1,3 = 44,2 < 46,2 olduğu için atlandı. XRP tek başına test edilince sermaye daha büyüktü; tutar minimuma yükseltildi (44,20) ve işlem açıldı. Kanıt: Freqtrade'in kendi `get_min_pair_stake_amount` ve `validate_stake_amount` kodu. Çözüm: sahte coinlere gerçekçi fiyat seviyeleri verildi (BTC 50.000, ETH 3.000, SOL 150, BNB 500, XRP 1). Sonra ayrışma 27/9'dan 2/0'a indi.
- **Canlıda olur mu?** Ana 5 coinin gerçek fiyatlarında minimum emir ~5,5 USDT. En oynak durumda bile VolTarget pozisyonu birkaç on USDT olduğu için bu sınıra yaklaşılmıyor. Not: mini botun alt sınırı 10 USDT (`stake < 10` → atla), Freqtrade'in "×1,3 sonra minimuma yükselt" kuralından farklı. Ana 5 coinde bugünkü fiyatlarla bir fark yaratmıyor.

## Anlaman gerekenler

- **Tatbikat, gerçek bir hatayı yakaladı.** Kill switch'in "tetiklenip tekrar açılması" ancak tetiklendikten sonra kârla kapanan bir işlem olunca ortaya çıkıyor; normal backtest'lerde görünmüyordu.
- **"Şu anki düşüş" ile "en kötü düşüş" farklı şeyler.** Fren, en kötüsüne bakmalı. Yoksa açık işlemlerin şansı freni kendiliğinden bırakır.
- **Backtest de bir model, gerçeğin kendisi değil.** "Aynı mumda yer açma", backtest'in gerçekte olamayacak bir şeyi yapabildiğini gösteriyor.
- **Sessiz ret en tehlikelisi.** XRP işlemi hiçbir log ve hiçbir "reddedildi" kaydı bırakmadan atlanıyordu. Bulmak için Freqtrade'in kendi kodunu adım adım okumak gerekti: sinyal var mı (var), yer var mı (var), kilit var mı (yok), tutar geçerli mi (değil).

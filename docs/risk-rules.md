# Risk kural kitabı (v1.1, 2026-10-31)

Botun "ne kadar kaybedebilir" sorusuna verdiği cevaplar. Her kural kodda tanımlı ve `tests/` altında testle kilitli: biri gevşetirse test kırmızı yanar.

Sayılar mantıklı başlangıç değerleri, henüz geçmiş veriyle ölçülmedi. Faz 1-3'te ölçülüp gerekirse değişecek (sadece train/validation verisine bakarak).

| # | Kural | Değer | Nerede | Test |
|---|---|---|---|---|
| **Tek işlem** | | | | |
| R1 | Stoploss: işlem bu kadar zarara düşerse sat | -%8 | `trend_ema.py` `STOPLOSS` | en fazla -%8 |
| R2 | İşlem başına risk: stoploss'a takılınca kaybedilen para | sermayenin %1'i | `RISK_PER_TRADE` | en fazla %1 |
| R3 | Pozisyon boyutu = sermaye × %1 / %8 | sermayenin %12,5'i (1000 USDT'de 125) | `risk_based_stake()` | hesap testi |
| R4 | Tek işlem tavanı | sermayenin %25'i | `MAX_STAKE_RATIO` | en fazla %25 |
| **Portföy** | | | | |
| R5 | Aynı anda açık işlem | en fazla 3 | `config.json` `max_open_trades` | en fazla 3 |
| R6 | Her coinde aynı anda | en fazla 1 işlem | Freqtrade varsayılanı | |
| R7 | Toplam açık risk | en fazla %3 (3 × %1); paranın en az %62'si nakit | R2 × R5 sonucu | |
| **Otomatik fren** | | | | |
| R8 | Soğuma: bir coinde işlem kapanınca o coinde bekle | 2 saat | `protections` CooldownPeriod | var mı |
| R9 | Seri kayıp freni: 24 saatte 3 stoploss | 12 saat tüm işlemler dur | StoplossGuard | var mı |
| **Acil durum** | | | | |
| R13 | Kill switch: gerçekleşmiş sermaye zirveden %20 düştü | yeni işlem yok, insan bakana kadar | `confirm_trade_entry` | en fazla %20 + hesap testi |
| R14 | Bayat veri koruması: son mum 2 saatten eski | o işleme girme | `confirm_trade_entry` | |
| **Sistem** | | | | |
| R15 | Sahte para, sadece spot, sırlar `.env`'de | | config + `.gitignore` | `test_config_safety.py` |
| R16 | Giriş/çıkış limit emir, 10 dk'da dolmazsa iptal; stoploss market emir | | `order_types`, `unfilledtimeout` | |
| R17 | Backtest'te komisyon + kayma | %0,15 | `--fee 0.0015` | Faz 1 |

## v1'den çıkarılanlar (v1.1)

Günlük kayıp limiti (%3 / 24 saat), haftalık kayıp limiti (%10 / 7 gün) ve kötü coin freni (LowProfitPairs) çıkarıldı.

Neden: Aynı anda en fazla 3 × %1 = %3 risk açık olabiliyor. Günlük %3 frenine ulaşmak için üç işlemin aynı gün stoploss olması gerekir; bu durumu R9 (24 saatte 3 stoploss) zaten yakalıyor. Haftalık fren de kill switch ile büyük ölçüde örtüşüyor. Her fren tahminle seçilmiş bir sayı daha demek; fazla ayar, geçmişi ezberleme (overfitting) riskini artırır.

**Açıklama notu (2026-11-02, sayı değişmedi):** R9, Freqtrade'in StoplossGuard korumasıyla uygulanıyor ve bu koruma **sadece stop çıkışlarını** sayıyor; sinyal çıkışıyla (EMA kesişmesi) gelen zararları saymıyor. Yani yukarıdaki "aynı gün üç stoploss" gerekçesi doğru, ama aynı gün üç *sinyal* zararı R9'u tetiklemez. Her zararı sayan sürüm denendi (T113, LossGuard): yeni coinlerde biraz iyileştirdi ama 2018-2020'de büyük trendin başını kaçırdı ve ölçütü geçemedi. Bu yüzden R9 olduğu gibi kalıyor.

Kural: Çıkarılan bir fren ancak backtest "bu boşluk gerçekten zarar ettiriyor" diye gösterirse geri eklenir.

## Başarı ölçütü

Bu risk kurallarıyla sermayenin en fazla ~%37'si piyasada olduğu için, güçlü yükselişte ham getiride al-tut'u geçmek neredeyse imkansız. Bu yüzden başarı risk-ayarlı ölçülür:

1. **Calmar oranı** (yıllık getiri / en büyük düşüş) al-tut'tan yüksek olmalı.
2. **En büyük düşüş (max drawdown)** al-tut'un yarısından az olmalı.
3. **En az 50 işlem** (daha azı istatistiksel olarak anlamsız).

Hepsi önce train/validation verisinde, en sonda bir kere test diliminde.

## Kill switch nasıl sıfırlanır?

Kill switch işlem geçmişinden hesaplanır, bu yüzden bot yeniden başlasa da açık kalır. Bilerek böyle: kötü giden bir botu "restart" ile kandıramazsın. Sıfırlamak için önce nedenini incele (`docs/journal.md`'ye yaz), sonra Claude ile birlikte karar ver.

### R13 eki: kill switch sonrası yeniden başlama (uygulandı 2026-11-01, Kaan değiştirebilir)

Kill switch işlem geçmişindeki **en büyük** düşüşe bakar (`trend_ema.worst_drawdown`): bir kez %20'ye ulaştıysa kendiliğinden açılmaz. Yeniden başlama için:

1. **En az 14 gün** bekleme (kilitlendiği andan itibaren).
2. `docs/journal.md`'de yazılı "KILL SWITCH İNCELEMESİ": ne oldu, kural mı piyasa mı, beklenen aralık, şu anki rejim, teknik hata var mı. Karar Kaan'ın.
3. Sıfırlama prosedürü: eski veritabanı **asla düzenlenmez**; arşive kopyalanır (salt okunur), bot yeni bir veritabanı adıyla (ayrı commit) başlar.

Ayrıntılı kontrol listesi ve gerekçe: `docs/proposals/kill-switch-restart.md`. Bu ek sadece yeniden başlamayı kısıtlar; hiçbir risk sayısı (%20, %1, %8, %25) değişmedi.

### Araştırma backtest'inde kapatma (2026-11-01)

Backtest'te kill switch bir kere tetiklenince dönemin geri kalanında hiç alım olmaz. O zaman sonuç "kural nasıl" değil "kural ilk %20 düşüşe kadar nasıldı" olur (ör. 14 coin testinde TrendEma Temmuz 2021'de durdu).

Bu yüzden **sadece backtest'te**, kuralı ölçmek için kill switch kapatılabilir: `ft.py backtest --no-kill-switch` (`user_data/config/research-no-kill-switch.json`). Kurallar:
- Dry-run ve gerçek işlemde config ne derse desin kill switch **her zaman açık** (`TrendEma.kill_switch_active`, testle zorunlu).
- Ana config'te bu bayrak olamaz (test).
- Bu sonuçlar ayrı klasöre yazılır, normal raporla karışmaz.
- Sayı (%20) değişmedi.

## Bilinen sınırlar

- Kill switch sadece **kapanmış** işlemlere bakar. Açık işlemler stoploss (R1) ile korunur.
- Stoploss market emirdir; çok sert düşüşte -%8'den biraz daha kötü fiyattan satabilir (kayma).
- Korumalar (R8-R9) yeni işlemi engeller, açık işlemi kapatmaz.

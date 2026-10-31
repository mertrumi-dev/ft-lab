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

Kural: Çıkarılan bir fren ancak backtest "bu boşluk gerçekten zarar ettiriyor" diye gösterirse geri eklenir.

## Başarı ölçütü

Bu risk kurallarıyla sermayenin en fazla ~%37'si piyasada olduğu için, güçlü yükselişte ham getiride al-tut'u geçmek neredeyse imkansız. Bu yüzden başarı risk-ayarlı ölçülür:

1. **Calmar oranı** (yıllık getiri / en büyük düşüş) al-tut'tan yüksek olmalı.
2. **En büyük düşüş (max drawdown)** al-tut'un yarısından az olmalı.
3. **En az 50 işlem** (daha azı istatistiksel olarak anlamsız).

Hepsi önce train/validation verisinde, en sonda bir kere test diliminde.

## Kill switch nasıl sıfırlanır?

Kill switch işlem geçmişinden hesaplanır, bu yüzden bot yeniden başlasa da açık kalır. Bilerek böyle: kötü giden bir botu "restart" ile kandıramazsın. Sıfırlamak için önce nedenini incele (`docs/journal.md`'ye yaz), sonra Claude ile birlikte karar ver.

## Bilinen sınırlar

- Kill switch sadece **kapanmış** işlemlere bakar. Açık işlemler stoploss (R1) ile korunur.
- Stoploss market emirdir; çok sert düşüşte -%8'den biraz daha kötü fiyattan satabilir (kayma).
- Korumalar (R8-R9) yeni işlemi engeller, açık işlemi kapatmaz.

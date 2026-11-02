# Öğretici kart 39: "Borsada stop" ne demek? Mac uyurken stopu kim izler?

## Stop nedir? (hatırlatma)

Botun kuralı: bir işlem girişin **%8 altına** inerse sat. Buna **stop** (zarar durdur) denir. Amacı tek bir işlemin büyük kayıp vermesini engellemek (risk kuralı R1: bir işlem sermayenin en fazla %1'ini kaybettirebilir).

## Stopu kim izliyor? İki yol var

| | Botta stop (şu anki dry-run botları) | Borsada stop |
|---|---|---|
| Stop nerede duruyor? | Botun hafızasında | Binance'in sunucusunda, bekleyen bir emir olarak |
| Kim izliyor? | Bot, 5 saniyede bir fiyata bakıyor | Borsa, her fiyat hareketinde |
| Mac uyursa? | **Kimse izlemiyor.** Bot donuyor | Borsa izlemeye devam ediyor |
| İnternet koparsa? | Kimse izlemiyor | Borsa izlemeye devam ediyor |

Borsada stop, Binance'e önceden verilmiş bir talimat gibidir: "Fiyat şu seviyeye düşerse benim yerime sat." Bu talimat borsada durduğu için bot uyusa da, internet kopsa da çalışır.

## Bugün neden önemli?

Bugün Mac 43 kez uyudu, toplam 16,7 saat. Bu sürede botun stopu izlenmedi. Şu an işlem açık olmadığı için zarar yok. Ama açık bir işlem varken Mac uyusa ve fiyat sert düşse, bot uyandığında stop çok daha kötü bir fiyattan çalışır. Örnek: stop %8'de, ama Mac uyanana kadar fiyat %15 düşmüşse, satış %15'ten olur.

Backtest (geçmiş verilerle sınama) her zaman stopun izlendiğini varsayar. Yani Mac uyudukça, gerçek sonuç backtest'ten kötü olabilir.

## Ne yapıldı?

- **Çalışan Mac botlarının ayarı değiştirilmedi.** Kural değişikliği gibi bir şey; ayrıca asıl çözüm uyumayan bir sunucu.
- **Demo (Faz 5) ayarında stop artık borsada:** `user_data/config/config.demo.json` içinde `stoploss_on_exchange: true`. Binance spotta bu, `stop_loss_limit` emri demek: fiyat stop seviyesine gelince, stopun %1 altına bir satış emri konur.
- **Ön kontrol bunu zorunlu kılıyor:** `python3 deploy/preflight.py`, demo ayarında borsada stop kapalıysa FAIL verir. Biri yanlışlıkla kapatırsa fark edilir.
- **Mini bot zaten böyle:** Demo modunda her alımdan sonra Binance'e stop emri koyuyor.

## Bir dezavantaj

"Limit" stop emri, fiyat çok hızlı düşerse dolmayabilir (fiyat limitin altına atlar). Bu yüzden limit, stopun %1 altına konuyor: küçük bir pay bırakılıyor. Freqtrade ayrıca stop emrini 60 saniyede bir kontrol edip gerekirse yeniliyor.

## Anlaman gerekenler

- **Bir güvenlik kuralı, onu uygulayan kişi uyurken işe yaramaz.** Stopu borsaya bırakmak, uygulayıcıyı her zaman uyanık birine (borsaya) devretmektir.
- **Backtest varsayımlarını canlıyla karşılaştır.** "Stop hep izleniyor" varsayımı Mac'te doğru değil; bu farkı bilmek gerçek sonuçları doğru okumayı sağlar.
- **Önemli bir ayarı test ile koru.** Ön kontrol, borsada stop kapatılırsa bunu yakalar.

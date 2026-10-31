# ft-lab yol haritası (sade anlatım)

## Bot ne yapacak?

Bot bir "kural takipçisi". Her yeni mumda (1 saatlik fiyat özeti: açılış, en yüksek, en düşük, kapanış) şunu yapar:

1. Binance'ten 5 coinin son fiyatlarını çeker.
2. Fiyatlardan göstergeler hesaplar (ör. RSI: son dönemde fiyat çok mu düştü, çok mu çıktı? 0-100 arası bir sayı).
3. Stratejiye sorar: "Şu an alayım mı? Elimdekini satayım mı?"
4. Cevaba göre (şimdilik sahte) alım-satım yapar ve deftere yazar.

Bot "tahmin" etmez, sihir yoktur. Sadece bizim yazdığımız kuralları 7/24, duygusuz ve yorulmadan uygular. Asıl iş: **hangi kuralın gerçekten işe yaradığını dürüstçe ölçmek.**

Kıyas noktamız hep **al-tut**: "Başta coinleri alıp hiç dokunmasaydık ne olurdu?" Bot bunu geçemiyorsa, uğraşmaya değmez. Bunu da dürüstçe yazacağız.

## Şu an ne yapıyor? (Faz 0)

- Kendi ilk stratejimiz **TrendEma** çalışıyor (trend takibi, 1 saatlik mumlar). Kuralları ve risk frenleri: `docs/learn/01-trend-ema-ve-risk.md`.
- 1000 USDT **sahte parayla**, 5 coinde (BTC, ETH, SOL, BNB, XRP) bakıyor.
- Kural: genel trend yukarıyken (fiyat EMA200 üstünde) EMA20, EMA50'yi yukarı keserse al; aşağı keserse sat. İşlem başına en fazla %1 risk, -%8 stoploss, art arda kayıp freni, %20'de kill switch.
- Amaç para kazanmak değil: **sistemin 24 saat hatasız çalıştığını görmek.** Borsa bağlantısı, veri, kayıt, arayüz, hepsi sağlam mı?
- Günlerce işlem açmayabilir. Trend takibi seyrek işlem yapar; sorun değil.

## Aşama aşama plan

| Faz | Ne yapacağız | Neden | Bitti sayılması için |
|---|---|---|---|
| **0. Kurulum** (şu an) | Bot sahte parayla 24 saat çalışsın | Sağlam bir zemin | 24 saat hatasız log |
| **1. Ölçüm disiplini** | 4-5 yıllık geçmiş fiyat verisi indir. Al-tut hesaplayan script yaz. Veriyi 3'e böl: ayarlama (%60), kontrol (%20), final sınavı (%20) | Bir stratejiyi ölçmeden "iyi" diyemeyiz. Final sınavı dilimine hiç bakmazsak kendimizi kandıramayız | Script çalışıyor, test edilmiş, örnek rapor var |
| **2. İlk 3 strateji** | (a) Trend takibi: kısa ve uzun ortalama kesişince al/sat. (b) Dipten alma: RSI çok düşükse al. (c) DCA: düştükçe kademeli al | Farklı mantıkları aynı cetvelle kıyaslamak | 3 strateji aynı tabloda, al-tut ile yan yana |
| **3. Sağlamlık ve "en optimum"** | Parametreyi biraz oynatınca sonuç çöküyor mu? Farklı yıllarda, düşüşte/yükselişte nasıl? Komisyon 2 katına çıkınca? Zarar limitleri ve acil durdurma | "Ezberlemiş" stratejiyi yakalamak. En iyi strateji = en çok kazandıran değil, her koşulda ayakta kalan | En iyi strateji final sınavında al-tut'u geçiyor, ya da geçemediğini dürüstçe yazıyoruz |
| **4. Sıfırdan mini bot** | Freqtrade'siz, 200 satırlık kendi botun (ccxt ile) | Freqtrade'in arka planda ne yaptığını gerçekten anlaman için | Testnet'e emir gönderip log yazıyor |
| **5. Demo borsa** | En iyi strateji Binance demo hesabında 4 hafta | Gerçek emir davranışı (gecikme, kısmi dolum) backtest'ten farklı olabilir | 4 hafta: demo sonucu, dry-run ve backtest beklentisiyle kıyaslandı |

Gerçek para bu planın **dışında**. Faz 5 bittikten sonra, sonuçlara bakıp ayrıca konuşacağız.

## Senin rolün ve benim rolüm

- **Ben:** kodu yazarım, her değişiklikte `docs/learn/` altına satır satır öğretici kart koyarım, sonuçları süslemeden raporlarım.
- **Sen:** kartları okursun, anlamadığını sorarsın, botu Mac'inde çalıştırırsın, kararları (hangi strateji, ne zaman ilerleme) sen verirsin.
- Her faz sonunda `docs/journal.md`'ye "ne öğrendik / ne işe yaramadı" yazılır.

## En önemli kural

**Final sınavı dilimine (son %20 veri) bakıp stratejiyi değiştirmek yasak.** Sınav sorularını görüp cevapları ezberleyen öğrenci gibi olur: geçmişte harika görünür, gerçekte çöker. Bunu her seferinde hatırlatacağım.

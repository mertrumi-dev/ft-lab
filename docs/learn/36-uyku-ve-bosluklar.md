# Öğretici kart 36: Mac uyuyunca ne oluyor? Boşluklar, tekrar deneme ve yapay zeka yorumlarının puanlanması (2026-11-02)

Bu kart 2 Kasım'daki üç kod değişikliğini anlatıyor. Hiçbiri botun alım-satım kuralını değiştirmedi; hepsi botun **etrafındaki** araçları daha sağlam yaptı.

## Önce temel fikir: "kalp atışı" (heartbeat)

Bot çalışırken dakikada bir log'a "Bot heartbeat" (kalp atışı) yazar. Bu, "hâlâ buradayım" demek.

- Kalp atışları dakikada bir geliyorsa: bot çalışıyor.
- İki kalp atışı arasında 5 dakikadan fazla varsa buna **boşluk** (gap) diyoruz: o sürede bot çalışmadı.

Bot neden çalışmaz? İki sebep olabilir:

1. **Bot çöktü** (programda hata oldu, kapandı).
2. **Mac uyudu** (bot hiç çökmedi ama bilgisayar uyuduğu için bekledi).

İkisi aynı görünür: log'da boşluk. Ama çözümleri farklı. Bu kart, ikisini nasıl ayırdığımızı anlatıyor.

## 1. Ağ hatası mı, gerçek hata mı? (b0cf11e)

`scripts/health.py` log'daki hataları iki gruba ayırır:

| Grup | Örnek | Ne demek |
|---|---|---|
| **Ağ hatası** | NetworkError, RequestTimeout | İnternete ulaşılamadı. Birkaç tane normal; çok sayıda gelirse internet yok ya da Mac uyuyor |
| **Diğer hata** | programdaki bir hata | Gerçek sorun, incelenmeli. Faz 0'ı başarısız yapar |

19:04'te ADX20 botunda bir hata "diğer" sayıldı. İnceledim:

```
aiohttp.client_exceptions.ClientConnectionResetError: Cannot write to closing transport
```

Türkçesi: "Kapanmakta olan bağlantıya yazamıyorum." Bot, Binance'ten canlı fiyat alan bağlantıya (websocket) "hâlâ buradayım" mesajı göndermeye çalışmış, ama Mac uykuya geçerken bağlantı zaten kopmuş. Yani bu bir **ağ olayı**, programda hata değil.

Düzeltme: Bu hata adını ağ hataları listesine ekledim (`NETWORK_EXCEPTIONS`). Ayrıca gerçek log satırlarından bir test yazdım: aynı satırlar gelirse "ağ hatası" sayılmalı.

**Dikkat:** Bu, hatayı saklamak değil. Bir hatayı "ağ" grubuna koymadan önce ne olduğunu okuduk ve sebebinin gerçekten bağlantı kopması olduğunu gördük. Bilmediğimiz bir hata asla bu listeye eklenmez.

## 2. Günlük rapor uykuya dayanıklı (7615c11)

`scripts/daily.py` her gün sırayla 30'dan fazla adım çalıştırır (veri indir, backtest, tablo, grafik...).

**Eski hali:** Bir adım başarısız olursa (örneğin Mac uykudayken veri indirme internet olmadığı için kalırsa) program **tamamen durur**du. O günün raporu hiç yazılmazdı.

**Yeni hali:**

1. Bir adım başarısız olursa 60 saniye bekler ve **bir kez daha dener**. Uyku ya da kısa bir internet kesintisinden sonra bağlantı genellikle geri gelir.
2. Yine olmazsa o adımı raporda **"BAŞARISIZ"** diye yazar ve **diğer adımlara devam eder**.
3. Program sonunda yine de "başarısız" sinyali verir (çıkış kodu 1). Yani hata gizlenmez; sadece bir adım yüzünden bütün gün kaybolmaz.

Programlamada bunun adı **"tekrar dene, sonra devam et"** (retry, then continue). Geçici hatalar (ağ) için iyi bir yaklaşım. Kalıcı hatalar için tekrar denemenin faydası yok, bu yüzden sadece **bir** kez deneniyor.

## 3. Boşlukları sayma ve sebebini söyleme (7615c11)

`health.py` raporuna yeni bir satır eklendi:

```
Gaps: 43 in the window, 16.7h without a heartbeat in total;
      container kept running through them: Mac asleep or no network, not a bot crash
```

Türkçesi: son 24 saatte 43 boşluk vardı, toplam 16,7 saat bot kalp atışı göndermedi. Sebep: konteyner (botun çalıştığı kutu) bu süre boyunca hiç yeniden başlamadı. Yani bot çökmedi, **Mac uyudu**.

Nasıl anlıyoruz? Docker, her konteynerin ne zaman başladığını bilir (`docker inspect` → `StartedAt`):

| Durum | Anlamı |
|---|---|
| Konteyner, ilk boşluktan **önce** başlamış ve hâlâ çalışıyor | Bot hiç kapanmadı → Mac uyudu ya da internet yoktu |
| Konteyner, ilk boşluktan **sonra** yeniden başlamış | Bot kapanıp yeniden açıldı → çökme ya da Docker yeniden başladı |

Bu, hata ayıklamanın (debugging) temel kuralı: **tahmin etme, kanıta bak.** Burada kanıt, konteynerin başlama zamanı ve Mac'in uyku kaydı (`pmset -g log`).

## 4. Yapay zeka grafik yorumları nasıl puanlanıyor? (ab2295f)

Bu bir deneme: Yapay zeka (ben), sadece günlük grafiğe bakarak 5 coin için "7 gün sonra fiyat yukarı mı, aşağı mı, yatay mı?" tahmini yazıyorum. Bot bu tahminleri **kullanmıyor**; sadece kaydediliyor.

Kurallar (ilk tahminden önce yazıldı, `docs/fresh/ai-views.md`):

1. Sadece şu sayılara bakılır: kapanış fiyatı, EMA20/50/200, 30 günlük oynaklık, hacim oranı. Haber yok.
2. Her tahmin: **yukarı / aşağı / yatay** (yatay = 7 günde ±%2 içinde) ve güven 1-3.
3. 7 gün sonra `python3 scripts/ft.py ai-score` gerçek kapanışa bakıp puanlar.
4. Karşılaştırma: **yazı-tura** (üç seçenekte rastgele %33 tutar) ve **"hep yukarı de"** tahmini.
5. Bot bu yorumları ancak **50'den fazla** tahminde ikisini de geçerse kullanmayı düşünür.

Neden sadece yeni veri? Yapay zeka eski grafikleri eğitiminden biliyor olabilir. Eski grafiklerde test etmek "kopya çekmek" olur. Sadece **henüz olmamış** 7 gün dürüst bir sınavdır.

Bir ayrıntı: "yatay" (±%2) dar bir bant. XRP gibi oynak bir coin haftada ortalama ~%6 oynuyor; böyle bir coin için "yatay" demek düşük ihtimalli bir tahmin. Bu yüzden yatay tahmini sadece oynaklığı düşük olan BTC için yazıldı.

İlk puanlama: **8 Kasım 2026.**

## Sonuç: bugünün dersi

Kural ne kadar iyi olursa olsun, **çalışmayan bot işlem yapamaz.** Bugün botlar 24 saatin 16,7 saatini Mac uykusu yüzünden kaybetti. Yazılımla bunun sadece bir kısmını çözebiliriz (`caffeinate` sadece "boşta uyuma"yı engeller; kapak kapanırsa ya da pilde sistem uyursa işe yaramaz). Gerçek çözüm: Mac'i şarja takmak ve kapağı açık tutmak, kalıcı olarak da hiç uyumayan bir sunucu (`deploy/MIGRATION.md`).

## Anlaman gerekenler

- **Boşluk ≠ çökme.** Log'da boşluk görünce önce "konteyner yeniden başladı mı?" diye bak. Başlamadıysa bot sağlam, sorun bilgisayarda.
- **Geçici hata için bir kez tekrar dene, sonra devam et ve kaydet.** Hatayı gizleme, ama bir hata yüzünden bütün işi de kaybetme.
- **Bir hatayı "zararsız" saymadan önce oku.** Ağ hatası listesine sadece sebebini anladığımız hatalar girer.

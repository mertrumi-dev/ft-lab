# Öğretici kart 35: Bir gecede 37 deneme ne öğretti? (2026-11-01/02)

Bu kart, ana kuralı "en iyi hale getirme" gecesinin derslerini özetliyor. Ayrıntılar: araştırma 12 (karne), `docs/journal.md`, `docs/trials.csv`.

## 1. Önce yaz, sonra bak (ön kayıt)

Her deneme koşmadan **önce** yazıldı: fikir, sayılar, geçme şartı. Sonuç gelince şart değiştirilmedi.

Neden: Sonucu gördükten sonra şart yazarsan, şartı sonuca uydurursun. Buna "çatallı yollar" denir: o kadar çok seçim yaparsın ki bir yerde iyi görünen bir sonuç mutlaka çıkar, ama şanstır.

Bu gece bir örnek: kazananları erken satan çıkış (T135) çok kötü çıktı. Sonra "o zaman kazananı uzun tutalım" fikri geldi (T136). Bu fikir sonuçtan doğduğu için ön kayıtta **açıkça** yazıldı ve aynı sıkı şartla sınandı. Yine kaldı.

## 2. Tek bir iyi sayı, iyi bir kural demek değildir (plato)

Bir ayarın iki yanındaki ayarlar da iyiyse buna **plato** (düzlük) denir: güvenilir. Sadece kendisi iyiyse **sivri tepe**: büyük ihtimalle şans.

| Ayar | Kendisi | Komşuları | Sonuç |
|---|---|---|---|
| EMA 20/50 (ana kural) | 1,86 | 0,67 - 1,88 | sivri tepe |
| Oylama eşiği 5/3 (T132) | 2,57 (early) | 4/2: 1,93 | sivri tepe |
| ADX 20 (yeni coinler) | +0,49 | 15: -0,57, 25: -0,64 | sivri tepe |
| Trend filtresi EMA200 | 1,86 | 1,22 - 1,91 | plato sayılır |
| Stop %8, oynaklık %60, pencere 30 gün | ~1,86 | 1,63 - 2,01 | plato |

**Ders:** Ana kuralın EMA çifti kırılgan, diğer ayarları sağlam. Kırılgan bir ayarı "düzeltmek" için başka bir sayı seçmek, aynı kırılganlığı başka yere taşır (oylama denemesi tam bunu yaptı).

## 3. En iyiyi sürekli yeniden seçmek, sabit kalmaktan kötü

"Son 12 ayın en iyi ayarını seç, sonraki 6 ay onu kullan" denendi (walk-forward): Calmar **0,50**. Hiç değiştirmeden bugünkü ayar: **0,92**. Geçmişin en iyisi, geleceğin en iyisi değil.

## 4. Kazananı erken kesme

Bu kural kârını birkaç büyük trendden alıyor. Kârı erken alan, iz süren stop koyan, korkuda satan her deneme (T060, T109, T135, T146) zarar verdi. Ama kazananı daha uzun tutmak da yeni coinlerde (T136) zarar verdi: yeni coinlerin trendleri kısa ve sert.

## 5. Hiç çalışmayan filtre de bir sonuçtur

Wikipedia ilgisi (T147) ve MVRV (T149) filtreleri işlem sayısını neredeyse hiç değiştirmedi. Bir kural neredeyse hiç devreye girmiyorsa, kurala bilgi eklemiyor demektir.

## 6. Aynı fikir, farklı veriyle yine aynı fikirdir

"Heyecanın zirvesinde alma" fikri üç farklı veriyle denendi: hacim (T144), Wikipedia ilgisi (T147), MVRV (T149). Üçü de ya zarar verdi ya hiçbir şey yapmadı. Dördüncü veriyi denemek sadece deneme sayısını (N) artırır.

## 7. Deneme sayısı (N) bir maliyettir

Her deneme, şansla iyi görünen bir sonuç bulma ihtimalini artırır. Bu yüzden "Deflated Sharpe" (deneme sayısına göre düzeltilmiş başarı ölçüsü) N ile birlikte hesaplanıyor. Bu gece N 111'den 148'e çıktı. Bazı fikirler (zaman bazlı çıkış, stoptan sonra yeniden giriş, 4 saatlik trend filtresi) önce ucuz bir analizle kontrol edildi; kazanç olmayacağı görülünce **deneme hakkı harcanmadı**.

## 8. Elle yapılan iş hata yapar, kurallar koda yazılır

Bu gece elle okumada süreç hataları oldu: kabuk komutunda kelime bölme, test hatasını gizleyen boru (`| tail`), yanlış yerde yapılan modül içe aktarma. Hepsi düzeltildi ve tekrarı için kod yazıldı: `ft.py trial` (dört dilim + otomatik hüküm), `ft.py prereg-judge` (taze veri satırlarını hüküm gününden önce asla açmaz), yapısal testler.

## 9. "Değişiklik yok" da bir sonuçtur

Gecenin sonunda ana kural **aynen** kaldı. Bu başarısızlık değil: kanıt, bugünkü kuralın elimizdeki veriyle ulaşılabilen en iyi hal olduğunu gösterdi. Dört umut verici fikir (F007-F010) 6 ay boyunca sadece yeni fiyatlarla yargılanacak.

## 10. Altyapı da bir risk

Botlar gece iki kez durdu, çünkü Mac uyudu. Kural ne kadar iyi olursa olsun, çalışmayan bot işlem yapamaz. Kalıcı çözüm: hiç uyumayan bir sunucu (deploy/MIGRATION.md).

## Anlaman gerekenler

- **Plato mu, tepe mi?** Bir ayarı değerlendirirken kendisine değil, komşularına da bak.
- **Ön kayıt kendini kandırmayı önler.** Şart sonuçtan önce yazılır, sonra değişmez.
- **Kodla zorlanan kural, hatırlanan kuraldan güçlüdür.** "Erken bakma" bir söz değil, kodda bir ret.

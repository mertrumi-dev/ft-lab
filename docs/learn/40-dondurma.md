# Kart 40: Denemeleri dondurma ve "bekçi" kod

## Ne değişti?

Deneme sayısı **N=160'ta donduruldu** (2026-11-05). Artık Kaan'ın açık onayı olmadan yeni deneme (T) ya da taze veri satırı (F) açılamıyor.

## Neden?

Aynı geçmiş veride ne kadar çok fikir denersen, şansla iyi görünen bir fikir bulma ihtimalin o kadar artar. 160 deneme zaten çok. Bundan sonra bilgi eski veriden değil, yeni fiyatlardan gelecek.

## Neden sadece CLAUDE.md'ye yazmadık?

Yazılı kural unutulabilir. Kod ise itiraz eder. Buna **guard (bekçi)** denir: bir işi yapmadan önce şartı kontrol edip şart yoksa işi durduran kod.

Satırlar bugüne kadar elle de eklendiği için üç ayrı kapı var:

| Kapı | Nerede | Ne yapar |
|---|---|---|
| `--open` komutu | `scripts/trials.py`, `scripts/prereg.py` | `--kaan-approved` yoksa ya da boşsa reddeder, dosyaya hiçbir şey yazmaz |
| Kontrol | her iki dosyadaki `problems()` | T162 ya da F013'ten sonraki bir satırın onay kaydı yoksa PROBLEM yazar; testler de bunu çalıştırdığı için commit öncesi yakalanır |
| Koşu | `ft.py trial` | `trials.csv`'de satırı olmayan stratejiyi koşmaz |

## Akış

`--kaan-approved "mesaj-id"` → boş mu? → (boşsa dur) → sıradaki id'yi bul → onayı `docs/freeze-approvals.csv`'ye yaz → satırı ekle.

Onay dosyası sadece büyür: hangi satırı kimin onayıyla açtığımızın kaydıdır.

## Bu bekçinin sınırı

Düz `ft.py backtest --strategy X` hâlâ çalışır, çünkü eski sonuçları yeniden ölçmek de bu komutu kullanıyor. Yani bekçi yanlışlıkla açmayı engeller, kararlı birini değil. Geri kalanı dürüstlük kuralı.

## Anlaman gerekenler

- **Bekçi işi yapmadan önce kontrol eder.** Refusal (ret) ilk satırlarda olduğu için hatalı durumda dosyaya hiçbir şey yazılmaz.
- **Tek kapı yetmez.** Bir kuralı atlamanın kaç yolu varsa, o kadar kontrol gerekir.
- **Test gerçek dosyayı da okur.** Bu yüzden elle eklenen bir satır commit öncesi testte patlar.

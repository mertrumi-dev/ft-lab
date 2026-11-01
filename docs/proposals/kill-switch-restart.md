# Kill switch sonrası insan kontrol listesi

> **Uygulandı 2026-11-01 (R13 eki, `docs/risk-rules.md`), Kaan değiştirebilir.** Seçilen bekleme: 14 gün + yazılı cevaplar. Koordinatörün kararıyla, Kaan'ın karar kartı cevabından önce uygulandı. Sadece yeniden başlamayı kısıtlıyor, hiçbir risk sayısını değiştirmiyor; sahte para botu için.

Neden: Final test otopsisi (araştırma 10) gösterdi ki kill switch kaybı %20'de tutuyor ama "ne zaman, nasıl yeniden başlanır" kararı belirsiz. Bu belge o kararı yazılı ve sakin bir sürece bağlamak için.

## 1. Kill switch kilitlenince bot ne yapar?

- **Yeni alım yapmaz.** Her alım isteği reddedilir; log'da `KILL SWITCH: realized drawdown reached X% (>= 20%) since the start. Entry on ... refused.` yazar.
- **Açık işlemleri zorla kapatmaz.** Onlar kendi stop'u (-%8) veya kendi çıkış sinyaliyle kapanır.
- **Kendi kendine açılmaz.** Kilit, işlem geçmişindeki en büyük düşüşe bakar (`trend_ema.worst_drawdown`). Sonradan kâr gelse de, bot yeniden başlatılsa da açık kalır. Mini bot için aynısı: `state.demo.json` içinde `kill_switch: true`.

## 2. Kaan ne görür?

- `python3 scripts/health.py`:
  `Kill switch: realized drawdown X% now, worst Y% of 20%  <-- TRIGGERED (stays on until a human resets it)`
  ve hemen altında bu belgenin yolu.
- Günlük rapor (`docs/fresh/latest.md`), bölüm 1: `Kill switch: ... TETİKLENDİ, yeni işlem yok, insan bakana kadar` ve bu belgenin yolu.

## 3. Sıfırlamadan önce cevaplanacak sorular

Cevaplar `docs/journal.md`'ye "KILL SWITCH İNCELEMESİ (tarih)" başlığıyla yazılır. Cevapsız soru varsa sıfırlama yapılmaz.

1. **Ne oldu?** Hangi tarihte kilitlendi, kaç işlemde, en büyük kayıplar hangi coinlerden? (`python3 scripts/ft.py explain`, `python3 scripts/ft.py execution`)
2. **Kural mı bozuk, piyasa mı?**
   - Aynı dönemde al-tut ve ünlü botlar ne yaptı? (`ft.py bots --slice fresh`)
   - Kayıp stop'lardan mı, küçük sinyal çıkışlarından mı, komisyondan mı? (araştırma 10'daki ayrım)
   - Emirler beklendiği gibi doldu mu, kayma büyük mü? (`ft.py execution`)
3. **Beklenen aralıkta mıydı?** `ft.py expected` taze sonucu beklenen aralığın neresinde gösteriyor? %5'in altındaysa "kural bu piyasada beklenenden kötü" sayılır.
4. **Şu anki rejim ne?** BTC günlük SMA200'ün üstünde mi, eğimi ne? (`ft.py chart --pair BTC --tr`, `ft.py scan`) Kural testere/ayıda kaybediyor (araştırma 06, 10).
5. **Teknik bir hata var mı?** Ağ kopması, veri boşluğu, yanlış fiyat? (`health.py`, log)
6. **Kararı kim veriyor?** Sadece Kaan. Claude sadece bilgiyi hazırlar.

## 4. Sıfırlama prosedürü (karar "yeniden başla" ise)

Kural: **eski veritabanı asla düzenlenmez.** İçindeki işlemleri silmek veya değiştirmek geçmişi sahteleştirir. Kill switch o geçmişten hesaplandığı için bu, freni kandırmak olur.

1. Botu durdur: `docker compose stop freqtrade`
2. Eski veritabanını arşivle (kopyala, sil değil):
   `mkdir -p user_data/archive && cp user_data/tradesv3.voltarget.dryrun.sqlite user_data/archive/tradesv3.voltarget.dryrun.KILLED-YYYYMMDD.sqlite && chmod 444 user_data/archive/*.sqlite`
3. Yeni veritabanı adı **ayrı bir commit** ile: `docker-compose.yml` → `--db-url sqlite:////freqtrade/user_data/tradesv3.voltarget-r2.dryrun.sqlite` (r2, r3, ...) ve `scripts/health.py` → `DB = ...-r2...`. Testler geçmeli; commit mesajında journal'daki inceleme tarihi geçmeli.
4. Başlat: `docker compose up -d freqtrade`
5. Doğrula: `python3 scripts/health.py`. "worst 0.0%" ve "TRIGGERED" yok; log'da strateji adı ve yeni DB adı.
6. Eski veritabanı analiz için kalır: `python3 scripts/ft.py execution --db user_data/archive/...KILLED-YYYYMMDD.sqlite`.

Mini bot (demo) için aynı mantık: `minibot/state.demo.json` → `minibot/archive/state.demo.KILLED-YYYYMMDD.json` (kopya), yeni dosya boş başlar. Eski dosya düzenlenmez.

## 5. En az bekleme süresi (uygulanan: 14 gün)

**Kilitlendikten sonra en az 14 gün** sıfırlama yok, ve 3. bölümdeki cevaplar journal'da yazılı olmalı.

Neden 14 gün:
- Kayıptan hemen sonra "hemen geri kazanayım" isteği kötü karar getirir. Bekleme süresi bunu engeller.
- 14 gün, `expected.py`'nin blok uzunluğunun (7 gün) iki katı. En az iki tam haftalık veriyle sakin bir bakış sağlar.

Bedeli (dürüstçe): Final testte (araştırma 10) VolTarget Temmuz 2026 sonunda kilitlendi, sert toparlanma Ağustos'ta geldi. 14 gün bekleme o toparlanmanın bir kısmını kaçırtırdı. Bekleme güvenlik için, getiri için değil.

Alternatif (Kaan seçebilir, ön kayıt gerektirir): "14 gün **ve** BTC günlük kapanışı 7 gün üst üste SMA200 üstünde". Daha temkinli, daha da geç.

## 6. Ne YAPILMAZ

- %20 sayısı "bu sefer" diye gevşetilmez (risk sayısı değişikliği = Kaan + tablo + test, R13).
- Kill switch kodu veya config bayrağı (`ftlab_research_no_kill_switch`) canlıda değiştirilmez; dry-run/canlıda zaten etkisiz (test).
- Sıfırlama aynı gün, inceleme yazılmadan yapılmaz.
- Eski DB silinmez, düzenlenmez.

## Anlaman gerekenler

- **Fren kendiliğinden bırakmaz; bırakma kararı yazılı ve gecikmeli olmalı.** Duyguyla verilen kararları azaltmak için.
- **Geçmiş kaydı kutsaldır.** Eski veritabanı arşivlenir, değiştirilmez. Yoksa ne olduğunu bir daha öğrenemeyiz.
- **Her güvenlik önleminin bir bedeli var.** Bekleme süresi kaybı da kazancı da geciktirir; bunu bilerek seçeriz.

# Öğretici kart 26: Günlük kısa rapor (`docs/fresh/latest.md`)

## Neden?

Bot ve testler her gün çok fazla sayı üretiyor. Kaan'ın her gün tek bir yere bakıp "her şey yolunda mı, bot ne görüyor, yeni fiyatlarda kim önde?" sorularının cevabını 1 dakikada görmesi lazım.

## Nerede?

- `docs/fresh/latest.md`: her zaman en son rapor.
- `docs/fresh/report-YYYY-MM-DD.md`: her günün raporu (geçmişe bakmak için).

`scripts/daily.py` bu raporu en son adımda kendisi yazar. Ek test koşturmaz; o gün zaten ölçülenleri toplar. Bota dokunmaz (sadece okur).

## 6 bölüm

1. **Bot sağlığı:** çalışıyor mu, kendi kodunda hata var mı, açık/kapanmış işlem, kâr/zarar, kill switch'e ne kadar yakın, Faz 0 durumu.
2. **Botun 5 coini:** her coin için durum (alım sinyali / trendde / bekliyor), uzun vade çizgisine (EMA200) uzaklık ve VolTarget'in pozisyon boyutu (oynak coinde %100'den küçük).
3. **Piyasa genişliği:** havuzdaki ~60 coinin yüzde kaçı uzun vade çizgisinin üstünde (son 7 gün). Düşükse piyasa genel olarak zayıf.
4. **Taze veri tablosu:** testten sonraki gerçek fiyatlarda VolTarget, eski kural (TrendEma), al-tut ve ünlü botlar. Ayrıca izleme satırları (2 saatlik, 1h+2h karışım, altınlı 6 coin).
5. **Emir kalitesi:** `ft.py execution` özeti (kart 25).
6. **Yapay zeka yorumları:** kaç yorum yazıldı, kaçı puanlandı.

## Kod

`scripts/kaan_report.py` sadece Python'un kendi kütüphaneleriyle çalışır. Her bölümü küçük bir fonksiyon üretir:

- `core_scan_rows`: tarayıcı çıktısından sadece botun 5 coinini (`*` işaretli satırları) alır.
- `bots_rows`: büyük tablodan sadece önemli satırları seçer.
- `breadth_rows`: `breadth.csv`'den son 7 günü okur.
- `ai_counts`: yorum tablosunda kaç satır var, kaçının "İsabet" sütunu dolu.
- `render`: hepsini Türkçe tek bir sayfaya dizer.

Testler bu fonksiyonları sahte girdilerle dener; böylece rapor biçimi bozulursa test kırmızı yanar.

## Anlaman gerekenler

- **Rapor kural değiştirmek için değil, izlemek için.** Taze verideki iyi ya da kötü bir gün yüzünden kural değiştirmiyoruz (aşırı uydurma).
- **"<50 trades" uyarısı:** az işlemle yapılan karşılaştırma şanstan ayırt edilemez. Bir ay boyunca bu uyarıyı göreceksin; normal.
- **Bağlantı hatası sayısı** Mac uyuyunca artar; botun kendi kodundaki hata sayısı (0) asıl önemli olan.

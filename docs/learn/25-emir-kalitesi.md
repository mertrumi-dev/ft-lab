# Öğretici kart 25: Emir kalitesi raporu (`ft.py execution`)

## Neden?

Geçmiş veri testi (backtest) her emrin mumun fiyatından hemen dolduğunu ve her işlemde sabit %0,15 maliyet olduğunu varsayar. Gerçekte üç şey farklı olabilir:

1. **Kayma (slippage):** Bot "alayım" dediğinde fiyat biraz kaçmış olabilir; emir sinyaldeki fiyattan biraz kötü dolar.
2. **Gecikme:** Limit emir hemen değil, birkaç dakika sonra dolar.
3. **Dolmayan emir:** Fiyat emrin bekleme süresinde (10 dakika) uzaklaşırsa emir iptal olur. O işlem hiç açılmaz.

Testlerimiz bu farkların önemli olduğunu gösterdi: komisyon 2 katına çıkınca botun skoru neredeyse yarıya iniyor. Kârın çoğu da az sayıdaki büyük trendden geliyor; tek bir kaçan giriş pahalıya patlayabilir. Bu rapor, bunları sahte para botunun kendi kayıtlarından ölçer.

## Komut

```
python3 scripts/ft.py execution
```

`user_data/` içindeki bütün `*.dryrun.sqlite` dosyalarını okur (TrendEma'nın veritabanı ve bu akşamdan sonra VolTarget'inki). Veritabanını **sadece okuma** modunda açar (`mode=ro`); çalışan bota dokunmaz.

## Ne gösterir?

| Satır | Anlamı |
|---|---|
| entry fill rate | Giriş emirlerinin yüzde kaçı doldu |
| avg slippage | Dolan fiyat ile sinyal mumunun kapanışı arasındaki fark. + = beklenenden kötü (alışta pahalıya, satışta ucuza) |
| avg time to fill | Emirden dolmaya kadar ortalama dakika |
| fees paid | Ödenen toplam komisyon (USDT) |
| missed entries | Dolmayan giriş emirleri; fiyatın 1 saat ve 24 saat sonra ne yaptığı. + = kaçan işlem kazandıracaktı |

Henüz işlem yoksa "no orders yet" yazar.

## Kod nasıl çalışıyor?

- `read_orders`: Freqtrade'in `orders` tablosundan her emri okur (çift, yön, giriş/çıkış, durum, istenen fiyat, dolan fiyat, zamanlar). `trades` tablosundan toplam komisyonu alır.
- `signal_candle`: Emir verildiği anda **kapanmış** son 1 saatlik mum. Mesela emir 10:05'te verildiyse sinyal mumu 09:00 mumudur.
- `slippage`: Alışta `dolan / sinyal − 1`, satışta `sinyal / dolan − 1`. İkisinde de + kötü demek.
- `summarize`: Fiyatları dışarıdan bir fonksiyonla alır. Testler gerçek veri gerektirmeden sahte fiyatlarla çalışabiliyor.

## Ne işe yarayacak?

Araştırma 05'teki "post-only" kararı için. Post-only emir sadece tahtada bekler, en ucuz komisyonu garanti eder, ama daha sık dolmayabilir. Binance demo hesabında 4 hafta bu rapor izlenecek:

- dolma oranı ≥ %90 mı?
- kaçan girişlerin sonraki hareketi, kazanılan komisyondan büyük mü?

İkisine göre post-only kalır ya da normal limit emre dönülür.

## Anlaman gerekenler

- **Backtest ile gerçek arasındaki fark ölçülmeden bilinmez.** Bu rapor o farkı sayıya döker.
- **Sadece okuma modu** bir güvenlik alışkanlığı: ölçüm aracı ölçtüğü sistemi asla değiştirmemeli.
- **Kaçan fırsatın da bir maliyeti var.** Ucuz emir, dolmazsa pahalı olabilir; ikisini birlikte ölçüyoruz.

# Araştırma 03: NFI X8'den bize ne alınabilir? (2026-11-01)

Kaynak: `user_data/strategies/thirdparty/NostalgiaForInfinityX8.py` (v18.0.183, GPL-3.0, 63.914 satır). Sadece okundu, kod kopyalanmadı.

## NFI nasıl çalışıyor (kısaca)
- 5 dakikalık mumlar; ~80 farklı giriş "modu" (normal, pump, quick, rebuy, rapid, grind, scalp, top_coins...). Çoğu **düşüşte alım**: fiyat kısa vadede aşırı düşmüşken (RSI düşük, Bollinger alt bandı altında) al.
- **Stop yok** gibi: spot stop eşiği %10 ama "rebuy/grind" modlarında 1,0 (= %100, yani hiç). Zarardaki işleme **ek alım** yapıp ortalamayı düşürür (grinding).
- Çıkış: kârdayken RSI/Bollinger "aşırı alım" sinyalleri, kâr kademelerine göre.
- Global koruma bayrakları (pump/dump) bu sürümde hep `True`, yani kapalı.

## Bizim kurallara uyan parça var mı?
| NFI fikri | Bizde denendi mi | Sonuç |
|---|---|---|
| Düşüşte alım (RSI düşükken al) | DipRsi, DipRsi4h (Faz 2) | Train'de her yıl zarar, elendi |
| Zarardayken ek alım (ortalama düşürme) | Risk kuralı R1/R2 (her işlemde stop, %1 risk) ile çelişiyor | Denenmez |
| Kârdayken ek alım (tersi) | TrendEmaPyramid / PyramidBtc | Train+val geçti, final testte kaldı |
| Aşırı alımda kâr al | TrendEma'nın en iyi %10 işlemi kârın %201'ini yapıyor; erken kâr almak bunları keser | Tur 5 ExitPrice 0,57, elendi |
| Piyasa geneli filtresi | TrendEmaBtc, TrendEmaBtcRising (tur 11) | BtcRising aday |

## Karar
NFI'nın kazancı "stopsuz ortalama düşürme + çok sayıda kısa vadeli düşüş alımı"ndan geliyor. İkisi de risk kurallarımıza (her işlemde stop, %1 risk) aykırı ya da bizde zaten denenip elendi. **Bota eklenecek yeni bir NFI parçası yok.** NFI ünlü bot kıyaslarında (`ft.py bots`) yerinde kalıyor.

# Öğretici kart 07: Kill switch backtest'i nasıl yanılttı

## Ne bulduk?

Rapora "Last trade" (son işlem tarihi) sütunu ekledik. Sonuç:

| Test | Strateji | Son işlem | Dönem sonu |
|---|---|---|---|
| 14 coin | TrendEma | **2021-07-12** | 2024-06-13 |
| 14 coin | TrendEmaSlow | **2022-02-18** | 2024-06-13 |
| 5 coin | TrendEmaMulti | 2022-06-07 | 2024-06-13 |
| 5 coin | TrendBreakout | 2022-06-10 | 2024-06-13 |
| 5 coin | TrendEma4h | 2023-03-03 | 2024-06-13 |

Yani bu stratejiler dönemin ortasında **%20 kill switch'e (acil durdurma) çarptı ve bir daha hiç alım yapmadı**. Örneğin 14 coin testinde TrendEma 3,5 yılın sadece ilk 6 ayında işlem yaptı.

## Neden sorun?

1. **"Kaldı" diyerek elediğimiz stratejiler aslında yarıda durdurulmuş olabilir.** Belki tam süre çalışsalardı iyi olacaklardı. Belki de çok daha kötü olacaklardı. Bilmiyoruz.
2. **14 coin testindeki "PASS" yanıltıcı.** TrendEma 2021 yükselişinde kazandı, sonra durdu ve 2022 çöküşünü nakitte geçirdi. Bu bir şans: kural çöküşü atlattığı için değil, kill switch tesadüfen doğru zamanda durdurduğu için iyi görünüyor.

## Gerçek botta kill switch iyi bir şey

Gerçek botta bu tam istediğimiz davranış: %20 kaybeden bot durur, sen bakarsın. Ama **ölçüm** yaparken bize şunu söylemesi lazım: "Bu kural 3,5 yıl boyunca nasıl davranır?"

## Çözüm: sadece backtest'te kapatılabilir anahtar

```python
def kill_switch_active(self) -> bool:
    if not self.config.get("ftlab_research_no_kill_switch", False):
        return True
    runmode = getattr(getattr(self, "dp", None), "runmode", None)
    return getattr(runmode, "value", None) not in ("backtest", "hyperopt")
```

Satır satır:
1. Config'te araştırma bayrağı yoksa kill switch **açık**.
2. Bayrak varsa botun hangi modda çalıştığına bakılır (`runmode`). `getattr(x, "y", None)`: "x'in y'si varsa al, yoksa None" (çökmeden).
3. Sadece mod "backtest" veya "hyperopt" ise kapalı. Dry-run, gerçek işlem veya bilinmeyen modda **açık**.

Yani bayrak yanlışlıkla canlı bota konsa bile kill switch kapanmaz. Bunu 5 test zorluyor. Ana config'te bayrak olmadığını da bir test kontrol ediyor.

Bayrak ayrı bir dosyada: `user_data/config/research-no-kill-switch.json`. Freqtrade birden fazla `--config` alabilir, ikincisi birincinin üstüne eklenir. Sonuçlar da ayrı klasöre gider (`backtest_results/no_kill_switch`), normal raporla karışmaz.

Komut:
```
python3 scripts/ft.py backtest --slice train --no-kill-switch --strategy all
python3 scripts/ft.py report --slice train --no-kill-switch
```

## Testler (17 yeni, toplam 101)

- Kill switch dry-run'da ve canlıda kapatılamıyor.
- Backtest'te varsayılan olarak açık.
- Mod bilinmiyorsa açık.
- Ana config'te bayrak yok.
- `ft.py` ikinci config'i ve ayrı klasörü ekliyor. Test dilimi kilidi hâlâ çalışıyor.
- Rapor "son işlem" tarihini gösteriyor ve %20 düşüşte işaret koyuyor.

---

## Anlaman gerekenler

1. Bir backtest'in "son işlem tarihi"ne her zaman bak; bot yarıda durmuş olabilir.
2. Kill switch canlıda koruma, ölçümde ise sis. Sadece ölçümde kapatıyoruz.
3. Önceki elemeler ve 14 coin sonucu yeniden ölçülecek; önceki kararlar kesin değil.

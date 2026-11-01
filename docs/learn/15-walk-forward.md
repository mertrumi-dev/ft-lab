# 15. Walk-forward: geçmişte en iyiyi seçmek gelecekte işe yarıyor mu? (Faz 3)

## Sorun

TrendEma'nın 6 komşusu var. Komşu, sayıları biraz farklı olan kural demek: EMA 15/25, 40/60, 150/250.

Bunların içinden "train'de en iyisini" seçmek cazip. Ama geçmişte en iyi olan, sırf şans eseri en iyi olmuş olabilir. Buna overfitting (aşırı uydurma) denir.

Walk-forward (ileriye yürüyerek test) bunu dürüstçe ölçer.

## Nasıl çalışıyor

Bir öğrenciyi düşün. Her dönem bir önceki yılın sınavlarına bakarak bir çalışma yöntemi seçiyor, sonra yeni dönemin sınavına giriyor. Seçtiği yöntem, girdiği sınava hiç bakmadan seçilmiş oluyor.

1. Train dilimi (2021-01 ile 2024-06) **6 aylık pencerelere** bölünür.
2. Her pencereden önce **son 12 aya** bakılır. 7 aday kuralın her biri puanlanır. Puan, getirinin düşüşe bölümüdür (Calmar benzeri).
3. En yüksek puanlı kural, **sadece bir sonraki 6 ayda** kullanılır.
4. Bu "sonraki 6 aylar" uç uca eklenir. Böylece sonuç seçim yapılmamış verilerden gelir (out-of-sample, örneklem dışı).
5. Aynı pencerelerde **hiç değiştirilmeyen TrendEma** ile karşılaştırılır.

İlk 12 ay sadece seçim için kullanılır. Örneklem dışı kısım 2022-01'den başlar.

## Nasıl yorumlanır

- **"En iyiyi seç" yöntemi, sabit TrendEma'yı yenmiyorsa:** sayıları sürekli ayarlamak işe yaramıyor, sadece risk ekliyor. Sabit kurala güveniriz. Bu iyi bir haber.
- **Yeniyorsa:** dönemsel yeniden ayar bir fikir olabilir. Ama yine validation diliminde doğrulanması gerekir.

## Önemli ayrıntılar

- **Yeni backtest yok.** Komşuların train sonuçları zaten vardı (kart 12). Script sadece işlemleri pencerelere ayırıyor. Bu yüzden yeni bir "deneme" sayılmaz.
- **Her işlemin sonucu hesabın yüzdesi olarak alınıyor:** "+10 USDT" yerine "+%1". Böylece farklı kuralların işlemleri uç uca eklenebiliyor.
- **Eşitlikte sabit kural seçiliyor.** Gereksiz değişiklik yapılmıyor.
- **Sadece train dilimi.** `--slice validation` ve `--slice test` komut satırında reddediliyor ve bu bir testle zorunlu tutuluyor.
- **Düşüş ölçümü kaba.** Burada düşüş sadece kapanmış işlemlerden ölçülüyor, saatlik ölçüm değil. Bu yüzden iki yöntemi kendi aralarında kıyaslamak için uygun.

## Testler (`tests/test_walkforward.py`)

En önemli test şu: A kuralı 2021'de parlıyor, 2022'de batıyor. B kuralı tam tersini yapıyor. Walk-forward 2022 için **A'yı seçmeli**, çünkü 2022'yi bilemez. Sonuç olarak sabit B'nin gerisinde kalmalı. Bu test, kodun geleceğe bakmadığını kanıtlıyor.

## Komut

```bash
python3 scripts/ft.py walkforward --slice train --no-kill-switch
```

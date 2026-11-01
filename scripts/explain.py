"""Trade explainer: every dry-run trade in plain Turkish (read-only).

    python3 scripts/ft.py explain      # prints Markdown; daily.py saves it to docs/fresh/trades-explained.md

For each trade in the dry-run DB(s): why it entered (EMA20 crossed above EMA50, how far
the price was above EMA200, VolTarget size from the hourly volatility), stake and risk,
why it exited, the result incl. fees, and what simply holding the coin did over the same
hours. With no trades yet it says what each of the bot's coins still needs for an entry.
The databases are opened read-only (sqlite uri mode=ro). Runs in Docker (pandas).
"""

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
USER_DATA = ROOT / "user_data"
DATA_DIR = USER_DATA / "data" / "binance"
CORE_5 = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
STOP = 0.08
TARGET_VOL, VOL_WINDOW, HOURS_PER_YEAR = 0.60, 24 * 30, 24 * 365
EXIT_TR = {
    "exit_signal": "EMA20, EMA50'yi aşağı kesti (trend bitti)",
    "ema_cross_down": "EMA20, EMA50'yi aşağı kesti (trend bitti)",
    "stop_loss": "-%8 zarar durdurma (stop) çalıştı",
    "stoploss": "-%8 zarar durdurma (stop) çalıştı",
    "trailing_stop_loss": "zarar durdurma (stop) çalıştı",
    "force_exit": "elle / zorla kapatıldı",
}


def indicators(closes: pd.Series) -> pd.DataFrame:
    """Same numbers the bot uses: EMA20/50/200 and the 30-day annualized hourly volatility."""
    df = pd.DataFrame({"close": closes})
    for n in (20, 50, 200):
        df[f"ema{n}"] = closes.ewm(span=n, adjust=False).mean()
    df["rvol"] = np.log(closes).diff().rolling(VOL_WINDOW).std() * np.sqrt(HOURS_PER_YEAR)
    return df


def size_scale(vol: float) -> float:
    return 1.0 if not np.isfinite(vol) or vol <= 0 else min(1.0, TARGET_VOL / vol)


def next_entry_need(row: pd.Series) -> str:
    """What a coin still needs for the bot's next entry, in plain Turkish."""
    gap200 = row["close"] / row["ema200"] - 1
    gap2050 = row["ema20"] / row["ema50"] - 1
    if gap200 <= 0:
        return (f"fiyat EMA200'ün %{abs(gap200) * 100:.1f} altında; önce EMA200 üstüne çıkmalı,"
                " sonra EMA20 EMA50'yi yukarı kesmeli")  # fmt: skip
    if gap2050 <= 0:
        return (f"fiyat EMA200'ün %{gap200 * 100:.1f} üstünde; EMA20'nin EMA50'yi yukarı kesmesi bekleniyor"
                f" (şu an %{abs(gap2050) * 100:.1f} altında)")  # fmt: skip
    return ("fiyat EMA200 üstünde ve kısa trend zaten yukarı; yeni giriş için EMA20 önce EMA50'nin"
            " altına inip tekrar yukarı kesmeli")  # fmt: skip


def exit_distance(row: pd.Series, open_rate: float, stop: float = STOP) -> str:
    """How far an open trade is from its two exits: EMA20 crossing below EMA50, or the stop."""
    gap = row["ema20"] / row["ema50"] - 1
    stop_px = open_rate * (1 - stop)
    to_stop = 1 - stop_px / row["close"]
    cross = (f"EMA20, EMA50'nin %{gap * 100:.1f} üstünde; aşağı keserse satar" if gap > 0
             else "EMA20 EMA50'nin altına indi; bir sonraki mumda çıkış sinyali bekleniyor")  # fmt: skip
    return f"- Çıkışa uzaklık: {cross}. Stop fiyatı {stop_px:g}, şu anki fiyatın %{to_stop * 100:.1f} altında."


def read_trades(db: Path) -> pd.DataFrame:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return pd.read_sql_query(
            "select id, pair, is_open, open_date, close_date, open_rate, close_rate, stake_amount, "
            "close_profit, close_profit_abs, exit_reason, strategy, fee_open_cost, fee_close_cost from trades order by open_date",
            con,
        )
    finally:
        con.close()


def explain_trade(t: pd.Series, ind: pd.DataFrame, now_close: float | None) -> str:
    opened = pd.Timestamp(t["open_date"], tz="UTC")
    signal = opened.floor("1h") - pd.Timedelta(hours=1)
    row = None
    if not ind.empty and len(ind.loc[:signal]):
        row = ind.loc[:signal].iloc[-1]
    lines = [f"### #{int(t['id'])} {t['pair']} ({t['strategy']}), giriş {opened:%Y-%m-%d %H:%M} UTC, fiyat {t['open_rate']:g}"]
    if row is not None:
        scale = size_scale(row["rvol"]) if "VolTarget" in str(t["strategy"]) else 1.0
        lines.append(f"- Neden aldı: {signal:%H:%M} mumunda EMA20 ({row['ema20']:g}) EMA50'yi ({row['ema50']:g}) yukarı kesti;"
                     f" fiyat EMA200'ün %{(row['close'] / row['ema200'] - 1) * 100:.1f} üstündeydi.")  # fmt: skip
        if "VolTarget" in str(t["strategy"]):
            lines.append(f"- Pozisyon boyutu: normalin %{scale * 100:.0f}'i (saatlik oynaklık yıllık %{row['rvol'] * 100:.0f};"
                         " %60'tan oynaksa küçülür).")  # fmt: skip
    lines.append(f"- Yatırılan: {t['stake_amount']:.2f} USDT; stop'a çarparsa en fazla ~{t['stake_amount'] * STOP:.2f} USDT kayıp.")
    fees = (t["fee_open_cost"] or 0) + (t["fee_close_cost"] or 0)
    if t["is_open"]:
        if now_close:
            lines.append(f"- Durum: hâlâ açık. Şu anki fiyat {now_close:g} ({now_close / t['open_rate'] - 1:+.1%}).")
            if not ind.empty:
                lines.append(exit_distance(ind.iloc[-1], t["open_rate"]))
        else:
            lines.append("- Durum: hâlâ açık.")
    else:
        closed = pd.Timestamp(t["close_date"], tz="UTC")
        why = EXIT_TR.get(str(t["exit_reason"]), str(t["exit_reason"]))
        lines.append(f"- Neden sattı: {why}, {closed:%Y-%m-%d %H:%M} UTC, fiyat {t['close_rate']:g}.")
        lines.append(f"- Sonuç: {t['close_profit'] * 100:+.2f}% = {t['close_profit_abs']:+.2f} USDT (komisyon dahil; ödenen komisyon {fees:.2f} USDT).")
        held = ind.loc[opened.floor("1h"): closed.floor("1h"), "close"] if not ind.empty else []
        if len(held) > 1:
            lines.append(f"- Aynı saatlerde coini sadece tutmak: {held.iloc[-1] / held.iloc[0] - 1:+.2%}.")
    return "\n".join(lines)


def load_indicators(pair: str, data_dir: Path = DATA_DIR) -> pd.DataFrame | None:
    path = data_dir / f"{pair.replace('/', '_')}-1h.feather"
    if not path.exists():
        return None
    h = pd.read_feather(path).set_index("date")
    return indicators(h["close"])


def render(trades: list[pd.DataFrame], ind_for) -> str:
    lines = ["# İşlem açıklamaları", "", "Sahte para botlarının (dry-run) her işlemi, sade dille. Yatırım tavsiyesi değildir.", ""]
    all_trades = pd.concat(trades) if trades else pd.DataFrame()
    if all_trades.empty:
        lines += ["Henüz işlem yok. Botun 5 coini için bir sonraki alım şartı (1 saatlik grafik):", ""]
        for pair in CORE_5:
            ind = ind_for(pair)
            if ind is None or ind.empty:
                lines.append(f"- {pair.split('/')[0]}: veri yok")
                continue
            lines.append(f"- {pair.split('/')[0]}: {next_entry_need(ind.iloc[-1])}")
        return "\n".join(lines) + "\n"
    for _, t in all_trades.iterrows():
        ind = ind_for(t["pair"])
        now_close = float(ind["close"].iloc[-1]) if ind is not None and len(ind) else None
        lines += [explain_trade(t, ind if ind is not None else pd.DataFrame(), now_close), ""]
    return "\n".join(lines) + "\n"


def main() -> None:  # pragma: no cover - reads the real DBs inside the container
    dbs = sorted(USER_DATA.glob("*.dryrun.sqlite"))
    cache: dict[str, pd.DataFrame | None] = {}

    def ind_for(pair: str):
        if pair not in cache:
            cache[pair] = load_indicators(pair)
        return cache[pair]

    print(render([read_trades(db) for db in dbs], ind_for))


if __name__ == "__main__":
    main()

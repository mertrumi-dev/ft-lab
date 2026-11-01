"""Replay check: does the mini bot's demo loop trade exactly like the backtested rule?

    python3 scripts/ft.py replay --slice fresh          # or validation (core coins, kill switch off)

A ReplayExchange (a fake ccxt object, no network, no keys) serves the real downloaded 1h
candles of the 5 core coins hour by hour. demo.step runs on it exactly as it would on Binance
Demo Mode: at hour T it sees the candles closed before T and sends LIMIT orders, which fill
inside candle T if its range touches the limit (at the open when the open is already better,
like Freqtrade's backtest). Then the trade list is compared with Freqtrade's
TrendEmaVolTarget backtest on the same timerange: entries/exits by hour, stake fraction, P/L.

Runs in Docker (pandas reads the candles and the backtest result).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

HOUR_MS = 3_600_000
CORE = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
DEMO_URLS = {"public": "https://demo-api.binance.com/api/v3", "private": "https://demo-api.binance.com/api/v3"}


class ReplayExchange:
    """Fake ccxt exchange over stored candles. `now_ms` = open time of the candle that is forming."""

    def __init__(self, candles: dict[str, list[list[float]]], fee: float):
        self.candles, self.fee = candles, fee
        self.index = {p: {int(r[0]): i for i, r in enumerate(rows)} for p, rows in candles.items()}
        self.urls, self.options = {"api": dict(DEMO_URLS)}, {"defaultType": "spot"}
        self.now_ms, self.orders = 0, {}

    def enable_demo_trading(self, enable):  # already demo urls
        pass

    def fetch_ohlcv(self, pair, timeframe, limit):
        i = self.index[pair].get(self.now_ms)
        rows = self.candles[pair][: i if i is not None else 0]  # only candles closed before now
        return rows[-limit:]

    def amount_to_precision(self, pair, amount):
        return repr(amount)

    def price_to_precision(self, pair, price):
        return repr(price)

    def fetch_balance(self):
        return {"free": {"USDT": 1e12}}  # the ledger, not the balance, limits risk

    def create_order(self, symbol, type, side, amount, price, params):
        assert type == "limit"
        oid = str(len(self.orders) + 1)
        if "stopLossPrice" in params:  # STOP_LOSS_LIMIT: waits for the trigger, checked candle by candle
            assert side == "sell"
            self.orders[oid] = {"id": oid, "status": "open", "filled": 0.0, "amount": amount, "price": price,
                                "average": None, "stop": params["stopLossPrice"], "placed": self.now_ms,
                                "symbol": symbol}  # fmt: skip
            return dict(self.orders[oid])
        order = {"id": oid, "status": "open", "filled": 0.0, "amount": amount, "price": price, "average": None}
        i = self.index[symbol].get(self.now_ms)
        if i is not None:
            _, o, h, lo, _c, _v = self.candles[symbol][i]
            fill = None
            if side == "buy" and lo <= price:
                fill = min(o, price)
            if side == "sell" and h >= price:
                fill = max(o, price)
            if fill is not None:
                order.update(status="closed", filled=amount, average=fill,
                             fee={"cost": amount * fill * self.fee, "currency": "USDT"})  # fmt: skip
        self.orders[oid] = order
        return dict(order)

    def _check_stop(self, order: dict) -> None:
        """Trigger inside every candle from the placement hour up to (not incl.) now: low <= stop.

        Fill: the stop price if the candle opened above it, the open if it opened between stop and
        limit (gap), else only when the price climbs back to the limit (at the limit).
        """
        if order.get("stop") is None or order["status"] != "open":
            return
        rows, i = self.candles[order["symbol"]], self.index[order["symbol"]].get(order["placed"])
        triggered = order.get("triggered", False)
        while i is not None and i < len(rows) and rows[i][0] < self.now_ms:
            ts, o, h, lo, _c, _v = rows[i]
            fill = None
            if not triggered and lo <= order["stop"]:
                triggered = True
                fill = order["stop"] if o >= order["stop"] else (o if o >= order["price"] else None)
            if triggered and fill is None and h >= order["price"]:
                fill = max(order["price"], min(o, order["stop"]))
            if fill is not None:
                order.update(status="closed", filled=order["amount"], average=fill, lastTradeTimestamp=ts,
                             fee={"cost": order["amount"] * fill * self.fee, "currency": "USDT"})  # fmt: skip
                return
            i += 1
        order["triggered"], order["placed"] = triggered, self.now_ms  # resume from here next time

    def fetch_order(self, oid, symbol):
        self._check_stop(self.orders[oid])
        return dict(self.orders[oid])

    def cancel_order(self, oid, symbol):
        self._check_stop(self.orders[oid])  # it may have filled before the cancel arrives
        if self.orders[oid]["status"] == "open":
            self.orders[oid]["status"] = "canceled"


def run_replay(candles, start_ms: int, end_ms: int, fee: float, pairs=CORE):
    """Run demo.step hour by hour. Returns (ledger, broker state, last closes)."""
    from minibot import demo, paper

    ex = ReplayExchange(candles, fee)
    state = {"ledger": paper.new_account(demo.RESEARCH_EQUITY)}
    clock = [0]

    def tick():  # every poll moves the fake clock, so an unfilled order times out at once
        clock[0] += demo.UNFILLED_TIMEOUT_S
        return clock[0]

    broker = demo.DemoBroker(ex, state, sleep=lambda s: None, clock=tick)
    t = start_ms
    while t < end_ms:
        ex.now_ms = t
        demo.step(state["ledger"], broker, ex, t, pairs=pairs)
        t += HOUR_MS
    return state


def minibot_trades(state: dict) -> list[dict]:
    """Pair entries and exits from the recorded orders (filled ones only)."""
    import pandas as pd

    trades, open_ = [], {}
    for o in state.get("orders", []):
        if not o.get("filled"):
            continue
        when = pd.Timestamp(o["candle"]) if "candle" in o else None
        if o["side"] == "buy":
            open_[o["pair"]] = {"pair": o["pair"], "open": when, "open_rate": o["average"], "amount": o["filled"],
                                "stake": o["filled"] * o["average"] + o["fee_usdt"]}  # fmt: skip
        elif o["pair"] in open_:
            tr = open_.pop(o["pair"])
            tr.update(close=when, close_rate=o["average"], reason=o["kind"],
                      profit=o["filled"] * o["average"] - o["fee_usdt"] - tr["stake"])  # fmt: skip
            trades.append(tr)
    return trades + [{**tr, "close": None, "reason": "open at end"} for tr in open_.values()]


def compare(mini: list[dict], ft: list[dict]) -> dict:
    """Match by (pair, open hour). Returns matched rows and the unmatched ones on each side."""
    import pandas as pd

    key = lambda pair, ts: (pair, pd.Timestamp(ts).floor("1h"))  # noqa: E731
    fmap = {key(t["pair"], t["open_date"]): t for t in ft}
    mmap = {key(t["pair"], t["open"]): t for t in mini if t["open"] is not None}
    both = sorted(set(fmap) & set(mmap))
    rows = []
    for k in both:
        f, m = fmap[k], mmap[k]
        same_exit = m["close"] is not None and pd.Timestamp(m["close"]).floor("1h") == pd.Timestamp(f["close_date"]).floor("1h")
        rows.append({"pair": k[0], "open": k[1], "ft_stake": f["stake_amount"], "mini_stake": m["stake"],
                     "ft_exit": pd.Timestamp(f["close_date"]).floor("1h"), "mini_exit": m["close"],
                     "same_exit": same_exit, "ft_reason": f.get("exit_reason"), "mini_reason": m["reason"],
                     "ft_profit": f["profit_abs"], "mini_profit": m.get("profit")})  # fmt: skip
    return {"matched": rows, "only_ft": [fmap[k] for k in sorted(set(fmap) - set(mmap))],
            "only_mini": [mmap[k] for k in sorted(set(mmap) - set(fmap))]}


def main() -> int:  # pragma: no cover - needs candles and backtest results inside the container
    import pandas as pd

    import report
    from splits import SLICES

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--slice", choices=["fresh", "validation"], required=True)
    p.add_argument("--fee", type=float, default=0.0015, help="per side; 0.0015 = the backtest's fee")
    p.add_argument("--results-dir", type=Path, default=Path("/freqtrade/user_data/backtest_results/no_kill_switch"))
    a = p.parse_args()
    s = SLICES[a.slice]
    data = ROOT / "user_data" / "data" / "binance"
    candles = {}
    for pair in CORE:
        df = pd.read_feather(data / f"{pair.replace('/', '_')}-1h.feather")
        ms = pd.to_datetime(df["date"], utc=True).astype("datetime64[ms, UTC]").astype("int64")
        candles[pair] = [[int(t), o, h, lo, c, v] for t, o, h, lo, c, v in
                         zip(ms, df["open"], df["high"], df["low"], df["close"], df["volume"])]  # fmt: skip
    start = int(pd.Timestamp(s.start, tz="UTC").value // 10**6)
    end = min(int(pd.Timestamp(s.end, tz="UTC").value // 10**6), max(r[0] for r in candles["BTC/USDT"]) + HOUR_MS)
    stats = report.latest_stats_per_strategy(s.timerange, CORE, 0.0015, a.results_dir).get("TrendEmaVolTarget")
    if not stats:
        print(f"no TrendEmaVolTarget backtest for {s.timerange} in {a.results_dir}: run ft.py backtest --slice {a.slice} "
              "--no-kill-switch --strategy TrendEmaVolTarget first")  # fmt: skip
        return 1
    state = run_replay(candles, start, end, a.fee)
    mini = minibot_trades(state)
    c = compare(mini, stats["trades"])
    print(render(a.slice, s.timerange, mini, stats, c, state))
    return 0


def exit_kinds(matched: list[dict]) -> str:
    """Classify exit-hour differences: a stop seen one candle later (by design) or still open at the end."""
    import pandas as pd

    kinds = {"stop 1h later": 0, "open at end (FT force exit)": 0, "other": 0}
    for r in matched:
        if r["same_exit"]:
            continue
        if r["mini_exit"] is None and r["ft_reason"] == "force_exit":
            kinds["open at end (FT force exit)"] += 1
        elif r["ft_reason"] == "stop_loss" and pd.Timestamp(r["mini_exit"]) - r["ft_exit"] == pd.Timedelta(hours=1):
            kinds["stop 1h later"] += 1
        else:
            kinds["other"] += 1
    return ", ".join(f"{k} {v}" for k, v in kinds.items())


def explain_extra(extra: list[dict], ft: list[dict]) -> dict:
    """For each minibot-only entry: what Freqtrade's rules (max 3 open, 2h cooldown, stop guard) would have said."""
    import pandas as pd

    out = {"max_open_trades (3 open in FT)": 0, "cooldown (same pair closed <2h before)": 0,
           "stoploss guard (3 stops in 24h)": 0, "unexplained": 0}  # fmt: skip
    for t in extra:
        when = pd.Timestamp(t["open"])
        opened = [f for f in ft if pd.Timestamp(f["open_date"]) <= when < pd.Timestamp(f["close_date"])]
        recent = [f for f in ft if f["pair"] == t["pair"] and timedelta_ok(pd.Timestamp(f["close_date"]), when, 2)]
        stops = [f for f in ft if f.get("exit_reason") == "stop_loss" and timedelta_ok(pd.Timestamp(f["close_date"]), when, 24)]
        if len(opened) >= 3:
            out["max_open_trades (3 open in FT)"] += 1
        elif recent:
            out["cooldown (same pair closed <2h before)"] += 1
        elif len(stops) >= 3:
            out["stoploss guard (3 stops in 24h)"] += 1
        else:
            out["unexplained"] += 1
    return {k: v for k, v in out.items() if v}


def timedelta_ok(closed, when, hours) -> bool:
    import pandas as pd

    return closed <= when < closed + pd.Timedelta(hours=hours)


def render(name, timerange, mini, stats, c, state) -> str:
    ft = stats["trades"]
    m = c["matched"]
    same_exit = sum(r["same_exit"] for r in m)
    stake_err = [abs(r["mini_stake"] / r["ft_stake"] - 1) for r in m if r["ft_stake"]]
    mini_pl = sum(t["profit"] for t in mini if t.get("profit") is not None)
    lines = [
        f"Replay {name} ({timerange}), core 5, minibot demo loop vs Freqtrade TrendEmaVolTarget backtest",
        f"  trades: Freqtrade {len(ft)}, minibot {len(mini)}; same entry hour {len(m)}; of those same exit hour {same_exit}",
        f"  stake: median |minibot/Freqtrade - 1| = {sorted(stake_err)[len(stake_err) // 2]:.2%}" if stake_err else "  stake: -",
        f"  P/L of trades both closed: Freqtrade {sum(r['ft_profit'] for r in m if r['mini_profit'] is not None):+.2f} USDT, "
        f"minibot {sum(r['mini_profit'] for r in m if r['mini_profit'] is not None):+.2f} USDT "
        f"(all closed: FT {sum(t['profit_abs'] for t in ft):+.2f} incl. force exits at the end, minibot {mini_pl:+.2f})",
        f"  exit differences: {exit_kinds(m)}",
        "  P/L gap minibot - FT: same-exit trades {:+.2f}, stop-1h-later trades {:+.2f}".format(
            sum(r["mini_profit"] - r["ft_profit"] for r in m if r["same_exit"]),
            sum(r["mini_profit"] - r["ft_profit"] for r in m if not r["same_exit"] and r["mini_profit"] is not None)),
        f"  only in Freqtrade: {len(c['only_ft'])}, only in minibot: {len(c['only_mini'])}",
    ]
    for t in c["only_ft"][:10]:
        lines.append(f"    FT only   {t['pair']:<9} {t['open_date']}  exit {t['exit_reason']}  {t['profit_abs']:+.2f}")
    why = explain_extra(c["only_mini"], ft)
    if why:
        lines.append("  why minibot-only: " + ", ".join(f"{k} {v}" for k, v in why.items()))
    for t in c["only_mini"][:10]:
        lines.append(f"    mini only {t['pair']:<9} {t['open']}  {t['reason']}  {t.get('profit') or 0:+.2f}")
    for r in [r for r in m if not r["same_exit"]][:10]:
        lines.append(f"    exit diff {r['pair']:<9} {r['open']}  FT {r['ft_exit']} ({r['ft_reason']})  mini {r['mini_exit']} ({r['mini_reason']})")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())

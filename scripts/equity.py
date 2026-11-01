"""Hour-by-hour account value of a backtest, open trades included.

Why: Freqtrade's drawdown only moves when a trade CLOSES. A trade that is -15%
for a week and then closes at -2% never shows the -15%. Buy-and-hold's
drawdown is measured every hour, so to compare fairly we measure the strategy
every hour too ("mark to market": value open coins at the current price).

Also measures exposure: what share of the money is actually in coins, on
average. A low number explains why the bot earns much less than buy-and-hold
in a rising market.
"""

import pandas as pd


def _ts(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def hourly_equity(
    trades: list[dict], closes: dict[str, pd.Series], start_balance: float, index: pd.DatetimeIndex
) -> pd.DataFrame:
    """DataFrame with columns equity and invested, one row per hour of `index`.

    realized: start balance + profit of every trade closed so far.
    open trade value change: coins x price now - money put in (fees on the
    still-to-come sell are not counted, so this is very slightly optimistic).
    """
    realized = pd.Series(0.0, index=index)
    unrealized = pd.Series(0.0, index=index)
    invested = pd.Series(0.0, index=index)
    for t in trades:
        opened, closed = _ts(t["open_date"]), _ts(t["close_date"])
        # profit counts from the close hour on
        realized.loc[realized.index >= closed] += t["profit_abs"]
        prices = closes.get(t["pair"])
        if prices is None:
            continue
        held = prices[(prices.index >= opened) & (prices.index < closed)]
        held = held[held.index.isin(index)]
        unrealized.loc[held.index] += t["amount"] * held.to_numpy() - t["stake_amount"]
        invested.loc[held.index] += t["stake_amount"]
    equity = start_balance + realized + unrealized
    return pd.DataFrame({"equity": equity, "invested": invested})


def hourly_equity_from_orders(
    trades: list[dict], closes: dict[str, pd.Series], start_balance: float, index: pd.DatetimeIndex
) -> pd.DataFrame:
    """Exact version, built from every filled order (needed when a trade buys or
    sells in several steps, e.g. position adjustment).

    cash: start balance - every buy (cost + fee) + every sell (cost - fee)
    coins: running amount held per pair, valued at each hour's close
    """
    cash = pd.Series(0.0, index=index)
    held_value = pd.Series(0.0, index=index)
    invested = pd.Series(0.0, index=index)
    for t in trades:
        prices = closes.get(t["pair"])
        steps = []  # (time, change in coins)
        for o in sorted(t["orders"], key=lambda o: o["order_filled_timestamp"] or 0):
            if not o.get("order_filled_timestamp"):
                continue
            when = pd.Timestamp(o["order_filled_timestamp"], unit="ms", tz="UTC")
            buy = o["ft_is_entry"]
            fee = t.get("fee_open" if buy else "fee_close", 0.0) or 0.0
            flow = -o["cost"] * (1 + fee) if buy else o["cost"] * (1 - fee)
            cash.loc[cash.index >= when] += flow
            steps.append((when, o["amount"] if buy else -o["amount"]))
        if prices is None or not steps:
            continue
        coins = pd.Series(0.0, index=index)
        for when, change in steps:
            coins.loc[coins.index >= when] += change
        coins = coins.clip(lower=0)
        price_now = prices.reindex(index).ffill().fillna(0.0)
        held_value += coins * price_now
        invested += coins * price_now
    equity = start_balance + cash + held_value
    return pd.DataFrame({"equity": equity, "invested": invested})


def build_curve(
    trades: list[dict], closes: dict[str, pd.Series], start_balance: float, index: pd.DatetimeIndex
) -> pd.DataFrame:
    """Use exact order-based curve when every trade carries its orders, else the simple one."""
    if trades and all(t.get("orders") for t in trades):
        return hourly_equity_from_orders(trades, closes, start_balance, index)
    return hourly_equity(trades, closes, start_balance, index)


def max_drawdown(equity: pd.Series) -> float:
    return float((1 - equity / equity.cummax()).max())


def summary(curve: pd.DataFrame) -> dict:
    """Hourly max drawdown and average share of money in coins."""
    return {
        "max_drawdown_hourly": max_drawdown(curve["equity"]),
        "exposure": float((curve["invested"] / curve["equity"]).mean()),
    }

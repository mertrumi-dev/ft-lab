"""Paper broker: a fake account that buys and sells with imaginary money.

It keeps cash and positions, pays a fee on every fill, and applies the same
risk rules as the real strategy (docs/risk-rules.md):
    1% risk per trade with a -8% stop, at most 25% of capital in one trade,
    no new trades after a 20% fall of realized equity from its peak.
State is a plain dict so it can be saved to / loaded from JSON.
"""

import json
from pathlib import Path

# Read from the bot's own config so the two can never drift apart.
CONFIG = Path(__file__).resolve().parent.parent / "user_data" / "config" / "config.json"
TRADABLE_BALANCE_RATIO = float(json.loads(CONFIG.read_text())["tradable_balance_ratio"])

FEE = 0.0015  # 0.1% commission + 0.05% slippage, per side (same as backtests)
STOPLOSS = -0.08
RISK_PER_TRADE = 0.01
MAX_STAKE_RATIO = 0.25
KILL_SWITCH_DRAWDOWN = 0.20
# Same as the Freqtrade bot (config.json max_open_trades, TrendEma.protections):
MAX_OPEN_TRADES = 3
COOLDOWN_HOURS = 2  # CooldownPeriod: after a trade closes, that pair waits 2 candles
GUARD_LOOKBACK_HOURS, GUARD_STOPS, GUARD_LOCK_HOURS = 24, 3, 12  # StoplossGuard: 3 stops in 24h -> 12h pause
HOUR_MS = 3_600_000


def new_account(cash: float = 1000.0) -> dict:
    return {"cash": cash, "start": cash, "positions": {}, "closed": [], "peak": cash, "realized": cash}


def capital(acc: dict, prices: dict[str, float]) -> float:
    """Cash + current value of every open position."""
    return acc["cash"] + sum(p["amount"] * prices.get(pair, p["entry"]) for pair, p in acc["positions"].items())


def kill_switch_hit(acc: dict) -> bool:
    """Realized equity (start + closed profits) fell 20% from its highest point."""
    return (acc["peak"] - acc["realized"]) / acc["peak"] >= KILL_SWITCH_DRAWDOWN


def risk_capital(acc: dict) -> float:
    """The capital the stake is sized on, exactly like Freqtrade's wallets.get_total_stake_amount():
    (stakes tied up in open trades + free cash) x tradable_balance_ratio. Open trades count at
    their cost, not their market value, so the stake does not move with unrealized profit."""
    return (acc["cash"] + sum(p["stake"] for p in acc["positions"].values())) * TRADABLE_BALANCE_RATIO


def stake_for(acc: dict, prices: dict[str, float], scale: float = 1.0) -> float:
    """How much cash to put in: losing 8% of it must cost at most 1% of capital (max 25%),
    times the VolTarget `scale` (1 = TrendEma; it can only shrink the stake).
    `prices` is no longer needed (risk capital is valued at cost); kept for the callers."""
    cap = risk_capital(acc)
    return min(min(cap * RISK_PER_TRADE / abs(STOPLOSS), cap * MAX_STAKE_RATIO) * min(scale, 1.0), acc["cash"])


def buy(acc: dict, pair: str, price: float, prices: dict[str, float], time: str, scale: float = 1.0) -> str | None:
    """Open a position. Returns a short note, or None if the buy was refused."""
    if pair in acc["positions"]:
        return None  # one position per coin
    if kill_switch_hit(acc):
        return f"KILL SWITCH: no new trades ({pair} refused)"
    stake = stake_for(acc, prices, scale)
    if stake < 10:
        return None  # Binance's minimum order is about 5-10 USDT
    amount = stake * (1 - FEE) / price  # the fee is taken from what we get
    acc["cash"] -= stake
    acc["positions"][pair] = {"amount": amount, "entry": price, "stake": stake, "time": time}
    return f"BUY {pair} {amount:.6f} @ {price:.4f} (stake {stake:.2f}, size {min(scale, 1.0):.0%})"


def sell(acc: dict, pair: str, price: float, time: str, reason: str) -> str | None:
    """Close a position, book its profit and update the kill-switch peak."""
    pos = acc["positions"].pop(pair, None)
    if pos is None:
        return None
    proceeds = pos["amount"] * price * (1 - FEE)
    profit = proceeds - pos["stake"]
    acc["cash"] += proceeds
    acc["realized"] += profit
    acc["peak"] = max(acc["peak"], acc["realized"])
    acc["closed"].append({"pair": pair, "open": pos["time"], "close": time, "profit": profit, "reason": reason})
    return f"SELL {pair} @ {price:.4f} ({reason}) profit {profit:+.2f}"


def stop_hit(acc: dict, pair: str, low: float) -> bool:
    """Did the candle's lowest price touch the -8% stop?"""
    pos = acc["positions"].get(pair)
    return pos is not None and low <= pos["entry"] * (1 + STOPLOSS)


# --- Demo mode (minibot/demo.py): the account follows what the exchange REALLY filled ---------


def open_from_fill(acc: dict, pair: str, filled: float, price: float, fee_usdt: float, time: str) -> str | None:
    """Book a (possibly partial) buy fill: `filled` coins at average `price`, plus the fee in USDT."""
    if filled <= 0:
        return None
    cost = filled * price + fee_usdt
    acc["cash"] -= cost
    acc["positions"][pair] = {"amount": filled, "entry": price, "stake": cost, "time": time}
    return f"BUY {pair} {filled:.6f} @ {price:.4f} (filled, cost {cost:.2f})"


def close_from_fill(acc: dict, pair: str, filled: float, price: float, fee_usdt: float, time: str, reason: str) -> str | None:
    """Book a (possibly partial) sell fill. A partial fill keeps the rest of the position open."""
    pos = acc["positions"].get(pair)
    if pos is None or filled <= 0:
        return None
    part = min(filled / pos["amount"], 1.0)
    proceeds = filled * price - fee_usdt
    stake_part = pos["stake"] * part
    profit = proceeds - stake_part
    acc["cash"] += proceeds
    acc["realized"] += profit
    acc["peak"] = max(acc["peak"], acc["realized"])
    if part >= 0.999:  # (almost) all sold: the position is closed
        acc["positions"].pop(pair)
        acc["closed"].append({"pair": pair, "open": pos["time"], "close": time, "profit": profit, "reason": reason})
    else:
        pos["amount"] -= filled
        pos["stake"] -= stake_part
    return f"SELL {pair} {filled:.6f} @ {price:.4f} ({reason}{', partial' if part < 0.999 else ''}) profit {profit:+.2f}"


# --- Entry gates shared by the paper and the demo bot (same rules as Freqtrade's) -------------


def entry_blocked(acc: dict, pair: str, now_ms: int) -> str | None:
    """Why a new entry on `pair` is not allowed right now, or None."""
    if len(acc["positions"]) >= MAX_OPEN_TRADES:
        return "max open trades"
    # A lock covers its end hour too (<=): matches Freqtrade's backtest (replay check, 2025-04-27 BTC).
    if now_ms <= acc.get("cooldown", {}).get(pair, -1):
        return "cooldown"
    if now_ms <= acc.get("guard_until", -1):
        return "stoploss guard"
    return None


def after_close(acc: dict, pair: str, now_ms: int, reason: str) -> None:
    """Start the pair's cooldown; after 3 stops within 24h lock every pair for 12h."""
    acc.setdefault("cooldown", {})[pair] = now_ms + COOLDOWN_HOURS * HOUR_MS
    if reason == "stoploss":
        stops = [t for t in acc.get("stop_times", []) if t > now_ms - GUARD_LOOKBACK_HOURS * HOUR_MS] + [now_ms]
        acc["stop_times"] = stops
        if len(stops) >= GUARD_STOPS:
            acc["guard_until"] = now_ms + GUARD_LOCK_HOURS * HOUR_MS

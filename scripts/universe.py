"""Which coins a backtest runs on.

core: the 5 coins in config.json (BTC, ETH, SOL, BNB, XRP). We picked them in
      2026, looking back, so they are all "winners that survived". That makes
      results look better than they really are (survivorship bias).

wide: 15 other coins that were among the ~25 biggest by market cap in
      January 2021 (stablecoins and the core 5 left out). Chosen with what
      someone would have known in 2021, so the list includes coins that later
      lost most of their value (EOS, THETA, FIL, VET...). If a rule only works
      on core, it was the coin choice, not the rule.

Stdlib only: ft.py imports this on Kaan's Mac without pandas/freqtrade.
"""

WIDE_2021 = [
    "ADA/USDT", "DOT/USDT", "LTC/USDT", "LINK/USDT", "BCH/USDT",
    "XLM/USDT", "DOGE/USDT", "UNI/USDT", "AAVE/USDT", "TRX/USDT",
    "ATOM/USDT", "VET/USDT", "FIL/USDT", "THETA/USDT", "EOS/USDT",
]  # fmt: skip

# alt2023 (added 2026-11-01, BEFORE any backtest on it; the list is never changed
# after seeing results): a third coin group nobody has tuned anything on.
# Rule: coins that were roughly in the top ~30 by market cap around January 2023,
# minus stablecoins, minus everything already in core or wide. All 16 candidates
# are listed; a coin without Binance spot data is skipped by the tools (logged as
# "No data"), not removed by hand.
# Known bias: picked in 2023, so these coins survived the 2022 crash. Their
# 2021-2022 history therefore looks better than a 2021 choice would (survivorship),
# which is why core/wide remain the main evidence and this is extra evidence.
ALT_2023 = [
    "MATIC/USDT", "AVAX/USDT", "SHIB/USDT", "NEAR/USDT", "ALGO/USDT", "ICP/USDT",
    "ETC/USDT", "HBAR/USDT", "APE/USDT", "SAND/USDT", "MANA/USDT", "EGLD/USDT",
    "XTZ/USDT", "CHZ/USDT", "QNT/USDT", "FTM/USDT",
]  # fmt: skip

UNIVERSES = {"core": None, "wide": WIDE_2021, "alt2023": ALT_2023}  # None = pairs from config.json

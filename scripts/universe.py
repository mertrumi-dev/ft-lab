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

UNIVERSES = {"core": None, "wide": WIDE_2021}  # None = pairs from config.json

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

# alt2024 (added 2026-11-01, BEFORE any backtest on it; never changed after results):
# a fourth untouched group. Rule: coins roughly in the top ~40 by market cap around
# January 2024, minus stablecoins and everything in core, wide or alt2023. All 15
# candidates are listed; coins without Binance spot data are skipped by the tools.
# RENDER traded as RNDR/USDT in January 2024 (renamed later), so the 2024 ticker is used.
# Known limits: many of these coins were listed in 2023, so their train history is
# short (the buy & hold window starts at the latest listing; the tools warn), and
# a 2024 pick means they survived 2023 (survivorship).
ALT_2024 = [
    "APT/USDT", "ARB/USDT", "OP/USDT", "INJ/USDT", "SUI/USDT", "SEI/USDT", "TIA/USDT",
    "STX/USDT", "IMX/USDT", "RNDR/USDT", "LDO/USDT", "RUNE/USDT", "GRT/USDT", "MKR/USDT",
    "KAS/USDT",
]  # fmt: skip

# alt2022 (added 2026-11-01, BEFORE any backtest on it; never changed after results):
# a fifth untouched group. Rule: coins roughly in the top ~60 by market cap around
# January 2022, minus stablecoins and everything in core, wide, alt2023 or alt2024.
# Listed in full, including coins that later collapsed or left Binance (LUNA, FTT,
# WAVES, XMR, HNT): the tools skip pairs without data, so the run says how many
# survived. That skip is itself survivorship bias; it is reported, not hidden.
ALT_2022 = [
    "AXS/USDT", "GALA/USDT", "ENJ/USDT", "KSM/USDT", "ZEC/USDT", "NEO/USDT", "IOTA/USDT",
    "DASH/USDT", "AR/USDT", "CRV/USDT", "LRC/USDT", "FLOW/USDT", "ONE/USDT", "CAKE/USDT",
    "CELO/USDT", "LUNA/USDT", "FTT/USDT", "WAVES/USDT", "XMR/USDT", "HNT/USDT",
]  # fmt: skip

# early (added 2026-11-01, BEFORE any backtest on it): for the "early" slice
# (2018-2020). The big coins that already had Binance USDT pairs in the first
# half of 2018. SOL did not exist yet, so core cannot run there. Known bias:
# picked in 2026, and all of these still trade (survivorship).
EARLY_2018 = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "LTC/USDT", "ADA/USDT", "NEO/USDT",
    "EOS/USDT", "XLM/USDT", "TRX/USDT", "ETC/USDT", "QTUM/USDT", "IOTA/USDT",
]  # fmt: skip

# pool (2026-11-01): every coin from every group above, for strategies that pick
# their own coins (TrendEmaVolTargetTopVol ranks them by 30-day volume). The core
# coins come first; pairs without data are skipped by the tools.
CORE_5 = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
POOL = list(dict.fromkeys(CORE_5 + WIDE_2021 + ALT_2022 + ALT_2023 + ALT_2024))

# core_gold (2026-11-01, research): the 5 core coins + tokenized gold, a different asset
# class (Hurst, Ooi & Pedersen 2017: trend following works best across uncorrelated markets).
CORE_GOLD = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "PAXG/USDT"]

UNIVERSES = {
    "pool": POOL,
    "early": EARLY_2018,
    "core": None, "core_gold": CORE_GOLD, "wide": WIDE_2021, "alt2022": ALT_2022, "alt2023": ALT_2023, "alt2024": ALT_2024,
}  # None = pairs from config.json

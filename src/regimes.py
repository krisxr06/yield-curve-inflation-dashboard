"""
Regime classification module.

Yield Curve Regimes (applied in strict priority order):
    1. Re-steepening  – highest priority; overrides all others
    2. Inverted
    3. Flat
    4. Normal

Inflation Regimes:
    Level     : Low (<2%), Moderate (2–4%), High (>4%)
    Direction : Rising (>+0.5 ppt 3m chg), Falling (<-0.5 ppt), Stable
    Combined  : e.g. "High / Falling"

Documented assumptions:
    - When cpi_yoy_3m_chg is NaN (first 3 months of CPI YoY series), direction
      defaults to "Stable" — conservative assumption that avoids spurious
      directional signals at the start of the series.
    - "Unknown" is assigned when the required input metric is NaN.
"""

import pandas as pd

# ── Yield Curve ────────────────────────────────────────────────────────────────

YC_REGIMES = ["Inverted", "Re-steepening", "Flat", "Normal"]

YC_COLORS = {
    "Inverted":      "rgba(204,  51,  51, 0.22)",
    "Re-steepening": "rgba(230, 150,  30, 0.22)",
    "Flat":          "rgba(210, 195,  50, 0.22)",
    "Normal":        "rgba( 50, 180,  80, 0.22)",
    "Unknown":       "rgba(150, 150, 150, 0.10)",
}

# ── Inflation ──────────────────────────────────────────────────────────────────

INF_LEVELS     = ["High", "Moderate", "Low"]
INF_DIRECTIONS = ["Rising", "Stable", "Falling"]
INF_REGIMES    = [f"{lvl} / {d}" for lvl in INF_LEVELS for d in INF_DIRECTIONS]

INF_LEVEL_COLORS = {
    "High":     "rgba(204,  80,  60, 0.18)",
    "Moderate": "rgba(210, 160,  50, 0.18)",
    "Low":      "rgba( 60, 140, 210, 0.18)",
    "Unknown":  "rgba(150, 150, 150, 0.10)",
}


# ── Classification helpers ─────────────────────────────────────────────────────

def classify_yc_regimes(df: pd.DataFrame) -> pd.Series:
    """
    Vectorised yield curve regime classification.

    Re-steepening conditions (ALL must hold):
        • The spread was negative at any point in the prior 6 calendar months
          (shift(1) excludes current month; rolling(6) looks 6 months back).
        • The spread has risen more than 0.25 ppts over the last 3 months.
        • The current spread is between -0.25 and +0.75 ppts (inclusive).

    Priority is enforced by applying rules lowest→highest, so the last
    assignment wins (Re-steepening overwrites Inverted/Flat/Normal).
    """
    spread    = df["spread_10y2y"]
    spread_3m = df["spread_3m_chg"]

    # Was spread negative at any point in the prior 6 months?
    had_neg_prior_6m = spread.shift(1).rolling(6, min_periods=1).min() < 0

    cond_re_steep = (
        had_neg_prior_6m
        & (spread_3m > 0.25)
        & (spread >= -0.25)
        & (spread <= 0.75)
    )

    # Apply in ascending priority (highest priority applied last)
    regimes = pd.Series("Unknown", index=df.index, dtype=object)
    regimes[spread > 0.50]                     = "Normal"
    regimes[(spread >= 0) & (spread <= 0.50)]  = "Flat"
    regimes[spread < 0]                        = "Inverted"
    regimes[cond_re_steep]                     = "Re-steepening"  # highest priority
    regimes[spread.isna()]                     = "Unknown"

    return regimes.rename("yc_regime")


def classify_inf_regimes(df: pd.DataFrame) -> pd.Series:
    """
    Vectorised inflation regime classification → 'Level / Direction'.

    Direction defaults to 'Stable' when cpi_yoy_3m_chg is NaN (early history).
    """
    cpi    = df["cpi_yoy"]
    cpi_3m = df["cpi_yoy_3m_chg"]

    # Level
    level = pd.Series("Unknown", index=df.index, dtype=object)
    level[cpi < 2]                  = "Low"
    level[(cpi >= 2) & (cpi <= 4)]  = "Moderate"
    level[cpi > 4]                  = "High"
    level[cpi.isna()]               = "Unknown"

    # Direction (NaN → Stable per documented assumption)
    direction = pd.Series("Stable", index=df.index, dtype=object)
    direction[cpi_3m > 0.5]   = "Rising"
    direction[cpi_3m < -0.5]  = "Falling"

    combined = level + " / " + direction
    combined[level == "Unknown"] = "Unknown"

    return combined.rename("inf_regime")


def add_regimes(df: pd.DataFrame) -> pd.DataFrame:
    """Append yc_regime and inf_regime columns to the transformed DataFrame."""
    df = df.copy()
    df["yc_regime"]  = classify_yc_regimes(df)
    df["inf_regime"] = classify_inf_regimes(df)
    return df

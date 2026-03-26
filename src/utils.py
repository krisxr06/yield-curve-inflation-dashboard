"""
Utility functions: extract latest values and generate plain-English summaries.
"""

from __future__ import annotations

import pandas as pd


# ── Latest values ──────────────────────────────────────────────────────────────

def latest_values(df: pd.DataFrame) -> dict:
    """
    Extract the most recent non-null value for each key metric.

    Returns a dict with keys:
        date, cpi_yoy, fedfunds, dgs2, dgs10, spread, yc_regime, inf_regime
    """
    def _last(col: str):
        if col not in df.columns:
            return float("nan")
        s = df[col].dropna()
        return s.iloc[-1] if not s.empty else float("nan")

    try:
        # Use last row that has at least one core market metric
        date = df[["CPIAUCSL", "DGS10", "DGS2"]].dropna(how="all").index[-1]
    except (IndexError, KeyError):
        date = df.index[-1] if not df.empty else pd.Timestamp.now()

    yc  = _last("yc_regime")
    inf = _last("inf_regime")

    return {
        "date":       date,
        "cpi_yoy":    _last("cpi_yoy"),
        "fedfunds":   _last("FEDFUNDS"),
        "dgs2":       _last("DGS2"),
        "dgs10":      _last("DGS10"),
        "spread":     _last("spread_10y2y"),
        "yc_regime":  str(yc)  if not _is_nan(yc)  else "Unknown",
        "inf_regime": str(inf) if not _is_nan(inf) else "Unknown",
    }


def _is_nan(v) -> bool:
    try:
        return pd.isna(v)
    except (TypeError, ValueError):
        return False


def _fmt(val, suffix: str = "", decimals: int = 2, signed: bool = False) -> str:
    if _is_nan(val):
        return "N/A"
    sign = "+" if signed and float(val) >= 0 else ""
    return f"{sign}{float(val):.{decimals}f}{suffix}"


# ── Section 1: Macro snapshot summary ─────────────────────────────────────────

def macro_snapshot_summary(vals: dict) -> str:
    """
    Return a 2–3 sentence Markdown string summarising the current macro setup
    and its implications for fixed-income risk.
    """
    yc      = vals.get("yc_regime", "Unknown")
    inf     = vals.get("inf_regime", "Unknown")
    spread  = vals.get("spread", float("nan"))
    cpi     = vals.get("cpi_yoy", float("nan"))
    ff      = vals.get("fedfunds", float("nan"))

    spread_s = _fmt(spread, suffix=" ppts", signed=True)
    cpi_s    = _fmt(cpi,    suffix="%", decimals=1)
    ff_s     = _fmt(ff,     suffix="%")

    level, _, direction = inf.partition(" / ")

    yc_sentences = {
        "Inverted":      f"Yield curve: **inverted** ({spread_s}).",
        "Re-steepening": f"Yield curve: **re-steepening** ({spread_s}) following a period of inversion.",
        "Flat":          f"Yield curve: **flat** ({spread_s}).",
        "Normal":        f"Yield curve: **normal** ({spread_s}).",
    }
    yc_sent = yc_sentences.get(yc, f"Yield curve: **{yc}** ({spread_s}).")

    inf_sent = f"CPI YoY **{cpi_s}** (*{inf}*); Fed Funds **{ff_s}**."

    risk_map: dict[tuple, str] = {
        ("Inverted",      "High"):     "Historically associated with elevated nominal yield volatility and compressed real returns.",
        ("Inverted",      "Moderate"): "Historically preceded easing cycles; timing and magnitude have varied across episodes.",
        ("Inverted",      "Low"):      "Historically observed ahead of policy pivots; outcomes dependent on cycle severity.",
        ("Re-steepening", "High"):     "Historically associated with rising long yields alongside persistent inflation pressure.",
        ("Re-steepening", "Moderate"): "Historically a transition environment; outcomes have varied by steepening driver.",
        ("Re-steepening", "Low"):      "Historically accompanied late-cycle dynamics with varied duration outcomes.",
        ("Flat",          "High"):     "Historically associated with constrained returns across most fixed-income maturities.",
        ("Flat",          "Moderate"): "Historically a range-bound rate environment; carry has driven outcomes more than price.",
        ("Flat",          "Low"):      "Historically associated with contained rate volatility ahead of more directional shifts.",
        ("Normal",        "High"):     "Historically associated with elevated nominal yields; real returns dependent on inflation trajectory.",
        ("Normal",        "Moderate"): "Historically associated with relatively more stable fixed-income conditions relative to inversion or high-inflation regimes.",
        ("Normal",        "Low"):      "Historically associated with lower nominal yield volatility and positive duration performance.",
    }
    risk_sent = risk_map.get(
        (yc, level),
        "Historical record for this combination is limited — outcomes have varied across episodes.",
    )

    disclaimer = (
        "*This framework is descriptive rather than predictive — intended to contextualize "
        "macro environments, not forecast them.*"
    )

    return f"{yc_sent}  \n{inf_sent}  \n{risk_sent}  \n{disclaimer}"


# ── Section 2: Yield curve chart explanation ──────────────────────────────────

def yc_chart_explanation(yc_regime: str) -> str:
    texts = {
        "Inverted":      "Negative 10Y–2Y spread. Historically preceded easing cycles, though lead times have varied widely across episodes.",
        "Re-steepening": "Spread widening following inversion — amber shading marks months where spread was recently negative and has risen more than 25 bps. Historically a transition regime.",
        "Flat":          "Narrow gap between short and long yields. Historically observed during tightening cycles and ahead of policy pivots — directional context matters.",
        "Normal":        "Upward-sloping curve (baseline state). Historically associated with lower macro stress relative to inversion periods — slope alone does not determine outcomes.",
    }
    return texts.get(yc_regime, "Insufficient spread history for classification.")


# ── Section 3: Inflation chart explanation ────────────────────────────────────

def inf_chart_explanation(inf_regime: str) -> str:
    level = inf_regime.split(" / ")[0] if " / " in inf_regime else inf_regime
    texts = {
        "High":     "Above 4% (red). Historically coincided with active tightening cycles and elevated nominal yields — real return outcomes dependent on inflation trajectory.",
        "Moderate": "2–4% (amber). Historically associated with more anchored expectations and predictable policy relative to High inflation episodes.",
        "Low":      "Below 2% (blue). Historically coincided with disinflationary or below-trend growth environments.",
    }
    return texts.get(level, "Insufficient CPI history for classification.")


# ── Section 4: Heatmap interpretation ────────────────────────────────────────

def heatmap_interpretation(df: pd.DataFrame, current_yc: str, current_inf: str) -> str:
    """
    Generate a plain-English interpretation of notable historical co-occurrences
    and contextualize the current combination.
    """
    valid = df[
        (df["yc_regime"] != "Unknown") & (df["inf_regime"] != "Unknown")
    ].copy()
    total = len(valid)
    if total == 0:
        return "Insufficient data for interpretation."

    # Current combination
    cur = len(valid[
        (valid["yc_regime"] == current_yc) & (valid["inf_regime"] == current_inf)
    ])
    cur_pct = cur / total * 100

    # Most common single combination
    combo = valid.groupby(["yc_regime", "inf_regime"]).size()
    top_yc, top_inf = combo.idxmax()
    top_n   = combo.max()
    top_pct = top_n / total * 100

    # Key combination counts
    inv_high = len(valid[
        (valid["yc_regime"] == "Inverted") & valid["inf_regime"].str.startswith("High")
    ])
    norm_low = len(valid[
        (valid["yc_regime"] == "Normal") & valid["inf_regime"].str.startswith("Low")
    ])
    re_steep = len(valid[valid["yc_regime"] == "Re-steepening"])

    lines = [
        f"- **Most common:** Normal / Moderate — {top_pct:.0f}% of classified history.",
        f"- **Inverted + High inflation:** {inv_high/total*100:.0f}% of history — historically associated with more stressed macro conditions (concentrated 1970s–80s).",
        f"- **Normal + Low inflation:** {norm_low/total*100:.0f}% of history — historically characterized as lower-volatility macro environments.",
        f"- **Re-steepening:** {re_steep/total*100:.0f}% of history — rare, typically observed during post-inversion transitions.",
        f"- **Current regime** (*{current_yc} / {current_inf}*): {cur} of {total} classified months ({cur_pct:.0f}%).",
    ]

    return "  \n".join(lines)


# ── Section 5: Yield Curve → Portfolio Interpretation ────────────────────────

def get_yield_curve_interpretation(yc_regime: str, inf_regime: str) -> dict:
    """
    Translate the current yield curve and inflation regime into descriptive
    portfolio risk labels and positioning context.

    This is NOT a trading signal or investment recommendation.
    All outputs are rule-based interpretations of historical regime patterns.

    Parameters
    ----------
    yc_regime  : e.g. "Normal", "Flat", "Inverted", "Re-steepening"
    inf_regime : e.g. "Moderate / Falling" — only the level prefix is used
                 for inflation pressure labeling

    Returns a dict with keys:
        policy_environment, rate_stability, inflation_pressure,
        duration_risk, carry, curve_trades, bullets
    """
    # ── Interpretation labels ─────────────────────────────────────────────────
    policy_map = {
        "Normal":        "Expansionary",
        "Flat":          "Late-cycle / Transition",
        "Inverted":      "Restrictive / Late-cycle",
        "Re-steepening": "Policy shift / Transition",
    }

    stability_map = {
        "Normal":        "Stable",
        "Flat":          "Moderate uncertainty",
        "Inverted":      "Unstable",
        "Re-steepening": "Highly unstable",
    }

    # Extract inflation level ("High", "Moderate", "Low") from full regime string
    inf_level = inf_regime.split(" / ")[0] if " / " in inf_regime else inf_regime
    pressure_map = {
        "High":     "Elevated",
        "Moderate": "Persistent",
        "Low":      "Contained",
    }

    # ── Portfolio lens labels ─────────────────────────────────────────────────
    duration_map = {
        "Normal":        "Moderate",
        "Flat":          "Moderate",
        "Inverted":      "Elevated",
        "Re-steepening": "High",
    }

    carry_map = {
        "Normal":        "Supportive",
        "Flat":          "Neutral",
        "Inverted":      "Weak",
        "Re-steepening": "Weak",
    }

    curve_trades_map = {
        "Normal":        "Attractive",
        "Flat":          "Limited",
        "Inverted":      "Unclear",
        "Re-steepening": "Unstable",
    }

    # ── Positioning implication bullets ──────────────────────────────────────
    # Observational language only — not trade recommendations.
    bullets_map = {
        "Normal": [
            "Historically associated with lower macro stress relative to inversion or transition regimes.",
            "Duration positioning has tended to be more stable when the curve maintains a normal slope.",
            "Carry advantages are generally more accessible in this environment relative to flat or inverted regimes.",
        ],
        "Flat": [
            "Flat curves have historically reduced carry advantages across maturities.",
            "Positioning tends to depend more on macro shifts than curve shape alone.",
            "Transition risk increases if policy expectations shift.",
        ],
        "Inverted": [
            "Historically associated with elevated policy uncertainty and compressed term premium.",
            "Duration outcomes have been less predictable than the curve shape alone might suggest.",
            "Carry conditions have historically been weak relative to normal or flat regimes.",
        ],
        "Re-steepening": [
            "Historically the most volatile transition environment in the sample.",
            "Curve positioning has tended to be less reliable as rate repricing occurs unevenly.",
            "Optionality has typically become more relevant during these episodes.",
        ],
    }

    return {
        "policy_environment": policy_map.get(yc_regime, "Unknown"),
        "rate_stability":     stability_map.get(yc_regime, "Unknown"),
        "inflation_pressure": pressure_map.get(inf_level, "Unknown"),
        "duration_risk":      duration_map.get(yc_regime, "N/A"),
        "carry":              carry_map.get(yc_regime, "N/A"),
        "curve_trades":       curve_trades_map.get(yc_regime, "N/A"),
        "bullets":            bullets_map.get(yc_regime, ["Insufficient regime history for positioning context."]),
    }

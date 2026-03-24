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

    # Yield-curve sentence
    yc_sentences = {
        "Inverted": (
            f"The yield curve is currently **inverted** ({spread_s}), "
            "a historically reliable signal of deteriorating credit conditions "
            "and eventual monetary easing."
        ),
        "Re-steepening": (
            f"The yield curve is **re-steepening** ({spread_s}) after a period of inversion — "
            "historically one of the most watched patterns because bear steepeners "
            "often precede, rather than follow, recession onset."
        ),
        "Flat": (
            f"The yield curve is **flat** ({spread_s}), offering little term premium "
            "and signalling uncertainty about the growth and policy outlook."
        ),
        "Normal": (
            f"The yield curve is upward sloping ({spread_s}), which has historically been "
            "associated with more stable macro conditions relative to inversion periods."
        ),
    }
    yc_sent = yc_sentences.get(yc, f"The yield curve regime is **{yc}** ({spread_s}).")

    # Inflation sentence
    level, _, direction = inf.partition(" / ")
    inf_sent = (
        f"Inflation is running at **{cpi_s} YoY** — "
        f"classified as *{inf}*, alongside a Fed Funds Rate of {ff_s}."
    )

    # Observational fixed-income context (descriptive, not prescriptive)
    risk_map: dict[tuple, str] = {
        ("Inverted",      "High"):     "Historically, this combination has been associated with significant nominal yield volatility and compressed real returns across the fixed-income complex.",
        ("Inverted",      "Moderate"): "Inverted curves with moderate inflation have historically preceded easing cycles, though the timing and magnitude vary considerably across episodes.",
        ("Inverted",      "Low"):      "Inversions accompanied by low inflation have historically occurred ahead of policy pivots, though outcomes have varied depending on the severity of the underlying slowdown.",
        ("Re-steepening", "High"):     "Re-steepening into elevated inflation has historically been associated with difficult fixed-income conditions — rising long yields alongside persistent price pressure.",
        ("Re-steepening", "Moderate"): "This combination has historically marked transition periods; outcomes across fixed-income segments have been mixed depending on whether the steepening was driven by the front or long end.",
        ("Re-steepening", "Low"):      "Re-steepening with low inflation has historically accompanied late-cycle dynamics, with varied duration outcomes depending on the pace of policy normalisation.",
        ("Flat",          "High"):     "Flat curves combined with high inflation have historically coincided with constrained nominal and real returns across most fixed-income maturities.",
        ("Flat",          "Moderate"): "This combination has historically been associated with range-bound rate environments, with carry rather than price return driving fixed-income outcomes.",
        ("Flat",          "Low"):      "Flat curves with low inflation have historically aligned with relatively contained rate volatility, though they also tend to precede more directional regime shifts.",
        ("Normal",        "High"):     "Normal slope with elevated inflation has historically been associated with elevated nominal yields and compressed real returns until inflation direction becomes clearer.",
        ("Normal",        "Moderate"): "This combination has historically been associated with more stable fixed-income environments relative to inversion or high-inflation regimes.",
        ("Normal",        "Low"):      "Normal curve combined with low inflation has historically coincided with periods of positive duration performance and lower nominal yield volatility.",
    }
    risk_sent = risk_map.get(
        (yc, level),
        "The historical record for this combination is limited — outcomes have varied across episodes.",
    )

    disclaimer = (
        "*This framework is descriptive rather than predictive, and is intended "
        "to contextualize macro environments rather than forecast them.*"
    )

    return f"{yc_sent}  \n{inf_sent}  \n{risk_sent}  \n{disclaimer}"


# ── Section 2: Yield curve chart explanation ──────────────────────────────────

def yc_chart_explanation(yc_regime: str) -> str:
    texts = {
        "Inverted": (
            "An <b>inverted</b> yield curve (negative 10Y–2Y spread) has preceded every U.S. recession "
            "since the 1970s, though the lead time has varied widely across cycles (roughly 6–24 months). "
            "Structurally, inversion occurs when near-term short rates exceed long yields — "
            "typically reflecting market pricing for eventual rate cuts rather than a directional forecast."
        ),
        "Re-steepening": (
            "A <b>re-steepening</b> following inversion has historically occurred during transition periods. "
            "In several prior cycles, the spread widened back out <em>before</em> recession onset rather than after, "
            "particularly in bear-steepening episodes driven by rising long yields. "
            "The amber shading identifies months where the spread was recently negative and has since widened by more than 25 bps."
        ),
        "Flat": (
            "A <b>flat</b> curve reflects a narrow gap between short and long yields. "
            "It has historically appeared during transitions — either as the front end rises toward inversion "
            "during tightening cycles, or as short rates fall ahead of policy easing. "
            "The directional context matters more than the level in isolation."
        ),
        "Normal": (
            "A <b>normal</b>, upward-sloping curve is the structural baseline: longer maturities "
            "carry higher yields to compensate for duration and uncertainty. "
            "Historically, this regime has been associated with periods of lower macro stress "
            "relative to inversion — though the slope alone does not determine outcomes."
        ),
    }
    return texts.get(yc_regime, "Regime classification requires sufficient spread history.")


# ── Section 3: Inflation chart explanation ────────────────────────────────────

def inf_chart_explanation(inf_regime: str) -> str:
    level = inf_regime.split(" / ")[0] if " / " in inf_regime else inf_regime
    texts = {
        "High": (
            "<b>High inflation</b> (above 4%, red shading) has historically coincided with active Fed "
            "tightening cycles and elevated nominal yields across the curve. "
            "Real return outcomes have varied considerably depending on the trajectory of inflation "
            "and whether the tightening cycle was near its end."
        ),
        "Moderate": (
            "The <b>2–4% band</b> (amber shading) broadly encompasses the Fed's stated target range. "
            "Historically, this regime has been associated with more anchored inflation expectations "
            "and more predictable policy relative to High episodes — though individual outcomes "
            "have depended on the direction of travel within the band."
        ),
        "Low": (
            "<b>Sub-2% inflation</b> (blue shading) has historically coincided with below-trend growth "
            "or disinflationary periods. Duration has tended to perform relatively well in this regime "
            "historically, though causality and sequencing vary across episodes."
        ),
    }
    return texts.get(level, "Inflation regime classification requires CPI data.")


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
        f"The most common historical environment is a **Normal curve combined with Moderate inflation**, "
        f"representing approximately **{top_pct:.0f}%** of observed classified periods.",

        f"**Inverted curve + High inflation** ({inv_high/total*100:.0f}% of history) appears less frequently "
        "but is historically associated with more stressed macro conditions, concentrated in the 1970s–80s.",

        f"**Normal curve + Low inflation** ({norm_low/total*100:.0f}% of history) aligns with periods "
        "often characterized as low-volatility macro environments in the historical record.",

        f"**Re-steepening regimes** ({re_steep/total*100:.0f}% of history) are relatively rare and "
        "typically occur during transitions following inversion, making them structurally important "
        "transition periods despite their low frequency.",

        f"The **current regime** (*{current_yc} / {current_inf}*) has occurred in "
        f"**{cur} of {total} classified months** ({cur_pct:.0f}% of history), "
        "placing it among the more frequently observed macro environments.",
    ]

    return "  \n\n".join(lines)

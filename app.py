"""
Yield Curve × Inflation Regime Dashboard
=========================================
Main Streamlit application.

Sections
--------
1. Current Macro Snapshot  – metric cards + plain-English summary
2. Yield Curve History      – spread chart with regime shading
3. Inflation History        – CPI YoY chart with level shading
4. Regime Interaction       – heatmap + summary table + interpretation
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make src/ importable when running from project root
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import load_all
from src.transforms  import apply_transforms
from src.regimes     import add_regimes
from src.charts      import yield_curve_chart, inflation_chart, regime_heatmap
from src.utils       import (
    latest_values,
    macro_snapshot_summary,
    yc_chart_explanation,
    inf_chart_explanation,
    heatmap_interpretation,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Yield Curve × Inflation Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ---- metric card ---- */
[data-testid="metric-container"] {
    background: #1a1d2e;
    border: 1px solid #2a2f45;
    border-radius: 10px;
    padding: 14px 18px 10px;
}
/* ---- regime badge colours ---- */
.badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.badge-inverted   { background:#3a0e0e; color:#ff7070; border:1px solid #6b1f1f; }
.badge-resteep    { background:#362200; color:#ffb347; border:1px solid #6b4a00; }
.badge-flat       { background:#2e2900; color:#e8d44d; border:1px solid #5a5000; }
.badge-normal     { background:#0d2914; color:#5dde7c; border:1px solid #1e5c30; }
.badge-unknown    { background:#1e2030; color:#9da5b4; border:1px solid #3a3f55; }
/* ---- divider ---- */
.divider { border-top:1px solid #2a2f45; margin:28px 0 20px; }
/* ---- explanation text ---- */
.explanation {
    font-size: 14px; color: #9ca3b0;
    line-height: 1.75; padding: 10px 2px 0;
}
</style>
""", unsafe_allow_html=True)


# ── Data (cached for 1 h) ──────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_data() -> pd.DataFrame:
    raw         = load_all()
    transformed = apply_transforms(raw)
    return add_regimes(transformed)


with st.spinner("Fetching FRED data…"):
    df = get_data()

vals        = latest_values(df)
current_yc  = vals["yc_regime"]
current_inf = vals["inf_regime"]


# ── Header ─────────────────────────────────────────────────────────────────────
st.title("📈 Yield Curve × Inflation Regime Dashboard")
try:
    date_str = vals["date"].strftime("%B %Y")
except Exception:
    date_str = "latest available"
st.caption(f"Data through **{date_str}** · Source: Federal Reserve Economic Data (FRED)")
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Current Macro Snapshot
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("1 — Current Macro Snapshot")

def _fmt(val, suffix: str = "", decimals: int = 2, signed: bool = False) -> str:
    try:
        if pd.isna(val):
            return "N/A"
        sign = "+" if signed and float(val) >= 0 else ""
        return f"{sign}{float(val):.{decimals}f}{suffix}"
    except Exception:
        return str(val)

# Row 1: four numeric metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("CPI YoY",        _fmt(vals["cpi_yoy"],  "%",  1))
c2.metric("Fed Funds Rate", _fmt(vals["fedfunds"], "%"))
c3.metric("2Y Treasury",    _fmt(vals["dgs2"],     "%"))
c4.metric("10Y Treasury",   _fmt(vals["dgs10"],    "%"))

st.write("")

# Row 2: spread + regime badges
c5, c6, c7 = st.columns(3)
c5.metric("10Y–2Y Spread", _fmt(vals["spread"], " ppts", signed=True))

_badge_class = {
    "Inverted":      "badge-inverted",
    "Re-steepening": "badge-resteep",
    "Flat":          "badge-flat",
    "Normal":        "badge-normal",
}.get(current_yc, "badge-unknown")

with c6:
    st.markdown("**Yield Curve Regime**")
    st.markdown(
        f"<span class='badge {_badge_class}'>{current_yc}</span>",
        unsafe_allow_html=True,
    )

with c7:
    st.markdown("**Inflation Regime**")
    st.markdown(
        f"<span style='font-size:17px; font-weight:600; color:#e8eaf0;'>{current_inf}</span>",
        unsafe_allow_html=True,
    )

st.write("")
st.info(macro_snapshot_summary(vals), icon="💡")
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Yield Curve History
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("2 — Yield Curve History")
st.plotly_chart(yield_curve_chart(df), use_container_width=True)
st.markdown(
    f"<div class='explanation'>{yc_chart_explanation(current_yc)}</div>",
    unsafe_allow_html=True,
)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Inflation History
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("3 — Inflation History")
st.plotly_chart(inflation_chart(df), use_container_width=True)
st.markdown(
    f"<div class='explanation'>{inf_chart_explanation(current_inf)}</div>",
    unsafe_allow_html=True,
)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Regime Interaction
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("4 — Regime Interaction  *(historical co-occurrence)*")

st.plotly_chart(regime_heatmap(df, current_yc, current_inf), use_container_width=True)

# ── Summary table ──────────────────────────────────────────────────────────────
st.markdown("#### Co-occurrence Summary Table")

valid_df = df[
    (df["yc_regime"] != "Unknown") & (df["inf_regime"] != "Unknown")
].copy()

if not valid_df.empty:
    summary = (
        valid_df.groupby(["yc_regime", "inf_regime"])
        .size()
        .reset_index(name="Months")
        .assign(Years=lambda x: (x["Months"] / 12).round(1))
        .assign(**{"% of History": lambda x: (x["Months"] / x["Months"].sum() * 100).round(1)})
        .rename(columns={"yc_regime": "Yield Curve Regime", "inf_regime": "Inflation Regime"})
        .sort_values("Months", ascending=False)
        .reset_index(drop=True)
    )

    def _highlight(row):
        if (
            row["Yield Curve Regime"] == current_yc
            and row["Inflation Regime"] == current_inf
        ):
            return ["background-color: #1a3a5c; font-weight: bold"] * len(row)
        return [""] * len(row)

    st.dataframe(
        summary.style.apply(_highlight, axis=1),
        use_container_width=True,
        hide_index=True,
        height=340,
    )

# ── Plain-English interpretation ───────────────────────────────────────────────
st.write("")
st.markdown(heatmap_interpretation(df, current_yc, current_inf))

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.caption(
    "Data: Federal Reserve Economic Data (FRED) · "
    "Series: CPIAUCSL, FEDFUNDS, DGS2, DGS10 · "
    "Built with Streamlit & Plotly"
)

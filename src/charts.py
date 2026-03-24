"""
Chart creation module.

Each public function accepts a fully-transformed + regime-labelled DataFrame
and returns a plotly Figure ready to embed in Streamlit.

Charts
------
yield_curve_chart  : 10Y–2Y spread time series with yield curve regime shading
inflation_chart    : YoY CPI time series with inflation level shading
regime_heatmap     : Month-count heatmap of (YC regime × inflation regime)
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .regimes import YC_COLORS, INF_LEVEL_COLORS, YC_REGIMES, INF_REGIMES

_TEMPLATE    = "plotly_dark"
_FONT_FAMILY = "Inter, 'Helvetica Neue', Arial, sans-serif"
_GRID_COLOR  = "rgba(255,255,255,0.07)"
_ZERO_COLOR  = "rgba(255,255,255,0.35)"


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _regime_periods(series: pd.Series) -> list[tuple]:
    """
    Convert a Series of regime labels into (start_date, end_date, label) spans.
    Consecutive identical labels are merged into a single period.
    """
    if series.empty:
        return []
    periods: list[tuple] = []
    current = series.iloc[0]
    start   = series.index[0]
    for ts, val in series.items():
        if val != current:
            periods.append((start, ts, current))
            current, start = val, ts
    periods.append((start, series.index[-1], current))
    return periods


def _add_regime_shading(fig: go.Figure, series: pd.Series, color_map: dict) -> None:
    """Add coloured vrect blocks for each regime period."""
    for start, end, label in _regime_periods(series):
        if start >= end:
            continue
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=color_map.get(label, "rgba(150,150,150,0.10)"),
            opacity=1.0,
            layer="below",
            line_width=0,
        )


# ── Section 2: Yield Curve History ────────────────────────────────────────────

def yield_curve_chart(df: pd.DataFrame) -> go.Figure:
    """
    Time series of 10Y–2Y spread with yield curve regime background shading.

    Colour coding:
        Inverted      → red
        Re-steepening → amber
        Flat          → yellow
        Normal        → green
    """
    valid = df[["spread_10y2y", "yc_regime"]].dropna(subset=["spread_10y2y"])
    if valid.empty:
        return go.Figure().update_layout(template=_TEMPLATE, title="No data available")

    fig = go.Figure()
    _add_regime_shading(fig, valid["yc_regime"], YC_COLORS)

    # Zero reference line
    fig.add_hline(y=0, line_dash="dot", line_color=_ZERO_COLOR, line_width=1)

    # Spread line
    fig.add_trace(go.Scatter(
        x=valid.index,
        y=valid["spread_10y2y"],
        mode="lines",
        name="10Y–2Y",
        line=dict(color="#7EB6FF", width=1.5),
        hovertemplate="%{x|%b %Y}: %{y:+.2f} ppts<extra></extra>",
    ))

    # Inline colour legend via annotations
    legend_items = [
        ("Inverted",      "#dc5050"),
        ("Re-steepening", "#e6962a"),
        ("Flat",          "#d4c44a"),
        ("Normal",        "#46b855"),
    ]
    annotations = []
    for i, (label, color) in enumerate(legend_items):
        annotations.append(dict(
            x=i * 0.26, y=1.07,
            xref="paper", yref="paper",
            text=f"<span style='color:{color}'>■</span> {label}",
            showarrow=False,
            font=dict(size=11, family=_FONT_FAMILY),
        ))

    fig.update_layout(
        template=_TEMPLATE,
        title=dict(text="10Y–2Y Treasury Spread & Yield Curve Regimes", font=dict(size=15)),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="Spread (ppts)", showgrid=True, gridcolor=_GRID_COLOR),
        hovermode="x unified",
        showlegend=False,
        font=dict(family=_FONT_FAMILY),
        margin=dict(l=60, r=20, t=65, b=40),
        height=390,
        annotations=annotations,
    )
    return fig


# ── Section 3: Inflation History ──────────────────────────────────────────────

def inflation_chart(df: pd.DataFrame) -> go.Figure:
    """
    Time series of YoY CPI with inflation *level* regime background shading.

    Colour coding:
        High (>4%)       → red
        Moderate (2–4%)  → amber/green
        Low (<2%)        → blue
    """
    valid = df[["cpi_yoy", "inf_regime"]].dropna(subset=["cpi_yoy"])
    if valid.empty:
        return go.Figure().update_layout(template=_TEMPLATE, title="No data available")

    # Extract level component for shading
    level_series = valid["inf_regime"].str.split(" / ").str[0]

    fig = go.Figure()
    _add_regime_shading(fig, level_series, INF_LEVEL_COLORS)

    # Reference lines
    for y_val, label in [(2.0, "2% target"), (4.0, "4%")]:
        fig.add_hline(
            y=y_val, line_dash="dot", line_color=_ZERO_COLOR, line_width=1,
            annotation_text=label, annotation_position="right",
            annotation_font=dict(size=10, family=_FONT_FAMILY),
        )

    # CPI line
    fig.add_trace(go.Scatter(
        x=valid.index,
        y=valid["cpi_yoy"],
        mode="lines",
        name="CPI YoY",
        line=dict(color="#FFB347", width=1.5),
        hovertemplate="%{x|%b %Y}: %{y:.1f}%<extra></extra>",
    ))

    legend_items = [
        ("High >4%",       "#cc503c"),
        ("Moderate 2–4%",  "#d2a032"),
        ("Low <2%",        "#3c8cd2"),
    ]
    annotations = []
    for i, (label, color) in enumerate(legend_items):
        annotations.append(dict(
            x=i * 0.34, y=1.07,
            xref="paper", yref="paper",
            text=f"<span style='color:{color}'>■</span> {label}",
            showarrow=False,
            font=dict(size=11, family=_FONT_FAMILY),
        ))

    fig.update_layout(
        template=_TEMPLATE,
        title=dict(text="YoY CPI Inflation & Inflation Regimes", font=dict(size=15)),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="YoY CPI (%)", showgrid=True, gridcolor=_GRID_COLOR),
        hovermode="x unified",
        showlegend=False,
        font=dict(family=_FONT_FAMILY),
        margin=dict(l=60, r=70, t=65, b=40),
        height=390,
        annotations=annotations,
    )
    return fig


# ── Section 4: Regime Interaction Heatmap ─────────────────────────────────────

def regime_heatmap(df: pd.DataFrame, current_yc: str, current_inf: str) -> go.Figure:
    """
    Heatmap of historical month counts for each
    (yield curve regime × inflation regime) combination.

    Axes
    ----
    X : Yield curve regime  (Inverted → Re-steepening → Flat → Normal)
    Y : Inflation regime    (High/Rising … Low/Falling)

    The current combination is annotated with "▶ NOW".
    """
    valid = df[
        (df["yc_regime"] != "Unknown") & (df["inf_regime"] != "Unknown")
    ][["yc_regime", "inf_regime"]].copy()

    # Build pivot table; reindex to enforce canonical ordering
    counts = (
        valid.groupby(["inf_regime", "yc_regime"])
        .size()
        .reset_index(name="months")
    )
    pivot = (
        counts.pivot(index="inf_regime", columns="yc_regime", values="months")
        .fillna(0)
        .reindex(index=INF_REGIMES, columns=YC_REGIMES, fill_value=0)
    )
    z = pivot.values.astype(int)

    # Cell text: count + years
    cell_text = []
    for row in z:
        row_text = []
        for v in row:
            row_text.append(f"{int(v)}<br>{v/12:.1f}y" if v > 0 else "—")
        cell_text.append(row_text)

    # Highlight current cell
    annotations = []
    if current_yc in YC_REGIMES and current_inf in INF_REGIMES:
        annotations.append(dict(
            x=current_yc,
            y=current_inf,
            text="▶ NOW",
            showarrow=False,
            font=dict(color="white", size=9, family=_FONT_FAMILY),
            xref="x", yref="y",
            yshift=14,
        ))

    fig = go.Figure(go.Heatmap(
        z=z,
        x=YC_REGIMES,
        y=INF_REGIMES,
        text=cell_text,
        texttemplate="%{text}",
        textfont=dict(size=11, family=_FONT_FAMILY),
        colorscale="Blues",
        colorbar=dict(
            title=dict(text="Months", side="right"),
            thickness=14, len=0.85,
        ),
        hovertemplate=(
            "YC: <b>%{x}</b><br>"
            "Inflation: <b>%{y}</b><br>"
            "Months: <b>%{z}</b><extra></extra>"
        ),
        xgap=3,
        ygap=3,
    ))

    fig.update_layout(
        template=_TEMPLATE,
        title=dict(text="Historical Regime Co-occurrence (months / years)", font=dict(size=15)),
        xaxis=dict(title="Yield Curve Regime", side="bottom", tickfont=dict(size=12)),
        yaxis=dict(title="Inflation Regime", autorange="reversed", tickfont=dict(size=11)),
        font=dict(family=_FONT_FAMILY),
        margin=dict(l=170, r=50, t=60, b=60),
        height=440,
        annotations=annotations,
    )
    return fig

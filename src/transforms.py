"""
Data transformation module.

All series are resampled to month-end frequency before any derived
metrics are computed.  Short gaps (≤ 3 months) in daily Treasury
series are forward-filled to avoid artificial NaN holes.

Derived columns added
---------------------
cpi_yoy        : YoY percentage change in CPIAUCSL
spread_10y2y   : DGS10 − DGS2 (percentage points)
spread_3m_chg  : 3-month change in spread (ppts)
cpi_yoy_3m_chg : 3-month change in YoY CPI (ppts)
"""

import pandas as pd


def resample_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample all series to month-end (ME) frequency.

    Daily series (DGS2, DGS10): last available value of the month.
    Monthly series (CPIAUCSL, FEDFUNDS): single value → last value == that value.
    Short gaps are forward-filled (limit=3 months) to handle holiday/weekend
    boundary effects at month end.
    """
    monthly = df.resample("ME").last()
    monthly = monthly.ffill(limit=3)
    return monthly


def compute_yoy_cpi(df: pd.DataFrame) -> pd.DataFrame:
    """Add cpi_yoy: 12-month percentage change in CPIAUCSL."""
    df = df.copy()
    df["cpi_yoy"] = df["CPIAUCSL"].pct_change(12) * 100
    return df


def compute_spread(df: pd.DataFrame) -> pd.DataFrame:
    """Add spread_10y2y: 10-year minus 2-year Treasury yield (ppts)."""
    df = df.copy()
    df["spread_10y2y"] = df["DGS10"] - df["DGS2"]
    return df


def compute_3m_changes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 3-month first-differences for spread and YoY CPI.

    These are used to determine directional regime labels (Rising / Falling /
    Stable) and the Re-steepening yield-curve condition.
    """
    df = df.copy()
    df["spread_3m_chg"]  = df["spread_10y2y"].diff(3)
    df["cpi_yoy_3m_chg"] = df["cpi_yoy"].diff(3)
    return df


def apply_transforms(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the full transformation pipeline in order."""
    df = resample_monthly(df)
    df = compute_yoy_cpi(df)
    df = compute_spread(df)
    df = compute_3m_changes(df)
    return df

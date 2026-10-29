"""
common.py
Shared helpers for the automatic stabilizers model: quarterly index construction,
simple transforms, fiscal-year conversion, polynomial distributed lags, and CSV loaders.
"""

import numpy as np
import pandas as pd


# ------------------------------------------------------------
# Quarterly index and simple transforms
# ------------------------------------------------------------

def make_qindex(first_qtr, last_qtr):
    """Quarterly PeriodIndex from first_qtr to last_qtr (inclusive), e.g. '1945Q1'-'2025Q3'."""
    return pd.period_range(start=first_qtr, end=last_qtr, freq="Q")


def new_q(qdx, fill=np.nan):
    return pd.Series(fill, index=qdx, dtype=float)


def d(s):
    return s.diff()


def dlog(s):
    return np.log(s).diff()


def annual_sum(s_q, complete_only=True):
    """
    Sum a quarterly series to calendar years.
    With complete_only=True (default), years with fewer than four observed
    quarters are dropped so that a partial final year is not treated as a
    full-year total.
    """
    s = s_q.dropna()
    grp = s.groupby(s.index.year)
    out = grp.sum()
    if complete_only:
        out = out[grp.count() == 4]
    return out


def annual_to_quarterly(s_a, qdx):
    """Repeat each annual value for all four quarters of that year."""
    s_q = new_q(qdx)
    for yr, val in s_a.items():
        try:
            yr_int = yr.year if isinstance(yr, pd.Period) else int(yr)
        except (ValueError, TypeError):
            continue
        for qn in range(1, 5):
            p = pd.Period(f"{yr_int}Q{qn}", "Q")
            if p in s_q.index:
                s_q[p] = val
    return s_q


def extend_annual_series(s_a, target_year, method="forward"):
    """Extend an annual series to target_year, forward-filling the last value by default."""
    def _yr(x):
        return x.year if isinstance(x, pd.Period) else int(x)

    s = pd.Series(s_a.values, index=pd.Index([_yr(i) for i in s_a.index], dtype=int), dtype=float)
    s = s.sort_index()[~s.index.duplicated(keep="last")]
    valid = s.dropna()
    if valid.empty or int(valid.index[-1]) >= target_year:
        return s

    last_year = int(valid.index[-1])
    last_val = float(valid.iloc[-1])
    if method == "forward":
        for yr in range(last_year + 1, target_year + 1):
            s.loc[yr] = last_val
    elif method == "growth":
        g = float(valid.iloc[-1] / valid.iloc[-2]) if len(valid) >= 2 else 1.0
        for yr in range(last_year + 1, target_year + 1):
            last_val *= g
            s.loc[yr] = last_val
    return s.sort_index()


# ------------------------------------------------------------
# Fiscal-year and calendar-year conversion
# ------------------------------------------------------------

def fiscal_year(p):
    """
    Fiscal year for a quarterly Period.
      Through FY1976: Jul-Jun.
      Transition Quarter (Jul-Sep 1976): excluded (returns None).
      FY1977 onward: Oct-Sep.
    """
    ts = p.to_timestamp()
    month, year = ts.month, ts.year
    if year == 1976 and month in (7, 8, 9):
        return None
    if year < 1976 or (year == 1976 and month <= 6):
        return year + 1 if month >= 7 else year
    return year + 1 if month >= 10 else year


def _fy_frame(df_q):
    df = df_q.copy()
    fys = [fiscal_year(p) for p in df.index]
    mask = [fy is not None for fy in fys]
    df = df.loc[mask]
    df.index = pd.Index([fy for fy in fys if fy is not None], name="fiscal_year")
    return df


def to_fiscal_year(df_q, min_quarters=4):
    """
    Fiscal-year averages of quarterly data (levels are seasonally adjusted
    annual rates, so the annual level is the average of the quarters).
    Fiscal years with fewer than min_quarters observed quarters are dropped.
    """
    df = _fy_frame(df_q)
    counts = df.groupby(df.index).size()
    avg = df.groupby(df.index).mean()
    return avg.loc[counts >= min_quarters]


def to_calendar_year(df_q, min_quarters=4):
    """Calendar-year averages of quarterly data; incomplete years are dropped."""
    df = df_q.copy()
    df.index = pd.Index(df.index.year, name="year")
    counts = df.groupby(df.index).size()
    avg = df.groupby(df.index).mean()
    return avg.loc[counts >= min_quarters]


# ------------------------------------------------------------
# Polynomial distributed lags
# ------------------------------------------------------------

def make_pdl_regressors(x, max_lag, degree, restrict="both"):
    """
    Build polynomial distributed lag regressors.
    EViews PDL restriction codes: 1=near-end, 2=far-end, 3=both.
    Python restrict parameter: 'near', 'far', 'both', or None.
    """
    lags = np.arange(0, max_lag + 1)
    Z = np.column_stack([lags ** k for k in range(degree + 1)])
    if restrict == "both":
        Z = Z[:, 1:-1] if Z.shape[1] > 2 else Z[:, 1:]
    elif restrict == "near":
        Z = Z[:, 1:]
    elif restrict == "far":
        Z = Z[:, :-1]
    X_lags = pd.concat([x.shift(l).rename(f"lag{l}") for l in lags], axis=1)
    pdl_cols = X_lags.values @ Z
    cols = [f"pdl_{i}" for i in range(pdl_cols.shape[1])]
    return pd.DataFrame(pdl_cols, index=x.index, columns=cols)


# ------------------------------------------------------------
# CSV loaders
# ------------------------------------------------------------

def load_quarterly_csv(path, qdx=None):
    """
    Load a CSV whose first column holds quarters ('1990Q1') into a
    PeriodIndex DataFrame with lower-case column names. If qdx is given,
    the frame is reindexed to it.
    """
    df = pd.read_csv(path, index_col=0)
    df.index = pd.PeriodIndex(df.index.astype(str).str.upper(), freq="Q")
    df.index.name = "quarter"
    df.columns = df.columns.str.lower()
    if qdx is not None:
        df = df.reindex(qdx)
    return df


def load_annual_csv(path):
    """Load a CSV whose first column holds integer years into an int-indexed DataFrame."""
    df = pd.read_csv(path, index_col=0)
    df.index = df.index.astype(int)
    df.index.name = "year"
    df.columns = df.columns.str.lower()
    return df

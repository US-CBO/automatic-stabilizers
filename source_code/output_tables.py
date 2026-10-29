"""
output_tables.py
Assembles baseline, cyclically adjusted, and cyclical-component series;
writes quarterly and annual CSV files, summary tables, and charts.
"""

import pandas as pd

from common import to_calendar_year, to_fiscal_year

# Variables written to the output files, each as _base, _ca, and _cyc (= base - ca)
OUTPUT_VARS = [
    "rcgf", "tpgf", "tcgfo", "tcgffrb", "twgf", "tpigf",
    "gexpf", "ruig8", "med", "food", "surgf",
    "sste", "sstse", "uit", "taxbase", "gdp", "gdpk", "gdpgap", "ur",
    "gdpfe", "ruc", "rucfe", "intpdgf",
]

# NBER recession dates (peak quarter to trough quarter)
NBER_RECESSIONS = [
    ("1948Q4", "1949Q4"), ("1953Q2", "1954Q2"), ("1957Q3", "1958Q2"), ("1960Q2", "1961Q1"),
    ("1969Q4", "1970Q4"), ("1973Q4", "1975Q1"), ("1980Q1", "1980Q3"), ("1981Q3", "1982Q4"),
    ("1990Q3", "1991Q1"), ("2001Q1", "2001Q4"), ("2007Q4", "2009Q2"), ("2020Q1", "2020Q2"),
]


def assemble_output(qb, qca):
    """Quarterly DataFrame of baseline (_base), cyclically adjusted (_ca), and cyclical (_cyc) series."""
    frames = {}
    for v in OUTPUT_VARS:
        if v in qb.columns:
            frames[f"{v}_base"] = qb[v]
        if v in qca.columns:
            frames[f"{v}_ca"] = qca[v]
        if v in qb.columns and v in qca.columns:
            frames[f"{v}_cyc"] = qb[v] - qca[v]     # convention: cyc = base - ca
    df_q = pd.DataFrame(frames)
    df_q.index.name = "quarter"
    return df_q


def summary_table(df):
    """
    Condensed table of revenues, outlays, and the surplus/deficit -- actual,
    excluding automatic stabilizers, and the stabilizer effect -- in levels
    (billions of dollars) and as a percent of potential GDP.
    """
    out = pd.DataFrame(index=df.index)
    cols = {
        "revenues": "rcgf_base", "outlays": "gexpf_base", "surplus": "surgf_base",
        "revenues_ex_stabilizers": "rcgf_ca", "outlays_ex_stabilizers": "gexpf_ca", "surplus_ex_stabilizers": "surgf_ca",
        "stabilizers_revenues": "rcgf_cyc", "stabilizers_outlays": "gexpf_cyc", "stabilizers_surplus": "surgf_cyc",
        "net_interest": "intpdgf_base",
    }
    scale = 100.0 / df["gdpfe_base"]
    for name, src in cols.items():
        out[name] = df[src]
    out["gdp_gap"] = df["gdp_base"] - df["gdpfe_base"]
    out["unemployment_gap"] = df["ruc_base"] - df["rucfe_base"]
    for name, src in cols.items():
        out[f"{name}_pct_potential_gdp"] = df[src] * scale
    out["gdp_gap_pct_potential_gdp"] = out["gdp_gap"] * scale
    return out


def write_csv_outputs(df_q, outputs, start_q, start_yr, decimals=4):
    """Write quarterly, fiscal-year, and calendar-year CSV files plus summary tables."""
    dq  = df_q.loc[df_q.index >= pd.Period(start_q, "Q")]
    dfy = to_fiscal_year(df_q)
    dfy = dfy.loc[dfy.index >= start_yr]
    dcy = to_calendar_year(df_q)
    dcy = dcy.loc[dcy.index >= start_yr]

    files = {
        "autostabs_quarterly.csv"            : dq,
        "autostabs_fiscal_year.csv"          : dfy,
        "autostabs_calendar_year.csv"        : dcy,
        "autostabs_summary_quarterly.csv"    : summary_table(dq),
        "autostabs_summary_fiscal_year.csv"  : summary_table(dfy),
    }
    for name, frame in files.items():
        frame.round(decimals).to_csv(outputs / name)
        print(f"  {name}")
    return dq, dfy


def _add_recession_bars(ax, xmin_ts, xmax_ts):
    for start, end in NBER_RECESSIONS:
        p_start = pd.Period(start, freq="Q").to_timestamp()
        p_end   = pd.Period(end,   freq="Q").to_timestamp(how="end")
        if p_end < xmin_ts or p_start > xmax_ts:
            continue
        ax.axvspan(max(p_start, xmin_ts), min(p_end, xmax_ts), color="gray", alpha=0.25, linewidth=0)


def _make_chart(x, series_specs, title, ylabel, outpath, xmin_ts, xmax_ts):
    """series_specs = list of (y, color, linestyle, label)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 5.5))
    for y, color, style, label in series_specs:
        ax.plot(x, y, color=color, linestyle=style, linewidth=1.5, label=label)
    ax.axhline(0, color="black", linewidth=0.5)
    _add_recession_bars(ax, xmin_ts, xmax_ts)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)
    print(f"  {outpath.name}")


def write_charts(df_q, outputs, start_q, start_yr):
    """
    Four PNG charts, all as a percent of potential GDP (shaded bars are NBER recessions):
      1. Quarterly: effect of automatic stabilizers on the deficit
      2. Quarterly: actual vs. cyclically adjusted deficit
      3. Fiscal year: effect of automatic stabilizers on the deficit
      4. Fiscal year: actual vs. cyclically adjusted deficit
    """
    dq = df_q.loc[df_q.index >= pd.Period(start_q, "Q")].copy()
    xq = dq.index.to_timestamp()
    scale_q = 100.0 / dq["gdpfe_base"]

    da = to_fiscal_year(df_q)
    da = da.loc[da.index >= start_yr]
    xa = pd.to_datetime(da.index.astype(int).astype(str) + "-04-01")   # midpoint of the Oct-Sep year
    a_xmin = pd.Timestamp(year=int(da.index.min()) - 1, month=10, day=1)
    a_xmax = pd.Timestamp(year=int(da.index.max()), month=9, day=30)
    scale_a = 100.0 / da["gdpfe_base"]

    blue, red = "#1F4E79", "#C00000"
    ylab = "Percent of potential GDP"

    _make_chart(xq, [(-dq["surgf_cyc"] * scale_q, blue, "-", "Effect of automatic stabilizers on the deficit")],
                "Effect of Automatic Stabilizers on the Federal Deficit (Quarterly)", ylab,
                outputs / "figure1_stabilizer_effect_quarterly.png", xq.min(), xq.max())

    _make_chart(xq, [(-dq["surgf_base"] * scale_q, red, "-", "Actual deficit"),
                     (-dq["surgf_ca"] * scale_q, blue, "--", "Deficit without automatic stabilizers")],
                "Actual and Cyclically Adjusted Federal Deficit (Quarterly)", ylab,
                outputs / "figure2_actual_vs_adjusted_quarterly.png", xq.min(), xq.max())

    _make_chart(xa, [(-da["surgf_cyc"] * scale_a, blue, "-", "Effect of automatic stabilizers on the deficit")],
                "Effect of Automatic Stabilizers on the Federal Deficit (Fiscal Year)", ylab,
                outputs / "figure3_stabilizer_effect_fiscal_year.png", a_xmin, a_xmax)

    _make_chart(xa, [(-da["surgf_base"] * scale_a, red, "-", "Actual deficit"),
                     (-da["surgf_ca"] * scale_a, blue, "--", "Deficit without automatic stabilizers")],
                "Actual and Cyclically Adjusted Federal Deficit (Fiscal Year)", ylab,
                outputs / "figure4_actual_vs_adjusted_fiscal_year.png", a_xmin, a_xmax)

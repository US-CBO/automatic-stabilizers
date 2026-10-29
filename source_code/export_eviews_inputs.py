"""
export_eviews_inputs.py
Purpose : One-time export of the series held in CBO's internal EViews databases
          to the CSV files read by the model:
            inputs/cbo_baseline_quarterly.csv   (CBO economic baseline)
            inputs/nipa_quarterly.csv           (national income and product accounts)
            inputs/heb_history_quarterly.csv    (historical series from the prior model database)
          This step is internal to CBO: it requires EViews, py2eviews, and access to
          CBO's network drives, and does not need to be re-run to reproduce the results.
Usage   : Set the database paths and LAST_QTR below, open EViews, then
          python export_eviews_inputs.py
"""

from pathlib import Path

import pandas as pd

# --- Settings ------------------------------------------------
LAST_QTR   = "2025Q3"
FIRST_QTR  = "1945Q1"
BBOX_EDB   = r"P:\CBO_Forecasts\2026_02\b251203f_rev"
NIPA_DAT   = r"W:\DLX\DATA\USNA.dat"
OLD_HEB    = r"P:\Models\HEB\2024_2\EDB\hx240906a"
INPUTS     = Path(__file__).resolve().parents[1] / "inputs"

BASELINE_VARS = [
    "divxper", "yentnfadj", "yentafadj", "yintper", "yrentadj", "gdp", "wsd",
    "zbadj", "zbaivafrb", "ruc", "rucfe", "qgdp", "qgdpfe",
    "sste", "sstse", "uit", "food", "med", "ruig8",
    "rcgf", "tpgf", "twgf", "tpigf", "gexpf", "intpdgf", "intrgf",
]
NIPA_VARS = [
    "gdp", "gfrie", "gfrid", "gfrcp", "gfrivf",
    "gftfbux", "gftfburx", "gftfbufx", "yptub", "yptue", "yptup", "yptuc",
]
HISTORY_VARS = ["txgfwfp", "med", "rcwss", "rcwsu"]


def load_edb(path, varlist, last_year):
    """Fetch a list of series from an EViews database into a quarterly DataFrame."""
    import py2eviews as evp
    evp.Cleanup()
    evp.Run(f"wfcreate(wf=_tmp,page=_pg) q 1945 {last_year}")
    evp.Run(f'dbopen "{path}" as _db')
    evp.Run(f'fetch {" ".join(varlist)}')
    evp.Run("close _db")
    raw = evp.GetWFAsPython(wfname="_tmp", pagename="_pg", namefilter="*")
    evp.Run("wfclose _tmp")
    df = pd.DataFrame(raw)
    if not isinstance(df.index, pd.PeriodIndex):
        try:
            df.index = pd.PeriodIndex(df.index, freq="Q")
        except Exception:
            df.index = pd.DatetimeIndex(df.index).to_period("Q")
    df.columns = df.columns.str.lower()
    return df[[v.lower() for v in varlist if v.lower() in df.columns]]


def main():
    qdx = pd.period_range(FIRST_QTR, LAST_QTR, freq="Q")
    last_year = qdx[-1].year
    jobs = [
        (BBOX_EDB, BASELINE_VARS, "cbo_baseline_quarterly.csv"),
        (NIPA_DAT, NIPA_VARS,     "nipa_quarterly.csv"),
        (OLD_HEB,  HISTORY_VARS,  "heb_history_quarterly.csv"),
    ]
    for path, varlist, fname in jobs:
        df = load_edb(path, varlist, last_year).reindex(qdx)
        df.index.name = "quarter"
        df.round(6).to_csv(INPUTS / fname)
        print(f"Wrote {INPUTS / fname}  ({df.shape[1]} series, {df.dropna(how='all').shape[0]} quarters)")


if __name__ == "__main__":
    main()

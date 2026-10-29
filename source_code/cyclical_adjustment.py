"""
cyclical_adjustment.py
Builds the quarterly database, estimates the income-share and cyclical-spending
equations, and solves the model twice: once at actual values (baseline) and once
with the GDP and unemployment gaps set to zero (cyclically adjusted).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from common import d, load_quarterly_csv, make_pdl_regressors

# Series taken from CBO's economic baseline (inputs/cbo_baseline_quarterly.csv)
BASELINE_VARS = [
    "divxper", "yentnfadj", "yentafadj", "yintper", "yrentadj", "gdp", "wsd",
    "zbadj", "zbaivafrb", "ruc", "rucfe", "qgdp", "qgdpfe",
    "sste", "sstse", "uit", "food", "med", "ruig8",
    "rcgf", "tpgf", "twgf", "tpigf",
    "gexpf", "intpdgf", "intrgf",
]

TREND_COLS = ["t53", "t57", "t60", "t69", "t73", "t80", "t81", "t90", "t01", "t07"]
SHARE_VARS = ["zbadjxfrb", "zbadj", "divxper", "yentadj", "ws", "yintper", "yrentadj", "taxbase"]


def build_database(inputs, qdx, exog_q, last_qtr):
    """Assemble the quarterly database used for estimation and solution."""
    last_q = pd.Period(last_qtr, "Q")

    # ----------------------------------------------------------
    # 1. CBO economic baseline
    # ----------------------------------------------------------
    bb = load_quarterly_csv(inputs / "cbo_baseline_quarterly.csv", qdx)
    missing = [v for v in BASELINE_VARS if v not in bb.columns]
    if missing:
        raise KeyError(f"cbo_baseline_quarterly.csv is missing columns: {missing}")

    q = pd.DataFrame(index=qdx)
    for v in BASELINE_VARS:
        q[v] = bb[v]

    # Forward-fill sste, sstse, uit in the last quarter if not yet available
    for _v in ["sste", "sstse", "uit"]:
        if pd.isna(q.loc[last_q, _v]):
            q.loc[last_q, _v] = q[_v].ffill().loc[last_q]

    q["gexpf"] = q["gexpf"].ffill().bfill()

    # Extend intrgf back to 1959Q3
    p59q4 = pd.Period("1959Q4", "Q"); p59q3 = pd.Period("1959Q3", "Q")
    q.loc[p59q4, "intrgf"] = q.loc[pd.Period("1960Q1", "Q"), "intrgf"]
    q.loc[p59q3, "intrgf"] = q.loc[p59q4, "intrgf"]

    # ----------------------------------------------------------
    # 2. Corporate taxes: NIPA before 1994, Treasury/tax-analysis data from 1994Q1
    # ----------------------------------------------------------
    nipa = load_quarterly_csv(inputs / "nipa_quarterly.csv", qdx)
    tad  = load_quarterly_csv(inputs / "tad_corporate_taxes.csv", qdx)
    q["tcgfo"]   = nipa["gfrcp"]
    q["tcgffrb"] = nipa["gfrivf"]
    from94 = q.index >= pd.Period("1994Q1", "Q")
    q.loc[from94, "tcgfo"]   = tad.loc[from94, "tcgf"]
    q.loc[from94, "tcgffrb"] = tad.loc[from94, "tcgffrb"]

    # ----------------------------------------------------------
    # 3. Historical series from the prior HEB database
    # ----------------------------------------------------------
    hist = load_quarterly_csv(inputs / "heb_history_quarterly.csv", qdx)
    q["txgfwfp"] = hist["txgfwfp"].fillna(0)
    q.loc[pd.Period("1986Q1", "Q"):, "txgfwfp"] = 0
    q.loc[pd.Period("1959Q1", "Q"):pd.Period("1960Q4", "Q"), "food"] = 0
    q.loc[pd.Period("1959Q1", "Q"):pd.Period("1965Q4", "Q"), "med"]  = 0
    q.loc[q["med"].isna(), "med"] = hist.loc[q["med"].isna(), "med"]

    # ----------------------------------------------------------
    # 4. Covered-wage ratios (backfilled from the prior HEB database)
    # ----------------------------------------------------------
    ratios = load_quarterly_csv(inputs / "covered_wage_ratios.csv", qdx)
    for _v in ["rcwss", "rcwsu"]:
        q[_v] = ratios[_v]
        q.loc[q[_v].isna(), _v] = hist.loc[q[_v].isna(), _v]

    # ----------------------------------------------------------
    # 5. Dummy and trend variables
    # ----------------------------------------------------------
    q["dum70"] = 0
    q.loc[pd.Period("1970Q1", "Q"):, "dum70"] = 1
    q["trend"] = np.arange(len(qdx))
    q.loc[q.index < pd.Period("1945Q2", "Q"), "trend"] = 0
    q["d84"] = 0
    q.loc[:pd.Period("1983Q4", "Q"), "d84"] = 1

    # ----------------------------------------------------------
    # 6. Attach elasticities and derived series
    # ----------------------------------------------------------
    q = q.drop(columns=[c for c in exog_q.columns if c in q.columns], errors="ignore")
    q = q.join(exog_q.reindex(q.index))

    q["ur"]        = q["ruc"] - q["rucfe"]
    q["ws"]        = q["wsd"]
    q["yentadj"]   = q["yentafadj"] + q["yentnfadj"]
    q["gdpgap"]    = 1 - (q["qgdp"] / q["qgdpfe"])
    q["gdpk"]      = q["gdp"] / (1 - q["gdpgap"])       # nominal potential GDP
    q["gdpfe"]     = q["gdpk"]
    q["dg"]        = q["gdpgap"].diff()
    q["zbadjxfrb"] = q["zbadj"] - q["zbaivafrb"]
    q["taxbase"]   = q["divxper"] + q["yentadj"] + q["ws"] + q["yintper"]
    q["intnetgf"]  = q["intpdgf"] - q["intrgf"]

    q["food1"] = 0.0
    sl1 = slice(pd.Period("1961Q2", "Q"), pd.Period("1996Q4", "Q"))
    q.loc[sl1, "food1"] = q.loc[sl1, "food"]
    q["food2"] = 0.0
    q.loc[pd.Period("1996Q4", "Q"):, "food2"] = q.loc[pd.Period("1996Q4", "Q"):, "food"]
    q.loc[pd.Period("1996Q4", "Q"), "food2"] = 0

    # Pandemic adjustment to UI benefits (2020Q2-2021Q4): remove the temporary federal programs
    p1, p2 = pd.Period("2020Q2", "Q"), pd.Period("2021Q4", "Q")
    q["ruig8_adj"] = q["ruig8"].copy()
    q.loc[p1:p2, "ruig8_adj"] = (
        (nipa.loc[p1:p2, "gftfbux"] - nipa.loc[p1:p2, "gftfburx"] - nipa.loc[p1:p2, "gftfbufx"]) / 1000
        - (nipa.loc[p1:p2, "yptub"] + nipa.loc[p1:p2, "yptue"] + nipa.loc[p1:p2, "yptup"] + nipa.loc[p1:p2, "yptuc"])
    )

    # ----------------------------------------------------------
    # 7. Residuals (add factors for the model equations)
    # ----------------------------------------------------------
    q["ssteresid"]  = np.log(q["sste"])  - q["ess"]  * np.log(q["rcwss"] * q["ws"])
    q["sstseresid"] = np.log(q["sstse"]) - q["esst"] * np.log(q["yentadj"])
    q["uitresid"]   = q["uit"]           - q["uitrate"] * (q["rcwsu"] * q["wsd"])
    q["twgfresid"]  = q["twgf"]          - q["sste"] - q["sstse"] - q["uit"]
    q["tpigfresid"] = np.log(q["tpigf"] - q["txgfwfp"]) - q["etxgf"] * np.log(q["gdpk"] * (1 - q["gdpgap"]))
    q["tcgforesid"] = np.log(q["tcgfo"]) - q["etcgf"] * np.log(q["zbadjxfrb"])
    q["tpgfresid"]  = np.log(q["tpgf"])  - q["ept"]  * np.log(q["ws"] + q["yentadj"] + q["divxper"] + q["yintper"])
    q["gexpfresid"] = q["gexpf"]         - (q["med"] + q["food"] + q["ruig8"])
    q["rcgfresid"]  = q["rcgf"]          - (q["tpgf"] + q["tcgfo"] + q["tcgffrb"] + q["twgf"] + q["tpigf"])
    for _v in ["gexpfresid", "rcgfresid"]:
        q[_v] = q[_v].ffill().bfill()

    return q


def estimate_equations(q, last_qtr, verbose=True):
    """Estimate the income-share equations and the cyclical spending equations."""
    last_q = pd.Period(last_qtr, "Q")

    def _print(model):
        if verbose:
            print(model.summary())

    # Income shares of potential GDP as functions of the GDP gap (0-4 lags) and trends
    share_models = {}
    est_mask_q = (q.index >= pd.Period("1949Q1", "Q")) & (q.index <= last_q)
    for v in SHARE_VARS:
        Xsh = pd.DataFrame({"const": 1.0}, index=q.index)
        for lag_n in range(5):
            Xsh[f"gdpgap_l{lag_n}"] = q["gdpgap"].shift(lag_n).values
        Xsh = Xsh.join(q[TREND_COLS])
        y_sh = pd.Series((q[v] / q["gdpk"]).values, index=q.index)
        share_models[v] = sm.OLS(y_sh[est_mask_q], Xsh[est_mask_q], missing="drop").fit()

    # UI benefits: change in share of potential GDP on changes in the unemployment gap (0-3 lags)
    ruig8_mask = (q.index >= pd.Period("1959Q1", "Q")) & (q.index <= last_q)
    y_ruig8 = d(q["ruig8_adj"] / q["gdpk"])
    X_ruig8 = pd.DataFrame({
        "const"   : 1, "d84": q["d84"],
        "d84_dur" : q["d84"] * d(q["ur"]),
        "d84_dur1": q["d84"] * d(q["ur"]).shift(1),
        "d84_dur2": q["d84"] * d(q["ur"]).shift(2),
        "d84_dur3": q["d84"] * d(q["ur"]).shift(3),
        "dur" : d(q["ur"]),          "dur1": d(q["ur"]).shift(1),
        "dur2": d(q["ur"]).shift(2), "dur3": d(q["ur"]).shift(3),
    })
    ruig8_model = sm.OLS(y_ruig8[ruig8_mask], X_ruig8[ruig8_mask], missing="drop").fit()
    _print(ruig8_model)

    # Medicaid: pdl(d(ur), 2, 1, far-end restriction)
    med_mask = (q.index >= pd.Period("1966Q1", "Q")) & (q.index <= last_q)
    y_med    = d(q["med"] / q["gdpk"])
    X_med    = pd.concat([pd.Series(1, index=q.index, name="const"),
                          make_pdl_regressors(d(q["ur"]), max_lag=2, degree=1, restrict="far")], axis=1)
    med_model = sm.OLS(y_med[med_mask], X_med[med_mask], missing="drop").fit()
    _print(med_model)

    # SNAP through 1996: pdl(d(ur), 3, 2, far-end restriction)
    food1_mask = (q.index >= pd.Period("1961Q3", "Q")) & (q.index <= pd.Period("1996Q4", "Q"))
    y_food1    = d(q["food1"] / q["gdpk"])
    X_food1    = pd.concat([pd.Series(1, index=q.index, name="const"),
                            make_pdl_regressors(d(q["ur"]), max_lag=3, degree=2, restrict="far")], axis=1)
    food1_model = sm.OLS(y_food1[food1_mask], X_food1[food1_mask], missing="drop").fit()
    _print(food1_model)

    # SNAP from 1997: pdl(d(ur), 12, 2, far-end restriction)
    food2_mask = (q.index >= pd.Period("1997Q1", "Q")) & (q.index <= last_q)
    y_food2    = d(q["food2"] / q["gdpk"])
    X_food2    = pd.concat([pd.Series(1, index=q.index, name="const"),
                            make_pdl_regressors(d(q["ur"]), max_lag=12, degree=2, restrict="far")], axis=1)
    food2_model = sm.OLS(y_food2[food2_mask], X_food2[food2_mask], missing="drop").fit()
    _print(food2_model)

    return {
        "share": share_models, "ruig8": ruig8_model, "med": med_model,
        "food1": food1_model, "food2": food2_model,
    }


def solve_baseline(q_in):
    """Solve the model at actual values (the residuals reproduce actual data)."""
    qb = q_in.copy()
    qb["sste"]  = np.exp(qb["ess"]  * np.log(qb["rcwss"] * qb["ws"]) + qb["ssteresid"])
    qb["sstse"] = np.exp(qb["esst"] * np.log(qb["yentadj"])           + qb["sstseresid"])
    # uit is computed before twgf (twgf depends on it) and uses wsd, not the adjusted ws
    qb["uit"]   = qb["uitrate"] * (qb["rcwsu"] * qb["wsd"]) + qb["uitresid"]
    qb["twgf"]  = qb["sste"] + qb["sstse"] + qb["uit"] + qb["twgfresid"]
    qb["tpigf"] = np.exp(qb["etxgf"] * np.log(qb["gdpk"] * (1 - qb["gdpgap"])) + qb["tpigfresid"]) + qb["txgfwfp"]
    qb["tcgfo"] = np.exp(qb["etcgf"] * np.log(qb["zbadjxfrb"]) + qb["tcgforesid"])
    qb["tpgf"]  = np.exp(qb["ept"]   * np.log(qb["ws"] + qb["yentadj"] + qb["divxper"] + qb["yintper"]) + qb["tpgfresid"])
    qb["rcgf"]  = qb["tpgf"] + qb["tcgfo"] + qb["tcgffrb"] + qb["twgf"] + qb["tpigf"] + qb["rcgfresid"]
    qb["food"]  = qb["food1"] + qb["food2"]
    qb["gexpf"] = qb["med"] + qb["food"] + qb["ruig8"] + qb["gexpfresid"]
    qb["surgf"] = qb["rcgf"] - qb["gexpf"]
    return qb


def solve_cyclically_adjusted(q, models):
    """Solve the model with the GDP and unemployment gaps set to zero."""
    share_models = models["share"]

    # Add factors for the income-share equations (held fixed in the adjusted solve)
    X_full = pd.DataFrame({"const": 1.0}, index=q.index)
    for lag_n in range(5):
        X_full[f"gdpgap_l{lag_n}"] = q["gdpgap"].shift(lag_n)
    X_full = X_full.join(q[TREND_COLS])
    share_addfactors = {v: (q[v] / q["gdpk"]) - share_models[v].predict(X_full) for v in SHARE_VARS}

    def predict_shares_zero_gap(q_in):
        Xz = pd.DataFrame({"const": 1.0}, index=q_in.index)
        for lag_n in range(5):
            Xz[f"gdpgap_l{lag_n}"] = 0.0
        Xz = Xz.join(q_in[TREND_COLS])
        return {v: (share_models[v].predict(Xz) + share_addfactors[v]) * q_in["gdpk"] for v in SHARE_VARS}

    def decycle_spending(q_in):
        """
        Remove the cyclical component of UI benefits, Medicaid, and SNAP.
        The coefficients estimated on changes in the unemployment gap are applied
        to the level of the gap, as in the EViews version of the model.
        """
        qd = q_in.copy()
        ur = qd["ur"]
        c  = models["ruig8"].params
        qd["ruig8"] = qd["gdpk"] * (
            qd["ruig8"] / qd["gdpk"]
            - (c["d84_dur"]  * qd["d84"] * ur          + c["d84_dur1"] * qd["d84"] * ur.shift(1)
             + c["d84_dur2"] * qd["d84"] * ur.shift(2) + c["d84_dur3"] * qd["d84"] * ur.shift(3)
             + c["dur"]  * ur          + c["dur1"] * ur.shift(1)
             + c["dur2"] * ur.shift(2) + c["dur3"] * ur.shift(3))
        )

        cm = models["med"].params
        ur_contrib_med = make_pdl_regressors(ur, max_lag=2, degree=1, restrict="far").values @ cm[1:].values
        qd["med"] = qd["gdpk"] * (qd["med"] / qd["gdpk"] - ur_contrib_med)

        cf1 = models["food1"].params
        ur_contrib_f1 = make_pdl_regressors(ur, max_lag=3, degree=2, restrict="far").values @ cf1[1:].values
        sl = slice(pd.Period("1961Q3", "Q"), pd.Period("1996Q4", "Q"))
        qd.loc[sl, "food1"] = (qd["gdpk"] * (qd["food1"] / qd["gdpk"] - ur_contrib_f1)).loc[sl]

        cf2 = models["food2"].params
        ur_contrib_f2 = make_pdl_regressors(ur, max_lag=12, degree=2, restrict="far").values @ cf2[1:].values
        sl2 = slice(pd.Period("1997Q1", "Q"), None)
        qd.loc[sl2, "food2"] = (qd["gdpk"] * (qd["food2"] / qd["gdpk"] - ur_contrib_f2)).loc[sl2]

        qd["food"] = qd["food1"] + qd["food2"]
        return qd

    qca = decycle_spending(q.copy())      # uses the actual unemployment gap
    qca["ur"]        = 0.0
    qca["gdpgap"]    = 0.0
    qca["uitrate"]   = qca["uitratek"]
    qca["zbadjxfrb"] = qca["zbadj"] - qca["zbaivafrb"]
    for v, s in predict_shares_zero_gap(qca).items():
        qca[v] = s
    return solve_baseline(qca)


def run_cyclical_adjustment(inputs, qdx, exog_q, last_qtr, verbose=True):
    """
    Returns (qb, qca): baseline and cyclically adjusted quarterly DataFrames,
    solved from 1963Q3 onward.
    """
    print("Running cyclical adjustment...")
    q = build_database(inputs, qdx, exog_q, last_qtr)
    models = estimate_equations(q, last_qtr, verbose=verbose)

    qb  = solve_baseline(q.copy())
    qca = solve_cyclically_adjusted(q.copy(), models)

    solve_mask = q.index >= pd.Period("1963Q3", "Q")
    qb.loc[~solve_mask, :]  = np.nan
    qca.loc[~solve_mask, :] = np.nan
    return qb, qca

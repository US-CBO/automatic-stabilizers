"""
elasticities.py
Estimates the tax elasticities and trend variables used to cyclically adjust the
budget (ESS, ESST, EPT, ETCGF, ETXGF, UITRATE, UITRATEK, and piecewise-linear
trends). Returns a quarterly DataFrame covering the full sample.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from common import (annual_sum, annual_to_quarterly, dlog, extend_annual_series,
                    load_annual_csv, load_quarterly_csv, new_q)


def estimate_elasticities(inputs, qdx, last_year, last_act_year, verbose=True):
    """
    Parameters
    ----------
    inputs        : Path to the inputs/ directory
    qdx           : quarterly PeriodIndex for the full sample
    last_year     : last calendar year covered by qdx (elasticities are carried through it)
    last_act_year : last complete calendar year of actual data (end of annual regression samples)
    """
    print("Estimating elasticities...")
    all_yrs = pd.RangeIndex(1945, last_year + 1)

    def _print(model):
        if verbose:
            print(model.summary())

    # ----------------------------------------------------------
    # 1. ESS and ESST  (FICA / SECA payroll tax elasticities)
    # ----------------------------------------------------------
    es = load_annual_csv(inputs / "payroll_tax_data.csv")
    es = es.reindex(all_yrs)

    pworkersbelowmax    = es["pworkersbelowmax"]
    allworkers          = es["allworkers"]
    nseca               = es["nseca"]
    nfica               = es["nfica"]
    secataxable_dollars = es["secataxable_dollars"]
    ficataxable_dollars = es["ficataxable_dollars"]
    taxmax              = es["taxmax"]

    xall  = 0.01 * pworkersbelowmax
    xnall = xall * allworkers

    # SECA
    xseca   = 0.01 * es["xseca"]
    xnbseca = xseca * nseca
    xnaseca = (1 - xseca) * nseca
    yseca   = (1_000_000 * secataxable_dollars - (taxmax * xnaseca * 1000)) / (1000 * xnbseca)
    eyseca  = (yseca * xseca) / ((yseca * xseca) + taxmax * (1 - xseca))
    esst_a  = (0.62 + 0.38 * eyseca * (1 + 0.62)) / (0.62 + 0.38 * (1 + 0.62))

    # FICA
    beta   = xnbseca / xnall
    alpha  = 1 - beta
    xfica  = (1 / alpha) * (xall - beta * xseca)
    yfica  = (1_000_000 * ficataxable_dollars - (taxmax * (1 - xfica) * 1000 * nfica)) / (xfica * 1000 * nfica)
    eyfica = (yfica * xfica) / ((yfica * xfica) + taxmax * (1 - xfica))
    ess_a  = (0.62 + 0.38 * eyfica * (1 + 0.62)) / (0.62 + 0.38 * (1 + 0.62))

    # Extend beyond the last year of payroll data using projected FICA/SECA elasticities
    proj = load_annual_csv(inputs / "payroll_elasticity_projections.csv")
    fica_proj, seca_proj = proj["fica"], proj["seca"]

    last_ess  = int(ess_a.dropna().index[-1])
    last_esst = int(esst_a.dropna().index[-1])
    ext_ess   = range(last_ess + 1, last_year + 1)
    ext_esst  = range(last_esst + 1, last_year + 1)
    ess_ext   = fica_proj.reindex(ext_ess) * ess_a[last_ess]  / fica_proj[last_ess]
    esst_ext  = seca_proj.reindex(ext_esst) * esst_a[last_esst] / seca_proj[last_esst]
    ess_a     = pd.concat([ess_a.loc[:last_ess],  ess_ext])
    esst_a    = pd.concat([esst_a.loc[:last_esst], esst_ext])

    # ----------------------------------------------------------
    # 2. EPT  (personal income tax elasticity)
    # ----------------------------------------------------------
    bb  = load_quarterly_csv(inputs / "cbo_baseline_quarterly.csv", qdx)
    agi = load_annual_csv(inputs / "agi_history.csv")["agi"]
    params = load_annual_csv(inputs / "annual_parameters.csv")

    ypaxrent = (annual_sum(bb["wsd"]) + annual_sum(bb["yentafadj"]) + annual_sum(bb["yentnfadj"])
                + annual_sum(bb["divxper"]) + annual_sum(bb["yintper"]))
    idx_a = ypaxrent.index
    agi_a = agi.reindex(idx_a)

    dum1 = pd.Series(0, index=idx_a); dum1.loc[1946:1986] = 1
    dum2 = pd.Series(0, index=idx_a); dum2.loc[1987:2000] = 1
    dum3 = pd.Series(0, index=idx_a); dum3.loc[2001:last_act_year] = 1

    dlagi  = dlog(agi_a)
    dlypax = dlog(ypaxrent)
    X = pd.DataFrame({
        "const"  : 1,
        "d1_ypax": dum1 * dlypax,
        "d2_ypax": dum2 * dlypax,
        "d3_ypax": dum3 * dlypax,
    })
    mask = (idx_a >= 1950) & (idx_a <= last_act_year)
    agi_model = sm.OLS(dlagi[mask], X[mask], missing="drop").fit()
    _print(agi_model)

    eby_a = pd.Series(0.0, index=all_yrs)
    eby_a.loc[1959:1986]      = agi_model.params["d1_ypax"]
    eby_a.loc[1987:2000]      = agi_model.params["d2_ypax"]
    eby_a.loc[2001:last_year] = agi_model.params["d3_ypax"]

    # ETB (elasticity of tax liability with respect to AGI) is an exogenous input
    etb_a = params["etb"].reindex(all_yrs)
    ept_a = etb_a * eby_a

    # ----------------------------------------------------------
    # 3. ETCGF  (corporate income tax elasticity)
    # ----------------------------------------------------------
    zb_a = annual_sum(bb["zbadj"]) - annual_sum(bb["zbaivafrb"])
    istsoi2_a = load_annual_csv(inputs / "soi_corporate_income.csv")["soi_taxable_income"]

    dum60  = pd.Series(0, index=all_yrs); dum60.loc[1960:1986]      = 1
    dum87  = pd.Series(0, index=all_yrs); dum87.loc[1987:2000]      = 1
    dum01b = pd.Series(0, index=all_yrs); dum01b.loc[2001:2017]     = 1
    dum19  = pd.Series(0, index=all_yrs); dum19.loc[2019:last_year] = 1
    active = (dum60 + dum87 + dum01b + dum19).astype(bool)

    corp_df = pd.DataFrame({
        "dl_ist2": dlog(istsoi2_a).astype(float), "dl_zb": dlog(zb_a).astype(float),
        "active": active, "dum60": dum60, "dum87": dum87, "dum01b": dum01b, "dum19": dum19,
    }, dtype=float).dropna(subset=["dl_ist2", "dl_zb"])
    corp_df = corp_df.loc[(corp_df.index >= 1960) & (corp_df.index <= last_act_year)
                          & corp_df["active"].astype(bool)]

    Y_corp = (corp_df["dl_ist2"] * corp_df["active"]).astype(float)
    X_corp = pd.DataFrame({
        "const_all": corp_df["active"],
        "d60_zb"   : corp_df["dum60"]  * corp_df["dl_zb"],
        "d87_zb"   : corp_df["dum87"]  * corp_df["dl_zb"],
        "d01b_zb"  : corp_df["dum01b"] * corp_df["dl_zb"],
        "d19_zb"   : corp_df["dum19"]  * corp_df["dl_zb"],
    }, dtype=float)
    corp_model = sm.OLS(Y_corp, X_corp, missing="drop").fit()
    _print(corp_model)

    c60, c87, c01b, c19 = (corp_model.params[k] for k in ["d60_zb", "d87_zb", "d01b_zb", "d19_zb"])
    etcgf_a = (dum60 * c60 + dum87 * c87 + dum01b * c01b + dum19 * c19).astype(float)
    etcgf_a.loc[:1959] = c60
    # Note: 2018 is in none of the regime dummies, so ETCGF is zero in that year
    # (no cyclical adjustment of corporate receipts in the TCJA transition year).

    # ----------------------------------------------------------
    # 4. ETXGF  (excise and customs tax elasticity)
    # ----------------------------------------------------------
    nipa = load_quarterly_csv(inputs / "nipa_quarterly.csv", qdx)
    gdp_a = annual_sum(nipa["gdp"])
    idx_tx = gdp_a.index
    exc_a = annual_sum(nipa["gfrie"]).reindex(idx_tx)    # excise and customs start later than GDP
    cus_a = annual_sum(nipa["gfrid"]).reindex(idx_tx)
    tot_a = exc_a + cus_a
    dum8086 = pd.Series(0, index=idx_tx); dum8086.loc[1980:1986] = 1

    est_mask_tx = (idx_tx >= 1964) & (idx_tx <= last_act_year)
    Xe = pd.DataFrame({
        "const": 1, "log_gdp": np.log(gdp_a),
        "trend": np.arange(len(gdp_a)), "dum8086": dum8086,
    }, index=idx_tx)
    excise_model  = sm.OLS(np.log(exc_a[est_mask_tx]), Xe[est_mask_tx], missing="drop").fit()
    customs_model = sm.OLS(np.log(cus_a[est_mask_tx]), Xe[est_mask_tx].drop(columns="dum8086"),
                           missing="drop").fit()
    etxgf_a = (excise_model.params["log_gdp"] * (exc_a / tot_a)
               + customs_model.params["log_gdp"] * (cus_a / tot_a))

    # ----------------------------------------------------------
    # 5. UITRATE and UITRATEK  (unemployment insurance tax rates)
    # ----------------------------------------------------------
    uitrate_a  = params["uitrate"]
    uitratek_a = params["uitratek"]

    # ----------------------------------------------------------
    # 6. Trend variables (piecewise linear, quarterly)
    # ----------------------------------------------------------
    def build_trend(start_q, peak_q):
        s  = new_q(qdx, 0.0)
        sp = pd.Period(start_q, "Q")
        pp = pd.Period(peak_q, "Q")
        val = 0.0
        for p in qdx:
            if p == sp:
                val = 0.25; s[p] = val
            elif sp < p <= pp:
                val += 0.25; s[p] = val
            elif p > pp:
                s[p] = val
        return s

    trends = {
        "t53": build_trend("1953Q2", "1957Q2"),
        "t57": build_trend("1957Q3", "1960Q1"),
        "t60": build_trend("1960Q2", "1969Q3"),
        "t69": build_trend("1969Q4", "1973Q3"),
        "t73": build_trend("1973Q4", "1979Q4"),
        "t80": build_trend("1980Q1", "1981Q2"),
        "t81": build_trend("1981Q3", "1990Q2"),
        "t90": build_trend("1990Q3", "2000Q4"),
        "t01": build_trend("2001Q1", "2007Q3"),
        "t07": build_trend("2007Q4", qdx[-1]),
    }

    # ----------------------------------------------------------
    # 7. Carry annual series through last_year, then convert to quarterly
    # ----------------------------------------------------------
    annual = {
        "ess": ess_a, "esst": esst_a, "ept": ept_a, "etb": etb_a, "eby": eby_a,
        "etcgf": etcgf_a, "etxgf": etxgf_a, "uitrate": uitrate_a, "uitratek": uitratek_a,
    }
    exog_data = {k: annual_to_quarterly(extend_annual_series(v, last_year), qdx)
                 for k, v in annual.items()}
    exog_data.update(trends)

    exog_q = pd.DataFrame({k: v.values for k, v in exog_data.items()}, index=qdx)

    # Back-extrapolate ESS/ESST to 1959Q3 (replicates the EViews hebexog logic)
    for col in ["ess", "esst"]:
        p59q4 = pd.Period("1959Q4", "Q"); p59q3 = pd.Period("1959Q3", "Q")
        p60q4 = pd.Period("1960Q4", "Q"); p61q4 = pd.Period("1961Q4", "Q")
        if pd.isna(exog_q.loc[p59q4, col]):
            v4 = exog_q.loc[p60q4, col]; v8 = exog_q.loc[p61q4, col]
            exog_q.loc[p59q4, col] = v4 * (v4 / v8)
            exog_q.loc[p59q3, col] = exog_q.loc[p59q4, col] * (exog_q.loc[p59q4, col] / v4)

    exog_q.index.name = "quarter"
    return exog_q

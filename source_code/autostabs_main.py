"""
autostabs_main.py
Purpose : Estimate the effect of automatic stabilizers on the federal budget by
          cyclically adjusting federal revenues and outlays (CBO's high-employment
          budget model), through the last quarter of actual data.
Usage   : python autostabs_main.py      (run from the source_code/ directory)
Inputs  : ../inputs/   Outputs: ../outputs/
"""

from pathlib import Path

import pandas as pd

from common import make_qindex
from cyclical_adjustment import run_cyclical_adjustment
from elasticities import estimate_elasticities
from output_tables import assemble_output, write_charts, write_csv_outputs

# ============================================================
# Configuration
# ============================================================

LAST_QTR      = "2025Q3"   # last quarter of actual data; the analysis ends here
LAST_ACT_YEAR = 2024       # last complete calendar year of actual data; ends the annual regression samples
FIRST_QTR     = "1945Q1"   # start of the quarterly database

OUT_START_Q   = "1965Q1"   # first quarter in the quarterly output
OUT_START_YR  = 1965       # first year in the annual outputs

RUN_ELASTICITIES = True    # True  = re-estimate the elasticities and save them to ELASTICITIES_CACHE
                           # False = load previously estimated elasticities from ELASTICITIES_CACHE
ELASTICITIES_CACHE = "elasticities_cache.csv"

PRINT_REGRESSIONS = True   # print regression summaries to the console
DECIMALS = 4               # rounding in the CSV outputs

ROOT    = Path(__file__).resolve().parents[1]
INPUTS  = ROOT / "inputs"
OUTPUTS = ROOT / "outputs"

# ============================================================
# Main
# ============================================================

def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    qdx = make_qindex(FIRST_QTR, LAST_QTR)
    last_year = pd.Period(LAST_QTR, "Q").year

    if RUN_ELASTICITIES:
        exog_q = estimate_elasticities(INPUTS, qdx, last_year, LAST_ACT_YEAR, verbose=PRINT_REGRESSIONS)
        exog_q.to_csv(INPUTS / ELASTICITIES_CACHE, float_format="%.9g")
        print(f"Elasticities saved to {INPUTS / ELASTICITIES_CACHE}")
    else:
        exog_q = pd.read_csv(INPUTS / ELASTICITIES_CACHE, index_col=0)
        exog_q.index = pd.PeriodIndex(exog_q.index, freq="Q")
        exog_q = exog_q.reindex(qdx)
        print(f"Elasticities loaded from {INPUTS / ELASTICITIES_CACHE}")

    qb, qca = run_cyclical_adjustment(INPUTS, qdx, exog_q, LAST_QTR, verbose=PRINT_REGRESSIONS)
    df_q = assemble_output(qb, qca)

    print(f"\nWriting output to {OUTPUTS}:")
    write_csv_outputs(df_q, OUTPUTS, OUT_START_Q, OUT_START_YR, decimals=DECIMALS)
    write_charts(df_q, OUTPUTS, OUT_START_Q, OUT_START_YR)
    print("Done.")


if __name__ == "__main__":
    main()

## Inputs
Contains the data files needed for the analysis. All quarterly files are indexed by quarter (e.g., 2025Q3) and end in 2025q3; annual files end in 2024 or 2025.
- `cbo_baseline_quarterly.csv` contains the NIPA and economic series from CBO's February 2026 economic baseline. Source: BEA, CBO estimates.
- `nipa_quarterly.csv` contains additional NIPA detail on federal receipts and unemployment insurance benefits. Source: BEA.
- `heb_history_quarterly.csv` contains historical series carried over from earlier versions of the model
- `tad_corporate_taxes.csv` contains corporate income taxes and Federal Reserve remittances used from 1994 onward
- `covered_wage_ratios.csv` contains the ratios of wages covered by Social Security and unemployment insurance taxes to total wages. Quarterly estimates. Source: CBO.
- `payroll_tax_data.csv` contains Social Security Administration data on covered workers and earnings. Source: Social Security Administration's Annual Statistical Supplement, tables 4.B.
- `payroll_elasticity_projections.csv` contains CBO's estimated payroll tax elasticities for recent years. Source: CBO estimates.
- `agi_history.csv` contains total adjusted gross income from individual income tax returns. Source: CBO Supplemental Revenue data.
- `soi_corporate_income.csv` contains corporate income subject to tax. Source: IRS Statistics of Income.
- `annual_parameters.csv` contains the exogenous tax elasticity and unemployment insurance tax rates. Source: CBO estimates.
- `elasticities_cache.csv` contains the estimated elasticities and trend variables; it is rewritten each time the elasticities are re-estimated

## Outputs
Contains the output files after running the analysis:
- `autostabs_quarterly.csv` contains quarterly actual (`_base`), cyclically adjusted (`_ca`), and cyclical (`_cyc`) values of revenues, outlays, their components, and the economic gaps
- `autostabs_fiscal_year.csv` and `autostabs_calendar_year.csv` contain fiscal-year and calendar-year averages of the same series
- `autostabs_summary_quarterly.csv` and `autostabs_summary_fiscal_year.csv` contain condensed tables of revenues, outlays, and the surplus or deficit, with and without automatic stabilizers, in dollars and as a percent of potential GDP
- `figure1_stabilizer_effect_quarterly.png` and `figure3_stabilizer_effect_fiscal_year.png` plot the effect of automatic stabilizers on the deficit
- `figure2_actual_vs_adjusted_quarterly.png` and `figure4_actual_vs_adjusted_fiscal_year.png` plot the actual and cyclically adjusted deficits

# Overview of the Automatic Stabilizers Model

Automatic stabilizers are the features of the federal budget that cause revenues to fall and outlays to rise when the economy weakens, and the reverse when it strengthens, without any change in law. This model measures their effect by estimating what federal revenues and outlays would have been if the economy had been operating at its potential level of output with unemployment at its noncyclical rate. The difference between actual budget flows and those cyclically adjusted flows is the effect of automatic stabilizers.

The model works with quarterly data from the national income and product accounts (NIPAs), so revenues and outlays are current receipts and current expenditures of the federal government at seasonally adjusted annual rates. The analysis covers 1965 through the last quarter of actual data.

## Steps

**1. Elasticities** (`elasticities.py`). Each major revenue source is linked to its tax base through an elasticity:

- FICA and SECA payroll taxes (`ess`, `esst`): computed from Social Security Administration data on the share of workers and earnings above the taxable maximum.
- Personal income taxes (`ept`): the product of the elasticity of tax liability with respect to adjusted gross income (`etb`, an exogenous input) and the elasticity of adjusted gross income with respect to the NIPA personal tax base (`eby`), estimated by regression in three regimes (through 1986, 1987-2000, 2001 onward).
- Corporate income taxes (`etcgf`): estimated by regressing the growth of corporate income subject to tax on the growth of NIPA corporate profits, again in regimes.
- Excise and customs taxes (`etxgf`): a weighted average of the GDP elasticities of excise taxes and customs duties.
- Unemployment insurance taxes: the effective tax rate (`uitrate`) and its value at the noncyclical unemployment rate (`uitratek`) are exogenous inputs.

**2. Income shares** (`cyclical_adjustment.py`). Each component of the personal and corporate tax bases (wages and salaries, proprietors' income, dividends, interest, rental income, corporate profits) is expressed as a share of potential GDP and regressed on the current and four lagged values of the GDP gap plus piecewise-linear trends. Setting the gap terms to zero gives the cyclically adjusted income shares.

**3. Cyclical outlays.** Unemployment insurance benefits, Medicaid, and SNAP are the outlay categories treated as automatic stabilizers. Changes in each, as a share of potential GDP, are regressed on current and lagged changes in the unemployment gap (using polynomial distributed lags for Medicaid and SNAP). The estimated coefficients are applied to the level of the unemployment gap to remove the cyclical component. Temporary pandemic unemployment programs are removed from unemployment insurance benefits before estimation.

**4. Solution.** The revenue equations (elasticity times tax base, plus a residual that makes the equations reproduce actual data) are solved twice: once at actual values of the tax bases, and once at the cyclically adjusted tax bases with the unemployment insurance tax rate set to `uitratek`. Outlays are the sum of the three cyclical categories plus a residual holding all other spending fixed. The cyclically adjusted deficit is the difference between cyclically adjusted revenues and outlays.

## Notes

- Corporate income taxes are split between taxes excluding Federal Reserve remittances (`tcgfo`), which are cyclically adjusted, and remittances (`tcgffrb`), which are not.
- Annual outputs are averages of the quarterly annual-rate values. Fiscal years run October through September from FY1977 onward and July through June before that; the transition quarter (July-September 1976) is excluded.

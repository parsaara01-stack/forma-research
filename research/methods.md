# Methods & Replication Standard — v0.1

## 1. Scientific status
This repository currently publishes a **data pipeline and hypotheses, not empirical conclusions**. No fitted models or out-of-sample studies are claimed. The interactive simulator is a hypothetical deterministic cash-flow bridge.

## 2. Universe and unit
Prospective full study: historical U.S.-listed common equities within a prespecified market-cap band at each formation date (e.g. $100 million–$5 billion in inflation-adjusted dollars), with sensitivity to Russell 2000 point-in-time membership. Include all former names, failures, delistings, cash takeouts, spin-offs and M&A exits. The initial eight ticker panel is purely to test ingestion and display, not a scientific sample.

Primary panel: firm-quarter; return evaluations: security-month; debt maturities: instrument-year. Link CIK and security IDs with validity windows. Historical ticker alone is not a persistent identifier.

## 3. Dates and fiscal accounting
For each original filing store filing acceptance/publication, accession, measurement end, and any restatement. Monthly signals include filings only after a lag reflecting actual availability. SEC CompanyFacts can contain retrospective recomputations and must not be treated as an immutable historical vintage; use archived original filing documents or a true as-reported vendor database for authoritative point-in-time testing.

Current v0.1 only extracts latest annual 10-K tag values (USD, annual span 330–390 days) and prefers earliest filing per fiscal period and tag available by the configured cutoff. This heuristic is fit for **current observation panels only**; it is not a validated historical backtest reconstruction. Missing values remain null.

## 4. Accounting & capital measurement
Compute every ratio with complete explicit numerator and denominator definitions, unit normalization, interest capitalization treatment, financing lease inclusions and sector comparability. Never divide by negative/zero invested capital and present a meaningful ROIC without flagging that change of definition. For a reliable debt cost distinguish paid coupon, accrual interest, average book-debt cost, variable reference-rate exposure, quoted credit spreads, and the incremental required yield for new financing.

Maintenance vs expansion capex are often not itemized. Capture reported company estimates where available and label inference. Leases, supplier finance, covenant headroom, secured versus unsecured claims, revolver capacity, maturity schedule, equity compensation, convertibles, noncontrolling claims, seniority and collateral matter to financing resilience. R&D capitalization is a planned robustness method, not v0.1 fact.

For banks, REITs, insurers, pre-commercial pharma and commodity producers, define separate measurement protocols; do not compare deposit liabilities or drug-development spend as if they were industrial leverage or maintenance capex.

## 5. Hypothesis testing
- Freeze primary tests and plausible effect thresholds before fitting.
- Define information-available timestamps, training/validation/test windows; avoid overlapping return-label leakage with purged rolling tests.
- Report number of firms/events, attrition, missingness, sector distributions, and summary stats.
- Benchmark against accounting persistence, profitability, momentum, size/value, Fama–French five factors, and a sector/industry model as appropriate.
- Show out-of-sample MAE/RMSE/calibration or event hazard accuracy for *fundamental* forecasts. Separately compute alpha, volatility, tail behavior, cost-adjusted information ratios and turnover for *market* signals.
- Include multiple-testing corrections, clustered standard errors, robust bootstrap uncertainty and regime analysis, not just in-sample R².
- Diagnose adverse selection: highly levered firms might not have been able to borrow even before interest-rate shocks.

## 6. Publishing thresholds
A claim can be labeled **Research result** only when its exact code/data release is reproducible, the sample and methodology are stated, forecast and market-pricing endpoints are separately validated, and out-of-sample diagnostics are reported. Even a positive result is not financial advice.

## 7. Limitations of public-only data
SEC API: publicly available filings, but not historic analyst forecast vintages, complete instrument-level debt prices, corporate action adjusted delisting returns, or historical FTSE Russell membership. Free substitutes are often survivorship-biased and unsuitable for formal asset-pricing claims. Licensing is a research infrastructure decision, not an analytical shortcut.

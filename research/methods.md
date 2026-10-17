# Methods & Replication Standard — v0.2

## 1. Scientific status
This repository currently publishes a **data pipeline and hypotheses, not empirical conclusions**. No fitted models or out-of-sample studies are claimed. The interactive simulator is a hypothetical deterministic cash-flow bridge.

## 2. Universe and unit
Prospective full study: historical U.S.-listed common equities within a prespecified market-cap band at each formation date (e.g. $100 million–$5 billion in inflation-adjusted dollars), with sensitivity to Russell 2000 point-in-time membership. Include all former names, failures, delistings, cash takeouts, spin-offs and M&A exits. The initial eight ticker panel is purely to test ingestion and display, not a scientific sample.

Primary panel: firm-quarter; return evaluations: security-month; debt maturities: instrument-year. Link CIK and security IDs with validity windows. Historical ticker alone is not a persistent identifier.

## 3. Dates and fiscal accounting
For each original filing store filing acceptance/publication, accession, measurement end, and any restatement. Monthly signals include filings only after a lag reflecting actual availability. SEC CompanyFacts can contain retrospective recomputations and must not be treated as an immutable historical vintage; use archived original filing documents or a true as-reported vendor database for authoritative point-in-time testing.

Current v0.2 extracts annual original 10-K facts, in USD or shares as appropriate. It selects the latest supported fiscal end, then the earliest original filing for that end and a shared annual duration (330–390 days). All displayed facts come from that accession. Ambiguous duplicate contexts, nonfinite values, unsupported concepts, amendments and incompatible durations are excluded. Revenue including assessed tax is a last-priority fallback and its source tag remains visible; cross-company tax treatment is not normalized. This is a **current observation panel**, not a validated as-reported historical reconstruction.

A cutoff includes the entire filing date; intraday acceptance timing and trading lags are not modeled. Subsequent amendments are not reconciled. Fiscal end is displayed rather than inferred from the calendar year. CIK is pinned in the pilot universe and ticker/CIK disagreements require manual review.

The SEC response bytes are hashed with SHA-256, optionally archived as deterministic gzip inputs, and referenced by each observation. Six-hour response caching reduces requests; bounded retries handle transient errors and rate limits. A failed historical refresh cannot carry later-filed observations backward. Partial failures retain eligible previous facts with an explicit stale status. Zero-success refreshes leave the published bytes untouched. Validation runs before replacement, output snapshots are content-addressed, and identical refreshes do not rewrite the public dataset.

`python -m engine replicate` checks archived source hashes and reconstructs the displayed facts and metrics without network calls. Reproduction establishes computational consistency, not accounting correctness. Source processing corrections, missing custom tags, original filing interpretation and selection bias still require independent review.

## 4. Accounting & capital measurement
Compute every ratio with complete explicit numerator and denominator definitions, unit normalization, interest capitalization treatment, financing lease inclusions and sector comparability. Never divide by negative/zero invested capital and present a meaningful ROIC without flagging that change of definition. For a reliable debt cost distinguish paid coupon, accrual interest, average book-debt cost, variable reference-rate exposure, quoted credit spreads, and the incremental required yield for new financing.

Maintenance vs expansion capex are often not itemized. Capture reported company estimates where available and label inference. Leases, supplier finance, covenant headroom, secured versus unsecured claims, revolver capacity, maturity schedule, equity compensation, convertibles, noncontrolling claims, seniority and collateral matter to financing resilience. R&D capitalization is a planned robustness method, not an implemented fact.

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


## 8. Implemented capital proxies (v0.2)

- Total debt requires three separately reported, nonnegative components: noncurrent long-term debt, its current portion, and short-term borrowings. A missing component makes total debt and debt/assets unavailable. Broad `LongTermDebt` or lease-inclusive concepts are never added to overlapping components. Leases, guarantees and other debt-note obligations are excluded.
- Interest coverage is operating income divided by positive reported interest expense. This is not EBITDA covenant coverage or a marginal debt yield. Tag-specific scope and capitalized interest may differ.
- FCF is reported operating cash flow less tagged PPE cash expenditure. It does not normalize acquisitions, intangibles, exploration spending or maintenance capex.
- Cash / operating burn uses unrestricted cash and equivalents divided by the magnitude of negative annual CFO. It excludes investments and future capex, so it is **not a forecast of total liquidity runway**.
- Maturity buckets use principal due in the next twelve months, years two through five and thereafter, anchored at fiscal end. They may be partial and are not reconciled to carrying debt; discounts, leases and custom instrument contexts may differ.
- Weighted-average diluted shares, SBC, common-stock cash proceeds and repurchases are reported inputs when available. They do not estimate future option dilution, issuance valuation or per-share value creation.
- Industrial ratios are suppressed for banks and insurers. Marginal debt cost, WACC, floating-rate percentages, debt covenants and maintenance capex remain unestimated.

## 9. Empirical study gate

The protocol is a versioned draft, not an external preregistration. Before fitting H01–H06, freeze the exact sample, treatment, comparator, endpoint, horizons, data definitions, exclusion and missingness rules, chronological splits, minimum effect of interest, multiple-testing family and code release. Separate descriptive current-vintage accounting work from any point-in-time forecasting test. No current site output constitutes a validated empirical finding.

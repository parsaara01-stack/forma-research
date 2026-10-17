# forma.
### The economics beneath the ticker.

**An open, empirical research laboratory studying how smaller public companies fund growth, deploy capital and create—or destroy—per-share value.**

> Status: **v0.1 | reproducible prototype | not a validated predictive model.**
> The website is launchable. The scientific study and historical backtest are **not complete**.

## Research objective

**How do capital requirements, financing structure, and marginal costs interact with operating performance to determine small-company financial resilience and subsequent shareholder returns?**

This is intentionally broader than predicting earnings recovery. A single reported EPS recovery can be driven by operating improvement, loss-base effects, index turnover, acquisitions, a lower share count, or one-off charges. We model operations, funding and pricing separately.

**Working paper:** *The Capital Conversion Gap: Financing Frictions, Reinvestment Intensity, and Value Creation in Small Public Companies.*

## Live architecture

Inspired by the workflow of [PRSN](https://github.com/parsaara01-stack/prsn-index), but isolated from its investment selection rules:

```
Official SEC CompanyFacts       Research protocol / hypotheses
           |                              |
   Python extraction                   Version control
           |                              |
Annual tagged observation panel  <---/    |
           |                              |
Metric validation / audit trail          |
           |                              |
      Versioned JSON ---------------------/
           |
Static accessible website  --> GitHub Actions  --> GitHub Pages
```

The repository uses only Python's standard library for SEC data processing and vanilla HTML/CSS/JS for the website. No API keys are needed except an identifiable SEC contact email for compliant request headers.

## Local preview

```bash
python3 -m http.server 8000 --directory site
# open http://localhost:8000
```

Do not open `site/index.html` directly using a `file://` URL: browsers restrict local JSON fetching. The website's eight launch tickers are **not populated with real financial values until an SEC refresh succeeds**. The Laboratory simulator is explicitly hypothetical.

## Data collection

```bash
export SEC_CONTACT='your-real-contact@example.com'
python3 -m engine refresh --archive
python3 -m engine validate
```

Requirements: Python 3.11+, internet access to sec.gov and data.sec.gov. Requests are throttled. The SEC can return access limits. On a complete network failure the current published dataset is preserved. Partial failures retain previous observations where available and mark them stale; logs appear in `refresh_warnings`.

The generated live site reads `site/data/research.json`; optional dated snapshots are in `data/snapshots/`. The first observation sample has 8 purposely heterogeneous firms. **It is not a Russell 2000 historical membership dataset.** Avoid index-wide inference or trading conclusions from this group.

## Run tests

```bash
python3 -m unittest discover -s tests -v
python3 -m engine validate
python3 -m compileall -q engine tests
```

The fixture data used in tests is synthetic, used only to validate behavior. The pipeline never silently substitutes zero for a missing regulatory fact.

## Publish on GitHub Pages

1. Create an empty repository, e.g. `parsaara01-stack/forma-research`. Keep the existing `prsn-index` repository unchanged.
2. Copy or push **all contents of this folder** onto that repository's `main` branch.
3. In **Settings → Pages → Build and deployment → Source**, select **GitHub Actions**.
4. In **Settings → Secrets and variables → Actions**, set `SEC_CONTACT` to a real contact email; never commit the email if you prefer it private.
5. Open **Actions → Publish forma. → Run workflow**, check **Update SEC filing panel**, and run. The workflow validates, optionally updates SEC annual observations, archives the snapshot, and deploys the website.
6. The initial site also publishes automatically on pushes to `main`. Twice-weekly scheduled refreshes only download current facts when `SEC_CONTACT` is configured.

GitHub's deployment uses `actions/configure-pages@v5`, `actions/upload-pages-artifact@v4`, and `actions/deploy-pages@v4` with `pages: write` and `id-token: write` in the deployment job. Review GitHub Pages documentation if organization or branch policies block deployment.

Suggested URL after GitHub Pages activation: `https://parsaara01-stack.github.io/forma-research/` (**not live until independently deployed**).

## Research modules

| Hypothesis | Research question | Status |
| --- | --- | --- |
| H01 Capital conversion gap | Is externally financed growth associated with lower subsequent per-share value than internally funded growth, conditional on opportunity set? | Protocol only |
| H02 Refinancing cliff | Do funding-cost resets reduce investment, profitability and equity valuations? | Protocol only |
| H03 Incremental ROIC | Does reinvestment productivity predict future cash flows beyond growth and trailing ROIC? | Protocol only |
| H04 Recovery illusion | Do cash flow and financing measures explain analyst forecast errors for rebound firms? | Protocol only |
| H05 Dilution and real options | When does issuance fund positive-NPV survival or destroy value? | Protocol only |
| H06 Index composition | How much index-level EPS growth reflects constituent changes and accounting/denominator effects? | Protocol only |

See `research/` for hypothesis registration, competing explanations, methods, data dictionary, capital taxonomy, and publication standards.

## Research limitations (read before citing)

- SEC XBRL provides filed historical accounting facts; it does not provide analyst forecast vintages, security returns, market-cap histories, index membership, or debt-market pricing. Those require other licensed or curated inputs.
- Annual facts are aligned by fiscal-period **end date** and filter source filing dates, but **CompanyFacts is not a complete historical vintage archive**. It can reflect later processing or changes. This is a current-facts prototype, **not** proof of an as-known-at-the-time backtest.
- The first SEC disclosure for an annual period is preferred for each chosen tag; it is *not* equivalent to reconciling every original 10-K form and amendment.
- Tags are heterogeneous. Some firms use custom taxonomy extensions; some accounting metrics are unavailable and remain null. Sector-specific normalization (especially banks, REITs, energy and pre-revenue biotech) is a future data-engineering milestone.
- `debt_to_assets` is intentionally null unless both current and noncurrent debt tags are present; it is not total indebtedness and excludes most lease obligations and guarantees.
- Financing rates, weighted-average cost of capital, debt maturity walls, debt covenants, leases, and maintenance capex are **not inferred** from the preliminary CompanyFacts facts; these require sourced instrument/narrative extraction.
- Historical returns must include delistings, corporate actions, transaction costs, and an ex-ante size classification before any alpha claims are made.
- Do not rely on this platform for investment decisions. This is an independent, evolving research artifact, not investment advice.

## Repository map

```
site/                  Publishable, responsive single-page website
site/data/             Machine-readable regulatory observations (starter values absent)
data/universe.json     Curated pilot observation panel
data/snapshots/        Archived outputs (only after --archive)
engine/                SEC ingestion and reproducible metric definitions
research/              Pre-registered questions, research and brand specification
tests/                 Synthetic fixtures and automated checks
.github/workflows/     Tests, scheduled SEC refresh, GitHub Pages deployment
```

## Publication and citation protocol

A finding is not called **validated** until the hypothesis has a frozen definition, the data can be recreated, sources and data-availability dates are traceable, comparisons account for standard risk factors and implementation costs, and the test survives out-of-sample evaluation. See `research/methods.md`.

Project start: October 17, 2026. Site/engine release: **0.1.0**. Software code is MIT-licensed; underlying third-party data may be subject to their own terms.

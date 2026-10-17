# forma.
### The economics beneath the ticker.

An independent research platform studying how smaller public companies fund growth, deploy capital and create—or destroy—per-share value.

**v0.2.1: working SEC observation platform. Twenty pilot companies have live, source-linked annual facts. All observations are unreviewed; there are no validated predictive findings or completed market-pricing backtests.**

## Research objective

How do capital requirements, financing structure and marginal financing costs interact with operating performance to determine financial resilience and subsequent shareholder returns?

The platform separates operating improvement, funding requirements, per-share outcomes, market expectations and price discovery. Earnings recovery is one mechanism under investigation. The six proposed research questions and their nulls are in [`research/protocol.json`](research/protocol.json); they are draft specifications, not external preregistrations.

Working paper: *The Capital Conversion Gap: Financing Frictions, Reinvestment Intensity, and Value Creation in Small Public Companies.*

## Preview

Python 3.11+ is sufficient for the engine and website. No production JavaScript dependencies or frontend build are required.

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
# Open http://127.0.0.1:8000
```

Open any company to inspect its reported facts, fiscal and filing dates, source tags, original filing index, capital proxies, partial maturity buckets and input fingerprint. The simulator is a deterministic hypothetical business, not a stock forecast. The 20-company pilot tests filing coverage; it is not a current or historical Russell 2000 membership sample.

## Refresh and reproduce

```sh
export SEC_CONTACT='your-real-contact@example.com'
python3 -m engine refresh --archive
python3 -m engine validate
python3 -m engine replicate
python3 -m engine build
```

The contact is sent only in SEC request headers. Keep it in your local environment or the repository's `SEC_CONTACT` Actions secret; do not commit credentials or personal configuration.

- Requests are paced at no more than five per second per client, cached for six hours and retried for transient network/server failures or rate limits. Do not run parallel clients beyond SEC's aggregate request limit.
- Raw SEC response bytes are SHA-256 fingerprinted. `--archive` preserves deterministic compressed inputs in `data/raw/` and content-addressed output snapshots in `data/snapshots/`. Different same-day outputs have different filenames; existing snapshots are never overwritten.
- `--force` bypasses the response cache. `--asof YYYY-MM-DD` applies an inclusive filing-date cutoff; it **does not recreate a historical database vintage**.
- `replicate` checks source hashes and re-extracts every displayed fact and metric offline. To reproduce a saved output, use `python3 -m engine replicate --snapshot data/snapshots/FILE.json` with the matching engine release.
- A failed company retains an eligible prior observation with an explicit stale label. Future-filed facts cannot carry backward through this fallback. Zero-success refreshes and invalid payloads preserve the published bytes. Identical refreshes do not rewrite the dataset.
- `build` copies versioned methods, hypotheses, protocol, variable dictionary, capital taxonomy and references into the public site. Edit the originals in `research/`, then rebuild.

The initial live collection was performed October 17, 2026. Fiscal ends and source dates vary by company. A successful retrieval means SEC tags were collected, not that their accounting interpretation was independently verified.

If macOS Python reports a certificate verification failure, install its trusted certificate bundle using that Python distribution's documented setup or use a correctly configured Python runtime. Do not disable TLS verification.

## Accounting boundaries

Extraction selects a single original 10-K accession for the latest supported fiscal end and uses one annual statement duration. It rejects ambiguous duplicate contexts, incompatible units and nonfinite values. Amendments, custom taxonomies and instrument-level note contexts require separate review. Per-fact source tags expose accounting differences, including the last-priority revenue-including-tax fallback.

Debt/assets requires noncurrent long-term debt, its current portion and short-term borrowings, all explicitly reported. Missing components remain unavailable; broad or lease-inclusive tags are never added to overlapping components. Maturity buckets can be partial and must be reconciled to the debt note. Marginal funding cost, WACC, covenants, floating-rate exposure, maintenance capex and future dilution remain unestimated.

FCF is CFO less tagged PPE cash expenditure, not a comprehensive measure of all investment. Cash/operating-burn is a narrow cash coverage ratio, not a total liquidity runway forecast. Industrial ratios are suppressed for banks and insurers. See [`research/methods.md`](research/methods.md) for definitions and exclusions.

## Quality checks

```sh
python3 -m unittest discover -s tests -v
python3 -m engine validate
python3 -m engine replicate
python3 -m compileall -q engine tests
```

Browser checks use Node.js 24, pnpm 11.25.0 and locked development dependencies:

```sh
pnpm install --frozen-lockfile
pnpm exec playwright install chromium
pnpm test
```

The browser suite starts its own local server. It checks desktop/mobile layout, calculator arithmetic, search, filters, modal keyboard focus, data failures, stale labels, unsafe links and automated WCAG A/AA accessibility rules. It saves previews in `test-results/`. Automated accessibility checks do not replace manual assistive-technology review. Test-only synthetic responses never enter the published data.

## GitHub publication and updates

The architecture follows [PRSN](https://github.com/parsaara01-stack/prsn-index): a Python engine, versioned data, a static website and scheduled GitHub Pages publishing. forma. has its own repository, scientific protocol and data model; it does not reuse PRSN's investment selection rules.

1. Create an empty **`parsaara01-stack/forma-research`** repository, without an initial README or license. Push this repository's `main` branch to it.
2. In **Settings → Pages → Build and deployment**, choose **GitHub Actions**.
3. Add a real contact email as **Settings → Secrets and variables → Actions → New repository secret → `SEC_CONTACT`**.
4. Confirm the workflow token can commit data under your branch rules. Required PR policies may require adapting the refresh to a data PR instead of direct pushes; the workflow will fail safely if a push is rejected.
5. Run **Actions → Publish forma.**, optionally enabling the SEC refresh. Tests, offline replication and browser checks gate deployment. Only `site/` is published.

Pushes to `main` publish after checks. Scheduled runs refresh on **Tuesday and Friday at 06:22 UTC**, subject to GitHub scheduling delays. Missing contact configuration produces a workflow warning and preserves the visibly dated prior dataset. Refresh failures block that deployment. Data commits made with `GITHUB_TOKEN` do not need to trigger another workflow; the same successful run deploys its tested output. Concurrent source changes cause the data push to fail rather than overwrite them.

Planned URL: `https://parsaara01-stack.github.io/forma-research/`. **This is not a claim that the site has been deployed.**

## Scientific publication gate

Historical expectations, complete security returns including delistings, and point-in-time index membership are not provided by CompanyFacts. They require licensed or independently curated datasets. No price targets, fitted recovery probabilities, alpha estimates or research conclusions are invented to fill those gaps.

Before fitting, freeze the exact exposures, comparators, endpoint definitions, sample and exclusion rules, date lags, chronological train/test windows, minimum effect sizes and multiple-testing family. Evaluate fundamental forecasting separately from cost-adjusted, factor-controlled return prediction. Report missingness, attrition, uncertainty and negative results. See `research/` for the proposed study and publication standards.

## Repository map

| Path | Purpose |
| --- | --- |
| `site/` | Public website and downloadable research documentation |
| `engine/` | Standard-library SEC ingestion, metrics, validation and replication |
| `data/universe.json` | Curated pilot with pinned CIK identities |
| `data/raw/` | Hashed SEC response archives; no request headers or contact email |
| `data/snapshots/` | Immutable output snapshots |
| `research/` | Draft study protocol, hypotheses, methods and source registry |
| `tests/` | Synthetic regression fixtures and real-browser checks |
| `.github/workflows/` | CI, scheduled refresh and gated Pages deployment |

v0.1 was imported unchanged from the supplied archive before development. Its archive hash and baseline commit are recorded in `data/import-provenance.json`, and its full source remains in local Git history. Software is MIT licensed. Third-party data retains its source terms. Research, not investment advice.

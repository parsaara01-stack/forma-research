# forma

When does growth pay off?

A working research workspace for small-cap investment timing — the economy, profits, earnings expectations and the price you pay

[Live study](https://parsaara01-stack.github.io/forma-research/) · [Portfolio article](https://parsaara.com/forma) · [Homepage](https://parsaara.com/home)

## What works

- Complete usable listed equity coverage from IWM's official, dated holdings file
- Membership rotation with saved additions, exits and original holdings files
- Annual SEC company evidence, source filing links, capital proxies and reported EPS history
- Dated FRED policy rate, Treasury yield, yield curve, unemployment and inflation readings
- An interactive timing lab with earnings, valuation, dilution, holding period and required-return controls
- Earnings / valuation sensitivity grid, annual EPS history and macro trends
- Search, sector filters and pagination across the full coverage group
- Individual company evidence loads on demand, keeping the initial page small
- A separate business calculator for borrowing costs, spending and dilution
- Reproducible archives, automated checks and GitHub Pages deployment

**The current stock list is IWM's listed equity holdings, a Russell 2000 proxy — not certified index membership**
Cash, derivatives, tickerless and unlisted residual positions are documented outside the stock panel
Exact current or historical Russell constituents require an authorized dated index feed

## Timing research status

The product can calculate scenarios and show observed data
It does not yet have a fitted timing model, a calibrated entry probability or a validated buy signal

The forward EPS field is a user assumption, not an analyst forecast
The study will test entry before earnings recover, after reported improvement and after price repricing, against holding IWM and simple alternatives
Historical analyst estimates, original macro release vintages and complete security returns including delistings remain required inputs

The draft nine-question protocol is in `research/protocol.json`
The proposed timing study and calculator equations are in `research/timing.md`
No backtest results or predictive performance are invented

## Run locally

Python 3.11+ serves the website and runs the engine without production dependencies

```sh
python3 -m engine build
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8000

## Refresh and reproduce

```sh
export SEC_CONTACT='your-real-contact@example.com'
python3 -m engine universe
python3 -m engine macro
python3 -m engine refresh --archive
python3 -m engine build
python3 -m engine validate
python3 -m engine verify-sources
python3 -m engine replicate
```

Keep the contact in the environment or the existing GitHub `SEC_CONTACT` secret
It is sent only in SEC request headers and is not committed

`universe` downloads the official IWM CSV, checks the source date, row count, weights, duplicate symbols and turnover before replacing coverage
Original holdings and dated membership snapshots retain additions and exits going forward
`sync` applies membership changes and prices to the public panel without changing annual-report refresh dates
It is used on weekdays without a full SEC collection

`macro` accepts FRED CSV or its mixed-frequency ZIP response, saves original bytes and publishes dated series
Observation dates are not publication dates and current revised data is not an original-vintage historical trading feed

`refresh --archive` uses up to four concurrent downloads behind one limiter of four request starts per second
Compressed, hash-checked response caches make interrupted runs resumable
403 access denials stop new requests
A full-universe refresh requires at least 85% successful observations or preserves the prior public dataset
Per-company failures retain eligible saved evidence with an older-data label, or remain missing
Ticker / CIK identity conflicts require review and do not reuse another issuer's evidence

Raw source files are content-addressed and compressed
New research snapshots use `.json.gz` to limit storage growth
`replicate --snapshot PATH` supports original JSON and new compressed snapshots
It verifies raw fingerprints and rebuilds company facts, financial ratios and EPS history offline
`verify-sources` independently rebuilds holdings and macro values from their raw archives
Snapshots and raw inputs accumulate over time and need storage monitoring

On macOS, a correctly configured Python trust store is required
Use the operating system's trusted certificate bundle if appropriate for the Python distribution
Do not disable TLS verification

## Automatic updates

GitHub Actions checks holdings and macro each weekday at 07:22 UTC
Full SEC report collection runs Tuesday and Friday, or when manually requested
GitHub can delay scheduled runs
New holdings enter the panel immediately with missing report data until collection succeeds
Prices are provider holdings valuations, not live executable quotes

Source and browser checks gate deployment
Data failures block that publication and preserve the previous live site
Validated data commits and the tested site deploy in the same workflow
Concurrent source changes cause a failed push rather than overwriting another edit

## Accounting boundaries

Facts use one original 10-K accession and coherent annual duration per fiscal period
Amendments, custom taxonomies, instrument terms and complete debt-note reconciliation need separate review
Annual figures are not current-quarter or trailing-twelve-month earnings
EPS uses the reported diluted EPS tag in USD/shares and stays missing where unsupported

Debt / assets requires all three nonoverlapping debt components
Missing components are not treated as zero
Maturity buckets may cover only part of total debt
The platform does not estimate marginal funding costs or WACC from accounting data
Industrial ratios are suppressed for the Financials sector

Free cash flow is operating cash flow minus tagged property and equipment spending
It excludes other investment and is not a complete cash distribution forecast
Reported observations are unreviewed until their accounting interpretation is checked

## Quality checks

```sh
python3 -m unittest discover -s tests -v
python3 -m engine validate
python3 -m engine verify-sources
python3 -m engine replicate
python3 -m engine build
pnpm install --frozen-lockfile
pnpm exec playwright install chromium
pnpm test
```

Tests cover source integrity, incomplete lists, dates, membership changes, identity, accounting units, cash calculations, timing arithmetic, dilution, invalid scenarios, pagination, failure states, responsive layout, keyboard focus and automated WCAG A/AA checks
Development uses Node 24 and pnpm 11.25.0
Only `site/` is deployed

## Project files

| Path | Purpose |
| --- | --- |
| `site/` | Three-section public product and research downloads |
| `engine/` | Standard-library source collection, calculations and replication |
| `data/universe.json` | Dated current IWM equity proxy |
| `data/membership/` | Saved membership changes |
| `data/holdings/`, `data/macro/`, `data/raw/` | Fingerprinted source archives |
| `data/snapshots/` | Immutable company observations |
| `research/` | Draft protocol, methods and timing research |
| `portfolio/` | Cover, article text and publication records |
| `tests/` | Source, financial and browser checks |

The supplied v0.1 archive remains preserved in Git history
The architecture follows the independent PRSN project's publishing approach
Software is MIT licensed and third-party data retains its source terms
The dark small-business cover was generated with OpenAI image generation and is a conceptual illustration, not a photograph of actual index constituents

Research, not investment advice

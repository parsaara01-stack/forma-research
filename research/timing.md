# When does growth pay off?

## Objective
Find a better time to invest in small caps by testing the economy, company profits, earnings expectations and the entry price together

## What works today
- Complete usable listed IWM equity coverage, refreshed from the provider's dated CSV
- Membership additions and exits recorded from the first complete import forward
- Source-linked original annual SEC reports, financing proxies and annual EPS histories where the taxonomy supports them
- Dated FRED interest-rate, yield-curve, inflation and employment observations
- A scenario calculator for future EPS, valuation, additional shares, holding period and required return
- A sensitivity grid showing how different EPS and valuation assumptions change annual price returns

These calculations describe assumptions, not a learned forecast or an optimal investment date

## The timing question
Compare entry before earnings recovery, entry after sustained reported improvement and entry after expectations and price have adjusted

The primary proposed endpoint is 12-month total return relative to IWM after costs, at matched risk
Secondary endpoints are 6- and 24-month returns, drawdown, distress, missed upside, turnover and time waiting in cash
Use a stated cash return for uninvested time rather than treating waiting as free

## Inputs and separation
- Macro: policy rates, yield curve, inflation, unemployment and credit conditions, using original release vintages in historical tests
- Profitability: trailing and quarterly EPS, margin changes, cash conversion and the share of companies improving
- Outlook: original-vintage analyst estimates, upward/downward revisions, forecast dispersion and guidance changes
- Funding: cash, borrowing cost, maturity schedule, floating-rate exposure, debt covenants and new shares
- Price: valuation, returns and momentum, liquidity, volatility and expectations already priced in

Reported EPS and future EPS are distinct variables
Annual statements are not trailing-twelve-month earnings and can be too old for a timing decision
Growth rates crossing a loss or zero base require separate classifications rather than percentage EPS growth
Do not apply industrial debt or cash-flow ratios to financial firms without a separate sector protocol

## Historical study design — not yet fitted
Freeze hypotheses, thresholds, allowed inputs, transformations and outcomes before fitting
Use dated membership including entrants, exits, bankruptcies and delistings
Preserve original report publication times and trade no sooner than the following trading session
Account for splits, distributions, corporate actions, transaction costs and delisting returns
Compare IWM buy-and-hold, equal monthly investment, a lagged profitability rule and a simple price-trend rule
Train in expanding chronological windows, purge overlapping return labels and reserve the final period untouched
Use sector and size controls, market beta, liquidity and volatility controls
Evaluate calibration and uncertainty separately from trading performance
Correct for testing many timing rules and report failed ideas

## Product boundary
The current complete stock list is IWM's usable listed equity holdings, an investable proxy for Russell 2000 exposure
The fund can hold positions that differ from the index, including cash, derivatives and unlisted residual holdings
Those positions are recorded outside the stock panel, with reasons
Exact current or historical index membership requires an authorized dated constituent feed
No analyst estimate feed or complete security total-return feed is currently connected
FRED observation dates are not release dates; its latest revised histories must not be used as if they were known on those dates
A calibrated timing probability, buy signal or claim of optimal timing remains unavailable until these inputs and historical tests exist

## Scenario definition
Future diluted EPS = user EPS assumption / (1 + extra shares / 100)
Future price = future diluted EPS × assumed exit price/earnings multiple
Annual price return = (future price / entry price)^(1 / years) − 1
Entry price meeting required return = future price / (1 + required annual return / 100)^years

Future EPS is the assumed value at the end of the entire holding period, before extra share issuance
It is not an annual EPS growth rate
The sensitivity grid varies EPS and price/earnings independently by ±25%, with no probability assigned
The model requires positive future earnings; price/earnings is inappropriate for a projected loss
The tool excludes dividends, fees, taxes and corporate actions
Prices in the holdings file are provider valuations, not real-time executable quotes

## Price trends and the two chart clocks

H10 tests whether a 200-trading-day simple moving average adds value after the economy, earnings and valuation are included
The 4-hour view is a separate exploratory lens, not a 200-day moving average calculated from 4-hour bars
Specify regular sessions, exchange timezone, split adjustment and signal availability before fitting a rule
Use only completed bars known at the decision time, trade no earlier than the next tradable bar, and test incremental value after spreads, fees and turnover
An apparent crossing of an average is not an entry recommendation
The public TradingView displays are not a licensed point-in-time backtest dataset

## Preloaded calculator assumptions

A selected profitable company starts with a transparent example of 10% yearly EPS growth over the initially selected holding period and a future P/E of 20
A company without positive annual EPS starts with a clearly marked recovery example of $1 future EPS
These examples explain the controls and imply no forecast confidence, analyst endorsement or recommended valuation
Changing fields changes the scenario, not the underlying reported facts

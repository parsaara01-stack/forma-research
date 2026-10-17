# Contributing to forma.

The repository is a public research artifact, not a venue for unsupported stock recommendations.

1. For every proposed metric, specify source, units, denominator, accounting standard, fiscal period, filing date and missing-data behavior.
2. For hypothesis changes, submit a documented amendment to `research/protocol.json` before running out-of-sample tests; do not silently rewrite preregistered hypotheses.
3. Run `python -m unittest discover -s tests -v` and `python -m engine validate`.
4. Distinguish SEC-reported accounting facts from normalized research calculations and market-vendor estimates.
5. No direct personally identifiable information, account credentials, API tokens, licensed raw datasets or private company claims should be committed.
6. Interpret null as unavailable, never as zero; preserve `refresh_warnings` and historical sample exclusions.
7. Include failure cases and uncertainty. Claims of persistent abnormal return require out-of-sample, transaction-cost, and factor control evidence.

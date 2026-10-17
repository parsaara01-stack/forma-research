"""Reported earnings evidence; projected earnings are intentionally absent."""
from datetime import date
from .sec import _anchors, choose_fact, extract_annual, TAGS


def earnings_evidence(full: dict, asof: date) -> dict:
    ends = sorted({r['end'] for r in _anchors(full, asof)}, reverse=True)[:4]
    history = []
    for end in ends:
        _, facts = extract_annual(full, asof, target_end=end)
        if not facts:
            continue
        anchor = next(iter(facts.values()))
        starts = [v['start'] for v in facts.values() if v.get('start')]
        eps = choose_fact(full, ['EarningsPerShareDiluted'], end, asof,
                          accession=anchor['accession'], start=starts[0] if starts else None, unit='USD/shares')
        history.append({'end': end, 'filed': anchor['filed'], 'accession': anchor['accession'],
                        'source_url': anchor['source_url'],
                        'eps': eps, 'revenue': facts.get('revenue'), 'net_income': facts.get('net_income'),
                        'diluted_shares': facts.get('diluted_shares'),
                        'operating_cash_flow': facts.get('operating_cash_flow')})
    return {'annual_history': history, 'forecast_eps': None,
            'forecast_status': 'Analyst forecasts are not connected; any forward EPS in the tool is a user assumption',
            'basis': 'Original annual US-GAAP reports, not quarterly or trailing-twelve-month earnings'}

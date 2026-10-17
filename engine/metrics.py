"""Explicit accounting proxies. Missing components are never imputed as zero."""
from __future__ import annotations
from math import isfinite


def get(facts: dict, field: str) -> float | None:
    v = facts.get(field, {}).get('value')
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v) else None


def safe_ratio(a, b, *, positive_base=True):
    if a is None or b is None or not isfinite(a) or not isfinite(b) or b == 0 or (positive_base and b < 0):
        return None
    result = a / b
    return result if isfinite(result) else None


def calculate(facts: dict, group: str = '') -> dict:
    r, op, cfo, capex = (get(facts, k) for k in ('revenue', 'operating_income', 'operating_cash_flow', 'capex'))
    assets, ltd, curr, short, interest = (get(facts, k) for k in
        ('total_assets', 'long_term_debt', 'current_debt', 'short_term_borrowings', 'interest_expense'))
    ni, sbc = (get(facts, k) for k in ('net_income', 'share_based_compensation'))
    fcf = cfo - capex if cfo is not None and capex is not None and capex >= 0 else None
    debt = ltd + curr + short if all(x is not None and x >= 0 for x in (ltd, curr, short)) else None
    cash = get(facts, 'cash')
    bank = group.lower() in {'banking', 'financials', 'banks', 'insurance', 'insurers'}
    values = {
        'operating_margin': safe_ratio(op, r), 'free_cash_flow': fcf,
        'free_cash_flow_margin': safe_ratio(fcf, r), 'capex_intensity': safe_ratio(capex, r) if capex is not None and capex >= 0 else None,
        'cfo_to_positive_net_income': safe_ratio(cfo, ni) if ni is not None and ni > 0 else None,
        'total_debt': debt, 'debt_to_assets': safe_ratio(debt, assets),
        'net_debt': debt - cash if debt is not None and cash is not None else None,
        'interest_coverage': safe_ratio(op, interest) if interest is not None and interest > 0 else None,
        'share_based_compensation_to_revenue': safe_ratio(sbc, r),
        'current_ratio': safe_ratio(get(facts, 'current_assets'), get(facts, 'current_liabilities')),
        'cash_runway_years': safe_ratio(cash, -cfo) if cfo is not None and cfo < 0 else None,
        'near_term_maturity_to_cash': safe_ratio(get(facts, 'maturity_year_1'), cash),
    }
    return {k: None if bank else v for k, v in values.items()}


def capital_profile(facts: dict, group: str = '') -> dict:
    financial = group.lower() in {'banking', 'financials', 'banks', 'insurance', 'insurers'}
    buckets = [get(facts, f'maturity_year_{n}') for n in range(1, 6)]
    return {
        'sector_protocol': 'financial-sector review required' if financial else 'nonfinancial accounting proxies',
        'maturities': {'years_1_to_5': buckets, 'thereafter': get(facts, 'maturity_thereafter'),
                       'status': 'tagged-partial-needs-note-review' if any(v is not None for v in buckets + [get(facts, 'maturity_thereafter')]) else 'not-available',
                       'definition': 'Long-term debt principal buckets relative to fiscal end; coverage is not a complete instrument schedule.'},
        'financing_cost': {'marginal_cost': None, 'weighted_average_cost_of_capital': None,
                           'status': 'not-estimated; requires market prices and instrument terms'},
        'review_required': ['Debt-note reconciliation and total coverage', 'Floating-rate share and reset dates',
                            'Leases, collateral, revolvers and covenants', 'Convertibles and contingent dilution',
                            'Maintenance versus expansion capex'],
    }

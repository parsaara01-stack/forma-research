"""Research metrics: explicit definitions and no imputation of missing inputs."""
from __future__ import annotations
from math import isfinite

def get(facts:dict, field:str) -> float|None:
    v=facts.get(field,{}).get('value')
    return float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v) else None

def safe_ratio(a:float|None,b:float|None,*,positive_base:bool=True) -> float|None:
    if a is None or b is None or b==0 or (positive_base and b<0):
        return None
    return a/b

def calculate(facts:dict, group:str="") -> dict:
    r=get(facts,'revenue'); op=get(facts,'operating_income'); cfo=get(facts,'operating_cash_flow'); capex=get(facts,'capex')
    assets=get(facts,'total_assets'); ltd=get(facts,'long_term_debt'); curr=get(facts,'current_debt'); interest=get(facts,'interest_expense')
    ni=get(facts,'net_income'); sbc=get(facts,'share_based_compensation')
    fcf=(cfo-capex) if cfo is not None and capex is not None else None
    # IMPORTANT: missing current debt or noncurrent debt must not be silently treated as zero.
    debt=(ltd+curr) if ltd is not None and curr is not None else None
    bank=group.lower() in {'banking','financials','banks'}
    return {
        'operating_margin':None if bank else safe_ratio(op,r),
        'free_cash_flow':None if bank else fcf,
        'free_cash_flow_margin':None if bank else safe_ratio(fcf,r),
        'capex_intensity':None if bank else safe_ratio(capex,r),
        'cfo_to_positive_net_income':None if bank or ni is None or ni<=0 else safe_ratio(cfo,ni),
        'debt_to_assets':None if bank else safe_ratio(debt,assets),
        'interest_coverage':None if bank or interest is None or interest<=0 else safe_ratio(op,interest,positive_base=False),
        'share_based_compensation_to_revenue':None if bank else safe_ratio(sbc,r),
    }

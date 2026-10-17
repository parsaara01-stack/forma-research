"""Minimal respectful SEC CompanyFacts client and defensible annual fact extraction.

NOT an as-reported historical database: SEC CompanyFacts may include facts and
corrections not exposed in the original publication. As-of filtering limits
filing dates but does not solve database-vintage biases. See research/methods.md.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date
from typing import Any

SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueGoodsNet"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"],
    "current_debt": ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent", "ShortTermBorrowings"],
    "interest_expense": ["InterestExpenseNonOperating", "InterestExpense", "InterestAndDebtExpense"],
    "depreciation": ["DepreciationDepletionAndAmortization", "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment"],
    "share_based_compensation": ["ShareBasedCompensation"],
}
STOCK_FIELDS = {"total_assets", "total_liabilities", "equity", "cash", "long_term_debt", "current_debt"}

class SECError(RuntimeError):
    pass

class SECClient:
    def __init__(self, contact: str, delay_seconds: float = .24, timeout: int = 20):
        if not contact or "@" not in contact or "." not in contact:
            raise ValueError("SEC_CONTACT must be a real contact email for the SEC User-Agent")
        self.contact = contact
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self.last_request_at = 0.0

    def get_json(self, url: str) -> Any:
        delay = self.delay_seconds - (time.monotonic() - self.last_request_at)
        if delay > 0:
            time.sleep(delay)
        req = urllib.request.Request(url, headers={
            "User-Agent": f"forma-research/0.1 contact {self.contact}",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
                result = json.loads(raw)
                if not isinstance(result, (dict, list)):
                    raise SECError("Unexpected JSON document type")
                return result
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TimeoutError) as exc:
            raise SECError(f"SEC retrieval failure for {url}: {exc}") from exc
        finally:
            self.last_request_at = time.monotonic()

    def resolve_tickers(self) -> dict[str, dict]:
        source = self.get_json(SEC_TICKERS)
        return {str(v['ticker']).upper():v for v in source.values() if isinstance(v, dict) and 'ticker' in v}

    def company_facts(self, cik: int) -> dict:
        return self.get_json(SEC_FACTS.format(cik=cik))


def _is_annual(observation: dict, *, stock: bool, asof: date) -> bool:
    if observation.get("form") != "10-K" or observation.get("fp") != "FY":
        return False
    try:
        filed=date.fromisoformat(observation["filed"])
        end=date.fromisoformat(observation["end"])
        if filed > asof or end > asof:
            return False
        if stock:
            return "start" not in observation
        start=date.fromisoformat(observation["start"])
        return 330 <= (end-start).days <= 390
    except (TypeError, ValueError, KeyError):
        return False


def find_anchor(companyfacts: dict, asof: date) -> str | None:
    """Find latest annual end shared by assets or income tags; no fiscal-year guesses."""
    facts=companyfacts.get('facts',{}).get('us-gaap',{})
    ends=[]
    for tag, stock in (("Assets",True), ("NetIncomeLoss",False), ("Revenues",False), ("OperatingIncomeLoss",False)):
        usd=facts.get(tag,{}).get('units',{}).get('USD',[])
        ends += [o['end'] for o in usd if _is_annual(o,stock=stock,asof=asof)]
    return max(ends) if ends else None


def choose_fact(companyfacts:dict,tags:list[str],end:str,asof:date,*,stock:bool=False) -> dict | None:
    """Prefer first tagged concept with an on-period annual observation.

    For each tag take the earliest filing that disclosed that end date. A later
    amended filing is not selected over an available earlier observation.
    """
    facts=companyfacts.get('facts',{}).get('us-gaap',{})
    for tag in tags:
        unit_rows=facts.get(tag,{}).get('units',{}).get('USD',[])
        matches=[o for o in unit_rows if o.get('end')==end and _is_annual(o,stock=stock,asof=asof)
                 and isinstance(o.get('val'),(int,float)) and not isinstance(o.get('val'),bool)]
        if matches:
            matches.sort(key=lambda r:(r['filed'],r.get('accn','')))
            o=matches[0]
            accession=o.get('accn','')
            cik=int(companyfacts.get('cik',0))
            archive=f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace("-", "")}/' if accession else None
            return {'value':o['val'],'tag':tag,'end':end,'filed':o['filed'],'accession':accession,
                    'source_url':archive,'source':'SEC CompanyFacts US-GAAP','form':'10-K','unit':'USD'}
    return None


def extract_annual(companyfacts:dict,asof:date) -> tuple[str|None,dict]:
    end=find_anchor(companyfacts,asof)
    if not end:
        return None,{}
    facts={}
    for field,tags in TAGS.items():
        chosen=choose_fact(companyfacts,tags,end,asof,stock=field in STOCK_FIELDS)
        if chosen is not None:
            facts[field]=chosen
    return end,facts

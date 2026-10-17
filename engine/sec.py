"""SEC retrieval and conservative, filing-coherent annual extraction.

CompanyFacts is a current database, not an as-reported historical database.
Original 10-K only: amendments require a separate reviewed reconciliation.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
TAGS = {
    'revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'],
    'operating_income': ['OperatingIncomeLoss'],
    'net_income': ['NetIncomeLoss'],
    'operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
    'capex': ['PaymentsToAcquirePropertyPlantAndEquipment'],
    'total_assets': ['Assets'], 'total_liabilities': ['Liabilities'],
    'equity': ['StockholdersEquity'],
    'cash': ['CashAndCashEquivalentsAtCarryingValue'],
    # These components deliberately exclude ambiguous total-debt and lease tags.
    'long_term_debt': ['LongTermDebtNoncurrent'],
    'current_debt': ['LongTermDebtCurrent'],
    'short_term_borrowings': ['ShortTermBorrowings'],
    'interest_expense': ['InterestExpenseNonOperating', 'InterestAndDebtExpense', 'InterestExpense'],
    'depreciation': ['DepreciationDepletionAndAmortization'],
    'share_based_compensation': ['ShareBasedCompensation'],
    'current_assets': ['AssetsCurrent'], 'current_liabilities': ['LiabilitiesCurrent'],
    'diluted_shares': ['WeightedAverageNumberOfDilutedSharesOutstanding'],
    'equity_issuance': ['ProceedsFromIssuanceOfCommonStock'],
    'share_repurchases': ['PaymentsForRepurchaseOfCommonStock'],
    **{f'maturity_year_{n}': [f'LongTermDebtMaturitiesRepaymentsOfPrincipalInYear{word}']
       for n, word in enumerate(['One', 'Two', 'Three', 'Four', 'Five'], 1)},
    'maturity_thereafter': ['LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive'],
}
TAGS['maturity_year_1'] = ['LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths']
STOCK_FIELDS = {'total_assets', 'total_liabilities', 'equity', 'cash', 'long_term_debt',
                'current_debt', 'short_term_borrowings', 'current_assets', 'current_liabilities',
                *[k for k in TAGS if k.startswith('maturity_')]}
UNITS = {'diluted_shares': 'shares'}


class SECError(RuntimeError):
    pass


def atomic_write(path: Path, raw: bytes) -> None:
    """Replace complete bytes; callers validate before publication."""
    import os
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(raw)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class SECClient:
    def __init__(self, contact: str, delay_seconds: float = .25, timeout: int = 25,
                 cache_dir: Path | None = None, archive_dir: Path | None = None,
                 cache_ttl: int = 21600, retries: int = 3):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', contact or ''):
            raise ValueError('SEC_CONTACT must be a contact email for the SEC User-Agent')
        self.contact = contact
        self.delay_seconds = max(.2, delay_seconds)
        self.timeout, self.retries = timeout, retries
        self.cache_dir, self.archive_dir, self.cache_ttl = cache_dir, archive_dir, cache_ttl
        self.last_request_at = 0.0
        self.documents: dict[str, dict] = {}

    def _remember(self, url: str, raw: bytes, retrieved_at: str, cached: bool) -> Any:
        try:
            result = json.loads(raw, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        except (ValueError, UnicodeDecodeError) as exc:
            raise SECError('SEC returned invalid JSON') from exc
        if not isinstance(result, dict):
            raise SECError('SEC returned an unexpected document type')
        digest = hashlib.sha256(raw).hexdigest()
        meta = {'url': url, 'sha256': digest, 'retrieved_at': retrieved_at, 'cache_hit': cached}
        if self.archive_dir:
            target = self.archive_dir / f'{digest}.json.gz'
            compressed = gzip.compress(raw, mtime=0)
            if target.exists():
                if gzip.decompress(target.read_bytes()) != raw:
                    raise SECError('Raw archive hash collision or corruption')
            else:
                atomic_write(target, compressed)
            meta['raw_path'] = f'data/raw/{target.name}'
        self.documents[url] = meta
        return result

    def get_json(self, url: str) -> Any:
        if not (url.startswith('https://data.sec.gov/') or url.startswith('https://www.sec.gov/')):
            raise SECError('Only official SEC HTTPS endpoints are allowed')
        key = hashlib.sha256(url.encode()).hexdigest()
        cache = self.cache_dir / f'{key}.json' if self.cache_dir else None
        if cache and cache.exists():
            try:
                item = json.loads(cache.read_text())
                raw = item['raw'].encode()
                age = time.time() - datetime.fromisoformat(item['retrieved_at']).timestamp()
                if 0 <= age < self.cache_ttl and hashlib.sha256(raw).hexdigest() == item['sha256']:
                    return self._remember(url, raw, item['retrieved_at'], True)
            except (ValueError, KeyError, TypeError, OSError, SECError):
                pass  # Never substitute a corrupt or expired cache on a network failure.
        req = urllib.request.Request(url, headers={
            'User-Agent': f'forma-research/0.2 contact {self.contact}',
            'Accept': 'application/json', 'Accept-Encoding': 'identity',
        })
        for attempt in range(self.retries + 1):
            wait = self.delay_seconds - (time.monotonic() - self.last_request_at)
            if wait > 0:
                time.sleep(wait)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    raw = response.read()
                retrieved = datetime.now(timezone.utc).isoformat()
                result = self._remember(url, raw, retrieved, False)
                if cache:
                    atomic_write(cache, json.dumps({'retrieved_at': retrieved,
                        'sha256': hashlib.sha256(raw).hexdigest(), 'raw': raw.decode()}).encode())
                return result
            except urllib.error.HTTPError as exc:
                retryable = exc.code in {429, 500, 502, 503, 504}
                retry_after = exc.headers.get('Retry-After', '') if exc.headers else ''
                if attempt == self.retries or not retryable:
                    raise SECError(f'SEC HTTP {exc.code} for {url}') from exc
                pause = min(30, max(2 ** attempt, int(retry_after) if retry_after.isdigit() else 0))
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == self.retries:
                    raise SECError(f'SEC network failure for {url}: {exc}') from exc
                pause = 2 ** attempt
            finally:
                self.last_request_at = time.monotonic()
            time.sleep(pause)
        raise SECError('SEC retries exhausted')

    def resolve_tickers(self) -> dict[str, dict]:
        source = self.get_json(SEC_TICKERS)
        resolved = {str(v['ticker']).upper(): v for v in source.values()
                    if isinstance(v, dict) and 'ticker' in v and 'cik_str' in v}
        if not resolved:
            raise SECError('Empty SEC ticker directory')
        return resolved

    def company_facts(self, cik: int) -> dict:
        result = self.get_json(SEC_FACTS.format(cik=cik))
        if int(result.get('cik', 0)) != cik or not isinstance(result.get('facts'), dict):
            raise SECError('CompanyFacts CIK or document structure mismatch')
        return result


def _is_annual(observation: dict, *, stock: bool, asof: date) -> bool:
    if observation.get('form') != '10-K' or observation.get('fp') != 'FY':
        return False
    try:
        filed, end = (date.fromisoformat(observation[k]) for k in ('filed', 'end'))
        if filed > asof or end > filed or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', observation.get('accn', '')):
            return False
        if stock:
            return 'start' not in observation
        return 330 <= (end - date.fromisoformat(observation['start'])).days <= 390
    except (TypeError, ValueError, KeyError):
        return False


def _anchors(companyfacts: dict, asof: date) -> list[dict]:
    facts = companyfacts.get('facts', {}).get('us-gaap', {})
    candidates = []
    for field in ('total_assets', 'revenue', 'net_income', 'operating_income'):
        for tag in TAGS[field]:
            candidates += [o for o in facts.get(tag, {}).get('units', {}).get('USD', [])
                           if _is_annual(o, stock=field in STOCK_FIELDS, asof=asof)]
    return candidates


def find_anchor(companyfacts: dict, asof: date) -> str | None:
    candidates = _anchors(companyfacts, asof)
    return max(o['end'] for o in candidates) if candidates else None


def choose_fact(companyfacts: dict, tags: list[str], end: str, asof: date, *, stock: bool = False,
                accession: str | None = None, start: str | None = None, unit: str = 'USD') -> dict | None:
    """Select a finite fact from a specific filing and duration when supplied."""
    facts = companyfacts.get('facts', {}).get('us-gaap', {})
    for tag in tags:
        matches = [o for o in facts.get(tag, {}).get('units', {}).get(unit, [])
                   if o.get('end') == end and _is_annual(o, stock=stock, asof=asof)
                   and (accession is None or o['accn'] == accession)
                   and (stock or start is None or o.get('start') == start)
                   and isinstance(o.get('val'), (int, float)) and not isinstance(o['val'], bool)
                   and math.isfinite(o['val'])]
        if matches:
            matches.sort(key=lambda o: (o['filed'], o['accn']))
            earliest = matches[0]
            same = [o for o in matches if (o['filed'], o['accn']) == (earliest['filed'], earliest['accn'])]
            if len({(o.get('start'), o['val']) for o in same}) != 1:
                continue  # Ambiguous contexts must be reviewed, never chosen by array order.
            accn = earliest['accn']
            cik = int(companyfacts.get('cik', 0))
            return {'value': earliest['val'], 'tag': tag, 'start': earliest.get('start'),
                    'end': end, 'filed': earliest['filed'], 'accession': accn,
                    'source_url': f'https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace("-", "")}/{accn}-index.html',
                    'source': 'SEC CompanyFacts US-GAAP', 'form': '10-K', 'unit': unit}
    return None


def extract_annual(companyfacts: dict, asof: date) -> tuple[str | None, dict]:
    candidates = _anchors(companyfacts, asof)
    if not candidates:
        return None, {}
    end = max(o['end'] for o in candidates)
    anchor = min((o for o in candidates if o['end'] == end), key=lambda o: (o['filed'], o['accn']))
    accession = anchor['accn']
    # A single statement duration prevents combining different reporting spans.
    starts = [o['start'] for o in candidates if o['end'] == end and o['accn'] == accession and 'start' in o]
    start = Counter(starts).most_common(1)[0][0] if starts else None
    result = {}
    for field, tags in TAGS.items():
        if field not in STOCK_FIELDS and start is None:
            continue
        chosen = choose_fact(companyfacts, tags, end, asof, stock=field in STOCK_FIELDS,
                             accession=accession, start=start, unit=UNITS.get(field, 'USD'))
        if chosen:
            result[field] = chosen
    return end, result

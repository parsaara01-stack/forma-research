"""Dated IWM equity coverage, with an explicit boundary from licensed index membership."""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from .sec import atomic_write

HOLDINGS_URL = 'https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/latest-holdings.csv'


def symbol(value: str) -> str:
    return value.strip().upper().replace(' ', '-').replace('.', '-')


def parse_holdings(raw: bytes, today: date) -> dict:
    text = raw.decode('utf-8-sig')
    lines = list(csv.reader(io.StringIO(text)))
    stamp = next((r[1] for r in lines if len(r) > 1 and r[0] == 'Fund Holdings as of'), None)
    if stamp is None:
        raise ValueError('IWM holdings date missing')
    effective = datetime.strptime(stamp, '%b %d, %Y').date()
    if not 0 <= (today - effective).days <= 10:
        raise ValueError('IWM holdings are future dated or more than 10 days old')
    header = next((n for n, r in enumerate(lines) if r[:2] == ['Ticker', 'Name']), None)
    if header is None:
        raise ValueError('IWM CSV header missing')
    companies, excluded, seen = [], [], set()
    for row in csv.DictReader(io.StringIO('\n'.join(text.splitlines()[header:]))):
        if not row.get('Name'):
            continue
        ticker = symbol(row.get('Ticker', ''))
        reason = None
        if row.get('Asset Class') != 'Equity':
            reason = 'Non-equity holding'
        elif ticker in {'', '-'} or not re.fullmatch(r'[A-Z0-9]+(?:-[A-Z0-9]+)*', ticker):
            reason = 'No usable public ticker'
        elif row.get('Exchange') == 'NO MARKET (E.G. UNLISTED)':
            reason = 'Unlisted position'
        if reason:
            excluded.append({'name': row['Name'], 'ticker': row.get('Ticker'), 'reason': reason})
            continue
        if ticker in seen:
            raise ValueError(f'Duplicate normalized IWM ticker: {ticker}')
        seen.add(ticker)
        weight, price = (float(row[k].replace(',', '')) for k in ('Weight (%)', 'Price'))
        if not (0 <= weight <= 10 and 0 <= price <= 1_000_000):
            raise ValueError('Invalid holdings weight or price')
        companies.append({'ticker': ticker, 'source_ticker': row['Ticker'], 'name': row['Name'],
                          'group': row['Sector'], 'weight_percent': weight, 'holding_price': price,
                          'price_date': effective.isoformat(), 'exchange': row['Exchange']})
    if not 1500 <= len(companies) <= 2400 or not 90 <= sum(r['weight_percent'] for r in companies) <= 105:
        raise ValueError('Incomplete IWM equity universe; prior coverage preserved')
    return {'version': '0.3.0', 'effective': effective.isoformat(), 'source_kind': 'iwm-holdings-proxy',
            'purpose': 'All usable listed IWM equities; an investable Russell 2000 proxy, not certified index membership',
            'companies': companies, 'excluded_holdings': excluded,
            'membership_note': 'Fund positions differ from index constituents; official historical membership requires a licensed dated feed'}


def refresh_universe(root: Path, today: date, raw: bytes | None = None) -> dict:
    if raw is None:
        request = urllib.request.Request(HOLDINGS_URL, headers={'User-Agent': 'forma-research/0.3 public research'})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
    candidate = parse_holdings(raw, today)
    path = root / 'data/universe.json'
    old = json.loads(path.read_text()) if path.exists() else {}
    if old.get('source_kind') == 'iwm-holdings-proxy':
        if candidate['effective'] < old['effective']:
            raise ValueError('Holdings date moved backward; prior universe preserved')
        before, after = ({r['ticker'] for r in u['companies']} for u in (old, candidate))
        if len(before.symmetric_difference(after)) / len(before) > .35:
            raise ValueError('Unexpected membership turnover above 35%; review the source before replacing coverage')
    else:
        before = set()
        after = {r['ticker'] for r in candidate['companies']}
    digest = hashlib.sha256(raw).hexdigest()
    saved = f'data/holdings/{digest}.csv.gz'
    candidate['source_document'] = {'url': HOLDINGS_URL, 'sha256': digest, 'raw_path': saved,
                                    'retrieved_at': datetime.now(timezone.utc).isoformat()}
    candidate['changes'] = {'basis': 'prior saved IWM snapshot' if before else 'initial complete holdings import',
                            'added': sorted(after - before), 'removed': sorted(before - after)}
    candidate['sec_mapping'] = 'Resolved independently by ticker against the SEC directory; unmatched companies stay visible'
    atomic_write(root / saved, gzip.compress(raw, mtime=0))
    encoded = (json.dumps(candidate, indent=2, allow_nan=False) + '\n').encode()
    snapshot = root / 'data/membership' / f"{candidate['effective']}-{digest}.json"
    # Preserve the first observation of each source file, including its actual retrieval timestamp
    if snapshot.exists():
        candidate = json.loads(snapshot.read_text())
        encoded = snapshot.read_bytes()
    else:
        atomic_write(snapshot, encoded)
    atomic_write(path, encoded)
    return {'tracked_equities': len(candidate['companies']), 'effective': candidate['effective'],
            'excluded_positions': len(candidate['excluded_holdings']), 'added': len(candidate['changes']['added']),
            'removed': len(candidate['changes']['removed'])}


def verify_universe(root: Path) -> dict:
    universe = json.loads((root / 'data/universe.json').read_text())
    doc = universe.get('source_document')
    if not doc:
        return {'universe': 'legacy-pilot'}
    expected = f"data/holdings/{doc['sha256']}.csv.gz"
    if doc.get('raw_path') != expected:
        raise ValueError('Invalid holdings archive path')
    raw = gzip.decompress((root / expected).read_bytes())
    if hashlib.sha256(raw).hexdigest() != doc['sha256']:
        raise ValueError('Holdings archive fingerprint mismatch')
    parsed = parse_holdings(raw, date.fromisoformat(universe['effective']))
    if parsed['companies'] != universe['companies'] or parsed['excluded_holdings'] != universe['excluded_holdings']:
        raise ValueError('Universe differs from archived IWM holdings')
    return {'verified_equities': len(parsed['companies']), 'effective': universe['effective']}

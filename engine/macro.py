"""Public macro context with dates and raw provenance, never a fitted timing signal."""
from __future__ import annotations
import csv
import gzip
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from .sec import atomic_write

SERIES = {'DFF': ('Policy rate', '%'), 'DGS10': ('10-year Treasury', '%'),
          'T10Y2Y': ('10-year minus 2-year yield', 'percentage points'),
          'UNRATE': ('Unemployment', '%'), 'CPIAUCSL': ('Consumer prices', 'index')}
URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + ','.join(SERIES)


def parse_macro(raw: bytes, cutoff: date) -> dict:
    files = [raw]
    if raw.startswith(b'PK'):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            files = [archive.read(name) for name in archive.namelist() if name.endswith('.csv')]
    observations = {key: {} for key in SERIES}
    for content in files:
        for row in csv.DictReader(io.StringIO(content.decode('utf-8-sig'))):
            stamp = row.get('observation_date') or row.get('DATE')
            if not stamp or date.fromisoformat(stamp) > cutoff:
                continue
            for key in SERIES:
                try:
                    value = float(row.get(key, ''))
                    if math.isfinite(value):
                        observations[key][stamp] = value
                except (TypeError, ValueError):
                    pass
    result = []
    for key, (label, unit) in SERIES.items():
        values = sorted(observations[key].items())
        if not values:
            raise ValueError(f'FRED series {key} missing')
        latest_date, value = values[-1]
        # Three calendar months, not a hard-coded number of daily records
        compare = date.fromisoformat(latest_date)
        prior = [v for stamp, v in values if (compare - date.fromisoformat(stamp)).days >= 90]
        change = value - prior[-1] if prior else None
        history = [{'date': d, 'value': v} for d, v in values if (cutoff - date.fromisoformat(d)).days <= 400]
        if key == 'CPIAUCSL':
            year = compare.replace(year=compare.year - 1)
            base = observations[key].get(year.isoformat())
            value = (value / base - 1) * 100 if base and base > 0 else None
            label, unit, change = 'Inflation over one year', '%', None
            history = [{'date': d, 'value': (v / observations[key][f'{int(d[:4])-1}{d[4:]}'] - 1) * 100}
                       for d, v in values if f'{int(d[:4])-1}{d[4:]}' in observations[key] and (cutoff - date.fromisoformat(d)).days <= 400]
        result.append({'series': key, 'label': label, 'unit': unit, 'value': value, 'date': latest_date,
                       'change_90d': change, 'history': history, 'source_url': f'https://fred.stlouisfed.org/series/{key}',
                       'status': 'stale' if (cutoff - compare).days > (75 if key in {'UNRATE', 'CPIAUCSL'} else 10) else 'current'})
    return {'asof_cutoff': cutoff.isoformat(), 'series': result,
            'note': 'Current FRED database vintage; dates are observation dates, not release dates — not valid historical trading inputs'}


def refresh_macro(root: Path, cutoff: date, raw: bytes | None = None) -> dict:
    if raw is None:
        with urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'forma-research/0.3'}), timeout=60) as response:
            raw = response.read()
    payload = parse_macro(raw, cutoff)
    digest = hashlib.sha256(raw).hexdigest()
    saved = f'data/macro/{digest}.bin.gz'
    payload['source_document'] = {'url': URL, 'sha256': digest, 'raw_path': saved,
                                  'retrieved_at': datetime.now(timezone.utc).isoformat()}
    atomic_write(root / saved, gzip.compress(raw, mtime=0))
    atomic_write(root / 'site/data/macro.json', (json.dumps(payload, indent=2, allow_nan=False) + '\n').encode())
    return {'macro_series': len(payload['series']), 'cutoff': cutoff.isoformat()}


def verify_macro(root: Path) -> dict:
    payload = json.loads((root / 'site/data/macro.json').read_text())
    doc = payload['source_document']
    expected = f"data/macro/{doc['sha256']}.bin.gz"
    if doc.get('raw_path') != expected:
        raise ValueError('Invalid macro archive path')
    raw = gzip.decompress((root / expected).read_bytes())
    if hashlib.sha256(raw).hexdigest() != doc['sha256']:
        raise ValueError('Macro archive fingerprint mismatch')
    rebuilt = parse_macro(raw, date.fromisoformat(payload['asof_cutoff']))
    if rebuilt['series'] != payload['series']:
        raise ValueError('Macro values differ from archived data')
    return {'verified_macro_series': len(payload['series'])}

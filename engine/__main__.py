"""Refresh, validate, and package the public research artifact."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
import pathlib
import re
import sys
from datetime import date, datetime, timezone
from .sec import SECClient, extract_annual, SECError, SEC_FACTS, atomic_write, UNITS
from .metrics import calculate, capital_profile

ROOT = pathlib.Path(__file__).resolve().parents[1]
UNIVERSE = ROOT / 'data/universe.json'
OUTPUT = ROOT / 'site/data/research.json'


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def validate_payload(d: dict) -> dict:
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(d.get('schema_version') in {'0.1.0', '0.2.0'}, 'Unsupported dataset schema')
    rows = d.get('companies')
    require(isinstance(rows, list) and bool(rows), 'Dataset needs companies')
    tickers = []
    cutoff = date.fromisoformat(d['asof_cutoff']) if d.get('asof_cutoff') else None
    for r in rows:
        ticker = r.get('ticker')
        require(isinstance(ticker, str) and bool(re.fullmatch(r'[A-Z0-9.\-]+', ticker)), 'Invalid ticker')
        tickers.append(ticker)
        require(isinstance(r.get('facts'), dict), f'Missing facts for {ticker}')
        facts = r['facts']
        observation_cutoff = date.fromisoformat(r.get('observation_cutoff', d.get('asof_cutoff'))) if facts else cutoff
        if facts:
            require(observation_cutoff <= cutoff, 'Observation cutoff exceeds dataset cutoff')
        accessions, starts = set(), set()
        for field, fact in facts.items():
            import math
            value = fact.get('value')
            require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), 'Nonfinite fact')
            require(fact.get('source') == 'SEC CompanyFacts US-GAAP', 'Unexpected source')
            require(fact.get('unit') == UNITS.get(field, 'USD') and fact.get('form') == '10-K', 'Wrong unit or form')
            filed, end = (date.fromisoformat(fact[k]) for k in ('filed', 'end'))
            require(cutoff is not None and end <= filed <= observation_cutoff, 'Fact exceeds information cutoff')
            require(fact['end'] == r.get('fiscal_end'), 'Fiscal end mismatch')
            accn = fact.get('accession', '')
            require(bool(re.fullmatch(r'\d{10}-\d{2}-\d{6}', accn)), 'Invalid accession')
            source = f'https://www.sec.gov/Archives/edgar/data/{int(r["cik"])}/{accn.replace("-", "")}/{accn}-index.html'
            require(fact.get('source_url') == source, 'Unexpected filing URL')
            accessions.add(accn)
            if fact.get('start'):
                start = date.fromisoformat(fact['start'])
                require(330 <= (end - start).days <= 390, 'Invalid annual duration')
                starts.add(fact['start'])
        require(len(accessions) <= 1 and len(starts) <= 1, 'Mixed filings or statement durations')
        if facts:
            require(r.get('observation_status') in {'sec-xbrl-unreviewed', 'stale-previous-snapshot'}, 'Unrecognized observation status')
            require(r.get('metrics') == calculate(facts, r.get('group', '')), 'Metrics differ from defined calculations')
            require(r.get('capital_profile') == capital_profile(facts, r.get('group', '')), 'Capital profile mismatch')
            require(r.get('primary_filing_url') in {x['source_url'] for x in facts.values()}, 'Primary filing mismatch')
            doc = r.get('source_document', {})
            require(bool(re.fullmatch(r'[a-f0-9]{64}', doc.get('sha256', ''))), 'Missing input fingerprint')
            require(doc.get('url') == SEC_FACTS.format(cik=int(r['cik'])), 'Unexpected input URL')
            datetime.fromisoformat(doc['retrieved_at'])
        else:
            require(not r.get('metrics'), 'Metrics without facts')
    require(len(tickers) == len(set(tickers)), 'Duplicate companies')
    return {'validated_rows': len(rows), 'rows_with_facts': sum(bool(r['facts']) for r in rows)}


def _safe_prior(record: dict, asof: date) -> bool:
    """A failed historical refresh must never carry future observations backward."""
    try:
        if record.get('observation_cutoff') and date.fromisoformat(record['observation_cutoff']) > asof:
            return False
        return bool(record.get('facts')) and all(
            date.fromisoformat(f['filed']) <= asof and date.fromisoformat(f['end']) <= asof
            for f in record['facts'].values())
    except (ValueError, KeyError, TypeError):
        return False


def _semantic(payload):
    value = copy.deepcopy(payload)
    for key in ('generated_at', 'last_successful_refresh', 'source_documents'):
        value.pop(key, None)
    for r in value.get('companies', []):
        if 'source_document' in r:
            r['source_document'].pop('retrieved_at', None)
            r['source_document'].pop('cache_hit', None)
    return value


def code_provenance() -> dict:
    import subprocess
    from . import __version__
    result = {'engine_version': __version__}
    try:
        result['git_commit'] = subprocess.check_output(
            ['git', '-C', str(ROOT), 'log', '-1', '--format=%H', '--', 'engine/'], text=True, stderr=subprocess.DEVNULL).strip()
        result['engine_has_local_changes'] = subprocess.run(
            ['git', '-C', str(ROOT), 'diff', '--quiet', 'HEAD', '--', 'engine/'],
            stderr=subprocess.DEVNULL).returncode != 0
    except (OSError, subprocess.CalledProcessError):
        result['git_commit'] = None
    return result


def refresh(asof: date, archive: bool = False, force: bool = False) -> dict:
    if asof > datetime.now(timezone.utc).date():
        raise ValueError('Information cutoff cannot be in the future')
    client = SECClient(os.environ.get('SEC_CONTACT', ''), cache_dir=ROOT / '.cache/sec',
                       archive_dir=ROOT / 'data/raw' if archive else None, cache_ttl=0 if force else 21600)
    universe = json.loads(UNIVERSE.read_text())
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'companies': []}
    prior = {r['ticker']: r for r in previous.get('companies', [])}
    resolved = client.resolve_tickers()
    final, errors, successes = [], [], 0
    for entry in universe['companies']:
        ticker = entry['ticker'].upper()
        record = {**entry, 'facts': {}, 'metrics': {}, 'observation_status': 'missing'}
        try:
            match = resolved.get(ticker)
            if not match:
                raise SECError(f'{ticker} absent from current SEC directory; review identity manually')
            cik = int(entry.get('cik', match['cik_str']))
            if cik != int(match['cik_str']):
                raise SECError('Pinned CIK differs from current ticker identity; manual review required')
            full = client.company_facts(cik)
            end, facts = extract_annual(full, asof)
            if not end or not facts:
                raise SECError(f'No supported annual facts by {asof}')
            document = {k: v for k, v in client.documents[SEC_FACTS.format(cik=cik)].items() if k != 'cache_hit'}
            record.update(cik=cik, fiscal_year=end[:4], fiscal_end=end, facts=facts,
                          metrics=calculate(facts, entry.get('group', '')),
                          capital_profile=capital_profile(facts, entry.get('group', '')),
                          observation_status='sec-xbrl-unreviewed', observation_cutoff=asof.isoformat(), source_document=document,
                          primary_filing_url=next(iter(facts.values()))['source_url'])
            successes += 1
        except (SECError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'{ticker}: {exc}')
            old = prior.get(ticker, {})
            if _safe_prior(old, asof) and (not entry.get('cik') or old.get('cik') == entry['cik']):
                record = copy.deepcopy(old)
                record['observation_status'] = 'stale-previous-snapshot'
                record['metrics'] = calculate(record['facts'], record.get('group', ''))
                record['capital_profile'] = capital_profile(record['facts'], record.get('group', ''))
            record['refresh_error'] = str(exc)
        final.append(record)
    if successes == 0:
        raise SECError('Zero fresh observations; published dataset preserved. ' + '; '.join(errors)[:600])
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        'schema_version': '0.2.0', 'generated_at': now, 'last_successful_refresh': now,
        'status': 'Unreviewed SEC-tagged observations; no validated predictive findings',
        'universe_description': 'Curated current pilot; not historical Russell membership',
        'asof_cutoff': asof.isoformat(), 'companies': final, 'refresh_warnings': errors,
        'code_provenance': code_provenance(),
        'source_documents': [{k: v for k, v in doc.items() if k != 'cache_hit'} for doc in client.documents.values()],
    }
    validate_payload(payload)  # Validate everything before touching the public dataset.
    changed = _semantic(previous) != _semantic(payload)
    if not changed:
        payload = previous
    raw = encoded(payload)
    if archive:
        digest = hashlib.sha256(raw).hexdigest()
        snapshot = ROOT / 'data/snapshots' / f'{asof.isoformat()}-{digest}.json'
        if snapshot.exists() and snapshot.read_bytes() != raw:
            raise SECError('Immutable snapshot collision')
        if not snapshot.exists():
            atomic_write(snapshot, raw)
    if changed:
        atomic_write(OUTPUT, raw)
    return {'companies': len(final), 'fresh': successes, 'warnings': len(errors),
            'cutoff': asof.isoformat(), 'changed': changed}


def replicate(snapshot: pathlib.Path) -> dict:
    """Verify archived bytes and rebuild each observation without a network request."""
    import gzip
    dataset = json.loads(snapshot.read_text())
    validate_payload(dataset)
    verified = set()
    for source in dataset.get('source_documents', []):
        expected = f"data/raw/{source['sha256']}.json.gz"
        if source.get('raw_path') != expected:
            raise ValueError('Snapshot source is not archived')
        raw = gzip.decompress((ROOT / expected).read_bytes())
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('Snapshot source fingerprint mismatch')
        verified.add(source['sha256'])
    count = 0
    for record in dataset['companies']:
        if not record.get('facts'):
            continue
        doc = record['source_document']
        expected = f"data/raw/{doc['sha256']}.json.gz"
        if doc.get('raw_path') != expected:
            raise ValueError('Raw archive path is absent or invalid; refresh with --archive')
        raw = gzip.decompress((ROOT / expected).read_bytes())
        if hashlib.sha256(raw).hexdigest() != doc['sha256']:
            raise ValueError('Raw source fingerprint mismatch')
        verified.add(doc['sha256'])
        full = json.loads(raw)
        if int(full['cik']) != int(record['cik']):
            raise ValueError('Raw input CIK mismatch')
        cutoff = date.fromisoformat(record.get('observation_cutoff', dataset['asof_cutoff']))
        end, facts = extract_annual(full, cutoff)
        if end != record['fiscal_end'] or facts != record['facts']:
            raise ValueError(f"Re-extracted facts differ for {record['ticker']}")
        if calculate(facts, record.get('group', '')) != record['metrics']:
            raise ValueError('Recomputed metrics differ')
        count += 1
    return {'reproduced_companies': count, 'network_requests': 0, 'verified_raw_documents': len(verified)}


def build() -> dict:
    target = ROOT / 'site/research'
    names = ['methods.md', 'hypotheses.md', 'capital_taxonomy.md', 'protocol.json', 'variables.csv', 'references.md']
    for name in names:
        atomic_write(target / name, (ROOT / 'research' / name).read_bytes())
    return {'packaged_research_files': len(names)}


def validate() -> dict:
    return validate_payload(json.loads(OUTPUT.read_text()))


def main():
    p = argparse.ArgumentParser(description='forma. research engine')
    p.add_argument('command', choices=['refresh', 'validate', 'build', 'replicate'])
    p.add_argument('--snapshot', type=pathlib.Path, help='Archived dataset to reproduce offline (default: current public dataset)')
    p.add_argument('--asof', help='Inclusive filing-date cutoff; not a historical database vintage')
    p.add_argument('--archive', action='store_true', help='Preserve hashed raw inputs and immutable output snapshot')
    p.add_argument('--force', action='store_true', help='Bypass the six-hour SEC response cache')
    args = p.parse_args()
    try:
        if args.command == 'refresh':
            result = refresh(date.fromisoformat(args.asof) if args.asof else datetime.now(timezone.utc).date(), args.archive, args.force)
        elif args.command == 'replicate':
            result = replicate(args.snapshot or OUTPUT)
        elif args.command == 'build':
            result = build()
        else:
            result = validate()
    except (ValueError, SECError, KeyError, TypeError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

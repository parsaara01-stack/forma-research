"""Command-line entry point for forma. data refresh and validation."""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import sys
from datetime import datetime,date,timezone
from .sec import SECClient,extract_annual,SECError
from .metrics import calculate

ROOT=pathlib.Path(__file__).resolve().parents[1]
UNIVERSE=ROOT/'data'/'universe.json'
OUTPUT=ROOT/'site'/'data'/'research.json'

def refresh(asof:date, archive:bool=False) -> dict:
    contact=os.environ.get('SEC_CONTACT','')
    client=SECClient(contact)
    universe=json.loads(UNIVERSE.read_text())
    previous=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'companies':[]}
    prior={x['ticker']:x for x in previous.get('companies',[])}
    resolved=client.resolve_tickers()
    final=[]
    errors=[]
    successes=0
    for entry in universe['companies']:
        ticker=entry['ticker'].upper()
        record={**entry, 'facts':{},'metrics':{}}
        try:
            if ticker not in resolved:
                raise SECError(f'Ticker {ticker} not found in current SEC ticker directory')
            cik=int(resolved[ticker]['cik_str'])
            full=client.company_facts(cik)
            end,facts=extract_annual(full,asof)
            if not end or not facts:
                raise SECError(f'No annual 10-K USD facts for {ticker} as of {asof}')
            record.update({'cik':cik,'fiscal_year':end[:4], 'fiscal_end':end,'facts':facts,
                           'metrics':calculate(facts,entry.get('group','')), 'observation_status':'verified-sec-xbrl'})
            links=[x.get('source_url') for x in facts.values() if x.get('source_url')]
            record['primary_filing_url']=next(iter(links),None)
            successes+=1
        except (SECError,ValueError,KeyError,TypeError) as e:
            errors.append(f'{ticker}: {e}')
            if ticker in prior and prior[ticker].get('facts'):
                record=prior[ticker].copy()
                record['observation_status']='stale-previous-snapshot'
                record['refresh_error']=str(e)
            else:
                record['observation_status']='missing'
                record['refresh_error']=str(e)
        final.append(record)
    if successes==0:
        raise SECError('Zero current facts retrieved; refusing to overwrite published dataset. '+('; '.join(errors))[:600])
    payload={
        'schema_version':'0.1.0',
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'last_successful_refresh':datetime.now(timezone.utc).isoformat(),
        'status':'Experimental filing-based observation panel; not validated predictive results',
        'universe_description':'Curated current pilot group, not point-in-time Russell index constituents',
        'asof_cutoff':asof.isoformat(),
        'companies':final,
        'refresh_warnings':errors,
    }
    # Atomic replacement; repeated requests only commit if data genuinely change.
    temp=OUTPUT.with_suffix('.tmp')
    temp.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    temp.replace(OUTPUT)
    if archive:
        snaps=ROOT/'data'/'snapshots'
        snaps.mkdir(parents=True,exist_ok=True)
        (snaps/(asof.isoformat()+'.json')).write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    return {'companies':len(final),'fresh':successes,'warnings':len(errors),'cutoff':asof.isoformat()}

def validate() -> dict:
    d=json.loads(OUTPUT.read_text())
    assert d['schema_version']=='0.1.0'
    assert isinstance(d['companies'],list) and len(d['companies'])>=1
    tickers=[r['ticker'] for r in d['companies']]
    assert len(tickers)==len(set(tickers)), 'Duplicate symbols in observation panel'
    for r in d['companies']:
        assert isinstance(r.get('facts'),dict),f"Missing facts object: {r['ticker']}"
        for fact in r['facts'].values():
            assert fact['source']=='SEC CompanyFacts US-GAAP'
            assert fact['unit']=='USD' and fact['form']=='10-K'
            assert fact['filed']<=d['asof_cutoff']
            assert fact['end']==r['fiscal_end']
    return {'validated_rows':len(tickers)}

def main():
    p=argparse.ArgumentParser(description='forma. research engine')
    p.add_argument('command',choices=['refresh','validate'])
    p.add_argument('--asof',help='Information date cutoff YYYY-MM-DD (not a PIT database reconstruction)')
    p.add_argument('--archive',action='store_true',help='Write immutable dated input/output snapshot for audit')
    args=p.parse_args()
    try:
        if args.command=='refresh':
            result=refresh(date.fromisoformat(args.asof) if args.asof else datetime.now(timezone.utc).date(),args.archive)
            validate()
        else:
            result=validate()
    except (ValueError,SECError,AssertionError,KeyError,OSError) as e:
        print(f'ERROR: {e}',file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()

"""Coverage safety and financial-input provenance regressions"""
import csv
import gzip
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock
from engine.universe import parse_holdings, refresh_universe, verify_universe
from engine.macro import parse_macro, refresh_macro, verify_macro
from engine.earnings import earnings_evidence
from engine.net import download
from engine.__main__ import sync_universe
from test_research import sample_facts

TODAY = date(2026, 10, 17)


def holdings(stamp='Oct 15, 2026', count=1600):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['iShares Russell 2000 ETF'])
    writer.writerow(['Fund Holdings as of', stamp])
    writer.writerow(['Ticker', 'Name', 'Sector', 'Asset Class', 'Weight (%)', 'Price', 'Exchange'])
    for i in range(count):
        writer.writerow([f'T{i}', f'Fixture {i}', 'Industrials', 'Equity', 100 / count, 20, 'NYSE'])
    writer.writerow(['-', 'Residual security', 'Industrials', 'Equity', 0, 0, 'NO MARKET (E.G. UNLISTED)'])
    writer.writerow(['USD', 'Cash', 'Cash', 'Cash', 0, 1, '-'])
    return stream.getvalue().encode()


class UniverseSafety(unittest.TestCase):
    def test_full_list_excludes_non_tradable_positions_but_records_them(self):
        parsed = parse_holdings(holdings(), TODAY)
        self.assertEqual(len(parsed['companies']), 1600)
        self.assertEqual(len(parsed['excluded_holdings']), 2)
        self.assertEqual(parsed['source_kind'], 'iwm-holdings-proxy')

    def test_incomplete_and_outdated_and_future_sources_are_rejected(self):
        for raw in [holdings(count=20), holdings('Oct 01, 2026'), holdings('Oct 18, 2026')]:
            with self.assertRaises(ValueError):
                parse_holdings(raw, TODAY)

    def test_ambiguous_tickers_rejected(self):
        raw = holdings().replace(b'T1,Fixture', b'T0,Fixture', 1)
        with self.assertRaises(ValueError):
            parse_holdings(raw, TODAY)

    def test_failed_update_preserves_universe_and_tampered_archive_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refresh_universe(root, TODAY, holdings())
            path = root / 'data/universe.json'
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                refresh_universe(root, TODAY, holdings(count=10))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(verify_universe(root)['verified_equities'], 1600)
            data = json.loads(path.read_text())
            (root / data['source_document']['raw_path']).write_bytes(gzip.compress(b'changed'))
            with self.assertRaises(ValueError):
                verify_universe(root)

    def test_membership_history_keeps_exits_and_does_not_backdate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refresh_universe(root, TODAY, holdings('Oct 14, 2026'))
            changed = holdings().replace(b'T0,Fixture 0', b'NEW,Fixture 0')
            refresh_universe(root, TODAY, changed)
            data = json.loads((root / 'data/universe.json').read_text())
            self.assertEqual(data['changes']['added'], ['NEW'])
            self.assertEqual(data['changes']['removed'], ['T0'])
            self.assertEqual(len(list((root / 'data/membership').glob('*.json'))), 2)
            with self.assertRaises(ValueError):
                refresh_universe(root, TODAY, holdings('Oct 14, 2026'))


class MacroSafety(unittest.TestCase):
    def raw(self):
        return b'observation_date,DFF,DGS10,T10Y2Y,UNRATE,CPIAUCSL\n2025-09-01,4,4,0,4,100\n2026-07-01,4,4,0,4,102\n2026-09-01,3,4,1,4.5,103\n2026-10-16,3,4,1,,,\n2026-11-01,99,99,99,99,999\n'

    def test_future_observations_are_not_used_and_yoy_inflation_is_correct(self):
        parsed = parse_macro(self.raw(), TODAY)
        lookup = {r['series']: r for r in parsed['series']}
        self.assertEqual(lookup['DFF']['value'], 3)
        self.assertAlmostEqual(lookup['CPIAUCSL']['value'], 3)
        self.assertEqual(lookup['UNRATE']['date'], '2026-09-01')
        self.assertIn('not release dates', parsed['note'])

    def test_missing_source_does_not_overwrite_and_archive_reproduces(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refresh_macro(root, TODAY, self.raw())
            path = root / 'site/data/macro.json'
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                refresh_macro(root, TODAY, b'observation_date,DFF\n2026-10-16,3\n')
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(verify_macro(root)['verified_macro_series'], 5)


class EarningsSafety(unittest.TestCase):
    def test_eps_uses_reported_diluted_unit_and_never_invents_a_forecast(self):
        full = sample_facts()
        obs = full['facts']['us-gaap']['Revenues']['units']['USD'][0]
        full['facts']['us-gaap']['EarningsPerShareDiluted'] = {'units': {'USD/shares': [{**obs, 'val': 2.5}]}}
        evidence = earnings_evidence(full, TODAY)
        self.assertEqual(evidence['annual_history'][0]['eps']['value'], 2.5)
        self.assertEqual(evidence['annual_history'][0]['eps']['unit'], 'USD/shares')
        self.assertIsNone(evidence['forecast_eps'])
        full['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['accn'] = '0001111111-26-000099'
        self.assertIsNone(earnings_evidence(full, TODAY)['annual_history'][0]['eps'])


class PublicSourceRetries(unittest.TestCase):
    @patch('engine.net.time.sleep')
    @patch('engine.net.urllib.request.urlopen')
    def test_transient_read_timeout_retries_without_publishing_partial_bytes(self, opened, sleep):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'complete response'
        opened.side_effect = [TimeoutError('synthetic timeout'), response]
        self.assertEqual(download('https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/latest-holdings.csv'), b'complete response')
        self.assertEqual([call.kwargs['timeout'] for call in opened.call_args_list], [30, 60])
        sleep.assert_called_once_with(2)

    @patch('engine.net.urllib.request.urlopen')
    def test_access_denials_are_not_retried(self, opened):
        import urllib.error
        opened.side_effect = urllib.error.HTTPError('https://www.ishares.com/', 403, 'denied', {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            download('https://www.ishares.com/')
        self.assertEqual(opened.call_count, 1)

    def test_unexpected_provider_rejected(self):
        with self.assertRaises(ValueError):
            download('https://example.org/untrusted.csv')

    @patch('engine.net.shutil.which', return_value='/usr/bin/curl')
    @patch('engine.net.subprocess.run')
    def test_fred_uses_complete_system_https_response(self, run, which):
        run.return_value.stdout = b'observation_date,DFF\n2026-10-16,3.88\n'
        self.assertIn(b'DFF', download('https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF'))
        command = run.call_args.args[0]
        self.assertIn('--fail', command)
        self.assertIn('--proto', command)
        self.assertNotIn('--insecure', command)
        self.assertEqual(run.call_args.kwargs['timeout'], 160)

    @patch('engine.net.shutil.which', return_value='/usr/bin/curl')
    @patch('engine.net.subprocess.run')
    def test_fred_failure_never_returns_partial_response(self, run, which):
        import subprocess
        run.side_effect = subprocess.CalledProcessError(28, ['curl'], output=b'partial')
        with self.assertRaises(OSError):
            download('https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF')

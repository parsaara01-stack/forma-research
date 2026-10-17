"""Regression tests for publication integrity, SEC failures and accounting context."""
import copy
import gzip
import io
import json
import tempfile
import unittest
import urllib.error
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from engine.sec import SECClient, SECError, TAGS, extract_annual, choose_fact, SEC_FACTS, SEC_TICKERS
from engine.metrics import calculate, capital_profile
import engine.__main__ as cli
from test_research import sample_facts

ASOF = date(2026, 10, 17)


class ExtractionIntegrity(unittest.TestCase):
    def test_no_mixed_accession_fallback(self):
        d = sample_facts()
        for o in d['facts']['us-gaap']['Revenues']['units']['USD']:
            o['accn'] = '0001111111-26-000099'
        _, facts = extract_annual(d, ASOF)
        self.assertNotIn('revenue', facts)

    def test_no_mixed_duration(self):
        d = sample_facts()
        for o in d['facts']['us-gaap']['Revenues']['units']['USD']:
            o['start'] = '2024-12-01'
        _, facts = extract_annual(d, ASOF)
        self.assertNotIn('revenue', facts)

    def test_nonfinite_and_boolean_rejected(self):
        for bad in [float('inf'), float('nan'), True]:
            d = sample_facts()
            d['facts']['us-gaap']['Revenues']['units']['USD'] = [
                {**d['facts']['us-gaap']['Revenues']['units']['USD'][0], 'val': bad}]
            self.assertIsNone(choose_fact(d, ['Revenues'], '2025-12-31', ASOF))

    def test_conflicting_context_rejected(self):
        d = sample_facts()
        rows = d['facts']['us-gaap']['Revenues']['units']['USD']
        rows.append({**rows[0], 'val': 700})
        self.assertIsNone(choose_fact(d, ['Revenues'], '2025-12-31', ASOF))

    def test_ambiguous_debt_totals_not_added(self):
        self.assertNotIn('LongTermDebt', TAGS['long_term_debt'])
        self.assertNotIn('LongTermDebtAndCapitalLeaseObligations', TAGS['long_term_debt'])
        self.assertIsNone(calculate({'long_term_debt': {'value': 30}, 'current_debt': {'value': 5}})['total_debt'])

    def test_first_maturity_bucket_uses_actual_taxonomy_tag(self):
        self.assertEqual(TAGS['maturity_year_1'], ['LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths'])

    def test_diluted_shares_correct_unit(self):
        d = sample_facts()
        o = {**d['facts']['us-gaap']['Revenues']['units']['USD'][0], 'val': 500}
        d['facts']['us-gaap']['WeightedAverageNumberOfDilutedSharesOutstanding'] = {'units': {'shares': [o]}}
        _, facts = extract_annual(d, ASOF)
        self.assertEqual(facts['diluted_shares']['unit'], 'shares')

    def test_bank_ratios_suppressed(self):
        self.assertTrue(all(v is None for v in calculate({'cash': {'value': 100}}, 'Banking').values()))

    def test_thereafter_alone_marks_partial_schedule(self):
        self.assertEqual(capital_profile({'maturity_thereafter': {'value': 40}})['maturities']['status'], 'tagged-partial-needs-note-review')


class ClientIntegrity(unittest.TestCase):
    def response(self, raw):
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = raw
        return cm

    @patch('engine.sec.time.sleep')
    @patch('engine.sec.urllib.request.urlopen')
    def test_retry_after_and_archived_bytes(self, open_url, sleep):
        raw = b'{"cik":1111111,"facts":{}}'
        open_url.side_effect = [urllib.error.HTTPError(SEC_TICKERS, 429, 'limited', {'Retry-After': '2'}, None), self.response(raw)]
        with tempfile.TemporaryDirectory() as tmp:
            client = SECClient('research@example.org', cache_dir=Path(tmp)/'cache', archive_dir=Path(tmp)/'raw')
            client.get_json(SEC_TICKERS)
            self.assertEqual(open_url.call_count, 2)
            self.assertTrue(any(c.args == (2,) for c in sleep.call_args_list))
            archived = next((Path(tmp)/'raw').glob('*.gz'))
            self.assertEqual(gzip.decompress(archived.read_bytes()), raw)
            client.get_json(SEC_TICKERS)
            self.assertEqual(open_url.call_count, 2)

    @patch('engine.sec.urllib.request.urlopen')
    def test_403_not_retried(self, open_url):
        open_url.side_effect = urllib.error.HTTPError(SEC_TICKERS, 403, 'blocked', {}, None)
        with self.assertRaises(SECError):
            SECClient('research@example.org').get_json(SEC_TICKERS)
        self.assertEqual(open_url.call_count, 1)

    @patch('engine.sec.urllib.request.urlopen')
    def test_cik_mismatch(self, open_url):
        open_url.return_value = self.response(b'{"cik":2222222,"facts":{}}')
        with self.assertRaises(SECError):
            SECClient('research@example.org').company_facts(1111111)

    @patch('engine.sec.urllib.request.urlopen')
    def test_invalid_json_not_cached(self, open_url):
        open_url.return_value = self.response(b'{"x": NaN}')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SECError):
                SECClient('research@example.org', cache_dir=Path(tmp)).get_json(SEC_TICKERS)
            self.assertEqual(list(Path(tmp).iterdir()), [])


class PublicationIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'site/data').mkdir(parents=True)
        (self.root/'data').mkdir()
        self.output = self.root/'site/data/research.json'
        self.universe = self.root/'data/universe.json'
        self.universe.write_text(json.dumps({'companies': [{'ticker': 'TEST', 'name': 'Synthetic fixture', 'group': 'Software'}]}))
        self.original = {'schema_version': '0.1.0', 'companies': [{'ticker': 'TEST', 'facts': {}, 'metrics': {}}]}
        self.output.write_text(json.dumps(self.original))
        self.patches = [patch.object(cli, 'ROOT', self.root), patch.object(cli, 'OUTPUT', self.output), patch.object(cli, 'UNIVERSE', self.universe)]
        for p in self.patches:
            p.start()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def client(self):
        client = MagicMock()
        client.resolve_tickers.return_value = {'TEST': {'cik_str': 1111111}}
        client.company_facts.return_value = sample_facts()
        client.documents = {SEC_FACTS.format(cik=1111111): {'url': SEC_FACTS.format(cik=1111111), 'sha256': 'a'*64, 'retrieved_at': '2026-10-17T00:00:00+00:00'}}
        return client

    def test_zero_success_preserves_dataset_bytes(self):
        before = self.output.read_bytes()
        client = self.client()
        client.company_facts.side_effect = SECError('Synthetic network failure')
        with patch.object(cli, 'SECClient', return_value=client), self.assertRaises(SECError):
            cli.refresh(ASOF)
        self.assertEqual(self.output.read_bytes(), before)

    def test_validation_failure_preserves_dataset_bytes(self):
        before = self.output.read_bytes()
        with patch.object(cli, 'SECClient', return_value=self.client()), patch.object(cli, 'validate_payload', side_effect=ValueError('invalid')):
            with self.assertRaises(ValueError):
                cli.refresh(ASOF)
        self.assertEqual(self.output.read_bytes(), before)

    def test_identical_refresh_no_rewrite_and_immutable_snapshot(self):
        with patch.object(cli, 'SECClient', return_value=self.client()):
            self.assertTrue(cli.refresh(ASOF, archive=True)['changed'])
            before = self.output.read_bytes()
            self.assertFalse(cli.refresh(ASOF, archive=True)['changed'])
            self.assertEqual(before, self.output.read_bytes())
            self.assertEqual(len(list((self.root/'data/snapshots').glob('*.json'))), 1)

    def test_future_stale_facts_never_carried_back(self):
        record = {'facts': {'revenue': {'filed': '2026-02-10', 'end': '2025-12-31'}}}
        self.assertFalse(cli._safe_prior(record, date(2026, 1, 1)))
        self.assertTrue(cli._safe_prior(record, ASOF))

    def test_future_observation_cutoff_is_not_reused(self):
        record = {'observation_cutoff': '2026-10-17', 'facts': {'revenue': {'filed': '2026-02-10', 'end': '2025-12-31'}}}
        self.assertFalse(cli._safe_prior(record, date(2026, 3, 1)))

    def test_future_cutoff_rejected(self):
        with self.assertRaises(ValueError):
            cli.refresh(date(2999, 1, 1))

    def test_tampered_metric_rejected(self):
        with patch.object(cli, 'SECClient', return_value=self.client()):
            cli.refresh(ASOF)
        payload = json.loads(self.output.read_text())
        payload['companies'][0]['metrics']['free_cash_flow'] = 123456
        with self.assertRaises(ValueError):
            cli.validate_payload(payload)

    def test_stale_and_missing_partial_failures(self):
        with patch.object(cli, 'SECClient', return_value=self.client()):
            cli.refresh(ASOF)
        self.universe.write_text(json.dumps({'companies': [{'ticker': t} for t in ['TEST', 'FRESH', 'MISSING']]}))
        client = self.client()
        client.resolve_tickers.return_value['FRESH'] = {'cik_str': 1111111}
        client.company_facts.side_effect = [SECError('Synthetic transient failure'), sample_facts()]
        with patch.object(cli, 'SECClient', return_value=client):
            result = cli.refresh(ASOF)
        self.assertEqual(result['warnings'], 2)
        self.assertEqual([r['observation_status'] for r in json.loads(self.output.read_text())['companies']],
                         ['stale-previous-snapshot', 'sec-xbrl-unreviewed', 'missing'])


if __name__ == '__main__':
    unittest.main()

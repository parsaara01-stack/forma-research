import json
import unittest
from datetime import date
from pathlib import Path
from engine.sec import choose_fact,extract_annual,find_anchor,SECClient
from engine.metrics import calculate,safe_ratio
ROOT=Path(__file__).resolve().parents[1]

def sample_facts():
    def flow(val,tag,year,filed,accn):
        return {'start':f'{year}-01-01','end':f'{year}-12-31','val':val,'form':'10-K','fp':'FY','fy':year,'filed':filed,'accn':accn}
    def stock(val,year,filed,accn):
        return {'end':f'{year}-12-31','val':val,'form':'10-K','fp':'FY','fy':year,'filed':filed,'accn':accn}
    accn='0001111111-26-000001'
    gaap={
      'Assets':{'units':{'USD':[stock(500,2025,'2026-02-10',accn)]}},
      'Revenues':{'units':{'USD':[flow(200, 'Revenues',2025,'2026-02-10',accn),flow(220,'Revenues',2025,'2026-03-10','0001111111-26-000002'),flow(999,'Revenues',2025,'2027-01-10','0001111111-27-000001')]}},
      'NetIncomeLoss':{'units':{'USD':[flow(20,'NetIncomeLoss',2025,'2026-02-10',accn)]}},
      'OperatingIncomeLoss':{'units':{'USD':[flow(40,'OperatingIncomeLoss',2025,'2026-02-10',accn)]}},
      'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':[flow(35,'NetCashProvidedByUsedInOperatingActivities',2025,'2026-02-10',accn)]}},
      'PaymentsToAcquirePropertyPlantAndEquipment':{'units':{'USD':[flow(15,'PaymentsToAcquirePropertyPlantAndEquipment',2025,'2026-02-10',accn)]}},
      'LongTermDebtNoncurrent':{'units':{'USD':[stock(50,2025,'2026-02-10',accn)]}},
      'LongTermDebtCurrent':{'units':{'USD':[stock(10,2025,'2026-02-10',accn)]}},
    }
    return {'cik':1111111,'facts':{'us-gaap':gaap}}

class TestSEC(unittest.TestCase):
    def test_no_asof_leakage(self):
        data=sample_facts(); end,facts=extract_annual(data,date(2026,2,8))
        self.assertIsNone(end);self.assertEqual(facts,{})
    def test_first_filing_preferred(self):
        data=sample_facts();end,facts=extract_annual(data,date(2026,12,31))
        self.assertEqual(end,'2025-12-31')
        self.assertEqual(facts['revenue']['value'],200)
        self.assertEqual(facts['revenue']['filed'],'2026-02-10')
        self.assertIn('000111111126000001',facts['revenue']['source_url'])
    def test_future_restatement_rejected(self):
        x=sample_facts();v=choose_fact(x,['Revenues'],'2025-12-31',date(2026,3,1))
        self.assertEqual(v['value'],200)
    def test_quarterly_not_annual(self):
        x=sample_facts(); x['facts']['us-gaap']['Revenues']['units']['USD'].append({'start':'2026-01-01','end':'2026-03-31','val':50,'form':'10-Q','fp':'Q1','filed':'2026-05-01'})
        self.assertEqual(find_anchor(x,date(2026,9,1)),'2025-12-31')
    def test_contact_required(self):
        with self.assertRaises(ValueError):SECClient('')

class TestMetrics(unittest.TestCase):
    def f(self,value):return {'value':value}
    def test_reinvestment_and_coverage(self):
        facts={name:self.f(v) for name,v in {
            'revenue':200,'operating_income':40,'operating_cash_flow':35,'capex':15,
            'total_assets':500,'long_term_debt':50,'current_debt':10,'short_term_borrowings':0,'interest_expense':5,'net_income':20,
        }.items()}
        m=calculate(facts)
        self.assertAlmostEqual(m['operating_margin'],.2)
        self.assertAlmostEqual(m['free_cash_flow'],20)
        self.assertAlmostEqual(m['capex_intensity'],.075)
        self.assertAlmostEqual(m['debt_to_assets'],.12)
        self.assertAlmostEqual(m['interest_coverage'],8)
    def test_missing_is_not_zero(self):
        m=calculate({'revenue':self.f(100),'operating_cash_flow':self.f(12),'long_term_debt':self.f(30),'total_assets':self.f(100)})
        self.assertIsNone(m['free_cash_flow'])
        self.assertIsNone(m['debt_to_assets'])
        self.assertIsNone(m['interest_coverage'])
    def test_banking_sector_no_industrial_ratios(self):
        m=calculate({'revenue':self.f(100),'operating_income':self.f(10)},'Banking')
        self.assertIsNone(m['operating_margin'])
    def test_negative_profit_no_cash_conversion_ratio(self):
        self.assertIsNone(calculate({'net_income':self.f(-3),'operating_cash_flow':self.f(15)})['cfo_to_positive_net_income'])
    def test_safe_ratio(self):
        self.assertIsNone(safe_ratio(3,0))
        self.assertIsNone(safe_ratio(4,-2))

class TestProject(unittest.TestCase):
    def test_published_dataset(self):
        d=json.loads((ROOT/'site/data/research.json').read_text())
        self.assertIn(d['schema_version'],{'0.1.0','0.2.0','0.3.0'})
        self.assertGreater(len(d['companies']),0)
    def test_unique_universe(self):
        d=json.loads((ROOT/'data/universe.json').read_text())
        names=[x['ticker'] for x in d['companies']]
        self.assertEqual(len(names),len(set(names)))
    def test_site_assets_exist(self):
        for asset in ['site/index.html','site/favicon.svg','site/assets/styles.css','site/assets/app.js']:
            self.assertTrue((ROOT/asset).exists())

if __name__=='__main__': unittest.main()

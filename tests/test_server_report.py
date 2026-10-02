import copy
import json
from pathlib import Path
import unittest
from src.server_report import calculate

class ReportTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(Path('config.example.json').read_text())
        self.data={'sales':{'Server A':{'net_sales':1000,'covers':50,'discount':20},'Server B':{'net_sales':3000,'covers':100,'discount':30}},'beverage':{'Server A':{'beverage_sales':190,'net_sales':1000},'Server B':{'beverage_sales':600,'net_sales':3000}},'turns':{'Server A':{'avg_minutes':40,'checks':25},'Server B':{'avg_minutes':45,'checks':50}}}
    def test_weighted_ppa_and_score(self):
        r=calculate(self.config,self.data)
        self.assertAlmostEqual(r['ppa_target'],4000/150)
        a=next(x for x in r['employees'] if x['employee']=='Server A')
        self.assertAlmostEqual(a['score'],96.25)
    def test_exclusion_changes_reference(self):
        self.config['excluded'].append('Server B')
        r=calculate(self.config,self.data)
        self.assertEqual(r['ppa_target'],20)
        self.assertEqual(len(r['employees']),1)
    def test_exact_time_boundary_blocks_top_tiers(self):
        self.data['turns']['Server B']['avg_minutes']=46
        r=calculate(self.config,self.data)
        b=next(x for x in r['employees'] if x['employee']=='Server B')
        self.assertEqual(b['components']['minutes'],100)
        self.assertEqual(b['tier'],3)
    def test_missing_report_rejected(self):
        del self.data['turns']['Server A']
        with self.assertRaises(ValueError):calculate(self.config,self.data)
    def test_zero_denominator_rejected(self):
        self.data['sales']['Server A']['covers']=0
        with self.assertRaises(ValueError):calculate(self.config,self.data)

if __name__=='__main__':unittest.main()

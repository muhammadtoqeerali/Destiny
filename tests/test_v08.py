import unittest
import pandas as pd
import numpy as np
from ml.nhanes_quality import PHQ_ITEMS, phq_diagnostics
from ml.nhanes_cohort_profile import build_profile
from ml.nhanes_survival import kaplan_meier
from ml.nhats_contract import validate_rounds

class TestV08(unittest.TestCase):
    def test_phq_matches_raw(self):
        raw=pd.DataFrame({'SEQN':[1,2,3],**{key:[0,1,7 if key==PHQ_ITEMS[-1] else 0] for key in PHQ_ITEMS}})
        proc=pd.DataFrame({'SEQN':[1,2,3],'phq9_score':[0,9,np.nan]})
        got=phq_diagnostics(raw,proc)
        self.assertEqual(got['mismatch_count'],0)
        self.assertEqual(got['raw_nine_complete'],2)
    def test_phq_detects_wrong_processing(self):
        raw=pd.DataFrame({'SEQN':[1,2],**{key:[1,2] for key in PHQ_ITEMS}})
        proc=pd.DataFrame({'SEQN':[1,2],'phq9_score':[9,7]})
        with self.assertRaisesRegex(ValueError,'mismatch'):phq_diagnostics(raw,proc)
    def test_survival_censoring(self):
        got=kaplan_meier([10,14,30,40],[1,0,1,0],(12,24,36))
        self.assertAlmostEqual(got[0]['survival'],.75)
        self.assertAlmostEqual(got[1]['survival'],.75)
        self.assertAlmostEqual(got[2]['survival'],.375)
    def test_small_cells_not_released(self):
        rng=np.random.default_rng(42)
        n=1200
        d=pd.DataFrame({'SEQN':range(n),'cycle':['2011-2012']*n,'data_origin':['NHANES_PUBLIC_2019_LMF']*n,
             'survey_weight':np.ones(n),'age':[70]*n,'sex':['Female']*n,'bmi':[26]*n})
        for k in ['heart_failure','coronary_disease','stroke','cancer','diabetes','hypertension','ever_smoked']:
            d[k]=[1]*8+[0]*(n-8) if k=='heart_failure' else [1]*240+[0]*(n-240)
        for k in ['walking_difficulty','stairs_difficulty','stooping_difficulty']:d[k]=[1]*700+[2]*500
        result=build_profile(d)
        all_group=result['groups'][0]
        self.assertNotIn('Heart failure',[x['label'] for x in all_group['conditions']])
        self.assertEqual(all_group['n'],1200)
    def test_nhats_refuses_unconfirmed(self):
        with self.assertRaises(ValueError):validate_rounds([],{})
    def test_nhats_schema_only(self):
        f1=pd.DataFrame({'pid':[1,2,3],'x':[1,2,3]})
        f2=pd.DataFrame({'pid':[2,3,4],'x':[2,2,2]})
        c={'participant_key':'pid','waves':['A','B'],'variables':{'mobility':'x'},'outcome_definition_verified':True}
        r=validate_rounds([f1,f2],c)
        self.assertEqual(r['overlap_n'],2)
        self.assertEqual(r['status'],'SCHEMA_CHECK_ONLY_NO_MODEL_TRAINING')

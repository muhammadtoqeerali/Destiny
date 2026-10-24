"""Interview-only synthetic data, separated datasets and front end. No private data access."""
from pathlib import Path
import json
import numpy as np
from ml.interview_benchmark_v47 import (FEATURES,NAMES,OUTPUT,generated,split,pipeline,models,
     metrics,report,serialized,check_fixture)

ROOT=Path(__file__).resolve().parents[1]
def src(p):return (ROOT/p).read_text(encoding='utf8')

def test_synthetic_replay_is_exact_and_contains_no_real_data():
    a=report();b=report()
    assert a==b
    check_fixture(json.loads(src(OUTPUT)),a)
    assert a['clinical_prediction'] is False
    assert a['person_level_real_data_used'] is False
    assert a['source']=='GENERATED_FICTIONAL_AGEING_COHORT_NOT_HUNT_NHATS_OR_NHANES'
    assert a['configuration']['generation_n']==1800
    assert [m['name'] for m in a['models']]==NAMES
    assert len(a['fictional_examples'])==8
    assert all(len(x['illustrative_factors'])==4 for x in a['fictional_examples'])
    assert all(x['id'].startswith('FICTIONAL-') and 0<=x['fictional_model_probability']<=1
               and type(x['current_conditions']) is list for x in a['fictional_examples'])

def test_training_validation_testing_have_no_group_overlap():
    df=generated();tr,va,te=split(df)
    ids=[set(df['fictional_id'].iloc[ix]) for ix in (tr,va,te)]
    assert all(not ids[i].intersection(ids[j]) for i in range(3) for j in range(i+1,3))
    assert [len(x) for x in (tr,va,te)]==[1080,360,360]
    assert 'future_adl_decline_demo' not in FEATURES and 'fictional_id' not in FEATURES

def test_models_are_fitted_on_training_subset_only():
    df=generated();tr,va,te=split(df)
    learner=pipeline(models()[1]); y=df['future_adl_decline_demo'].to_numpy()
    learner.fit(df.iloc[tr][FEATURES],y[tr]);p=learner.predict_proba(df.iloc[va][FEATURES])[:,1]
    assert p.shape==(360,) and np.all(np.isfinite(p))
    scores=metrics(y[va],p)
    assert 0<=scores['brier']<=1
    assert 'transform' in learner.named_steps and 'model' in learner.named_steps
    assert len(te)==360

def test_selects_only_on_validation_not_test():
    d=report()
    selected=min(d['models'],key=lambda m:(m['validation']['brier'],NAMES.index(m['name'])))
    assert d['selected_model']==selected['name']
    assert d['selected_validation']==selected['validation']
    assert d['synthetic_test']!=d['selected_validation']
    assert sum(b['count'] for b in d['calibration'])==d['configuration']['test_n']

# The former web-source assertions for the Interview presentation were retired with that UI.
# Equivalent (and stricter) checks live in tests/test_frailtyscope_redesign.py.

def test_no_real_person_records_or_data_files_in_package():
    body=src(OUTPUT)
    for token in ('patient_id','SEQN','date_of_birth','HUNT_RESTRICTED_RECORD',
                  'clinical_prediction": true','person_level_real_data_used": true'):
        assert token not in body
    assert not (ROOT/'web/public/data/interview-patient-records.json').exists()

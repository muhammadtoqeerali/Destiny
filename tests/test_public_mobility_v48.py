"""Only generated source-coded synthetic test tables; NEVER load NHANES participant data."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pytest
from ml.public_mobility_v48 import (CASE_ID,INPUTS,TABLES,ContractError,check,
                                    harmonize,train,metric,safe_root,candidates)

ROOT=Path(__file__).resolve().parents[1]

def fake_raw(n=300,seed=8):
    rng=np.random.default_rng(seed)
    age=rng.integers(64,81,n)
    bmi=rng.normal(28,6,n)
    diabetes=rng.choice([1,2,3,7],n,p=[.21,.70,.05,.04])
    arthritis=rng.choice([1,2,7],n,p=[.45,.52,.03])
    mobility_prob=1/(1+np.exp(-(-1+0.14*(age-70)+0.7*(arthritis==1)+0.03*(bmi-26))))
    label=rng.binomial(1,mobility_prob,n)
    ans=np.where(label==1,rng.choice([2,3,4],n),1).astype(float)
    ans[:8]=[5,7,9,np.nan,1,2,3,4]
    aids=np.full(n,2.0);aids[4]=1
    x={'SEQN':np.arange(n)+1000000,'RIDAGEYR':age,'RIAGENDR':rng.choice([1,2],n),
       'SDMVPSU':rng.integers(1,3,n),'SDMVSTRA':rng.integers(1,20,n),
       'WTMEC2YR':rng.uniform(100,1000,n),'PFQ054':aids,'PFQ061B':ans,
       'BMXBMI':bmi,'MCQ160A':arthritis,'MCQ160B':rng.choice([1,2],n,p=[.1,.9]),
       'MCQ160F':rng.choice([1,2],n,p=[.08,.92]), 'DIQ010':diabetes}
    for k in TABLES['DPQ'][1:]:x[k]=rng.choice([0,1,2,3,7],n,p=[.6,.2,.12,.07,.01])
    return pd.DataFrame(x)

def test_real_questionnaire_semantics_and_routing():
    x,r=harmonize(fake_raw(),'2015-2016')
    assert r['excluded_PFQ054_uses_walking_aid']==1
    assert r['eligible_age_65_plus']<300
    assert r['questionnaire_respondents']<r['eligible_age_65_plus']
    assert x.target.nunique()==2 and x['target'].between(0,1).all()
    assert 1000004 not in set(x['id'])  # equipment skip
    assert 1000000 not in set(x['id'])  # does not do activity != 'no difficulty'
    assert 1000001 not in set(x['id'])  # refused excluded
    assert 1000002 not in set(x['id'])  # don't know excluded
    assert 'PFQ061B' not in INPUTS and 'PFQ054' not in INPUTS
    assert x['diabetes'].isna().any()  # borderline not diagnosed
    assert r['sample_age_80_is_topcoded'] is True

def test_phq_requires_all_nine_valid_items():
    frame=fake_raw(120)
    frame.loc[20,'DPQ010']=7
    out,_=harmonize(frame,'2015-2016')
    assert pd.isna(out.loc[out['id']==1000020,'phq9_score']).all()
    frame.loc[20,'DPQ010']=2
    for col in TABLES['DPQ'][1:]:frame.loc[20,col]=2
    out,_=harmonize(frame,'2015-2016')
    assert float(out.loc[out['id']==1000020,'phq9_score'].iloc[0])==18

def test_pipeline_runs_with_no_person_overlap_and_no_clinical_claim():
    earlier,_=harmonize(fake_raw(200,seed=2),'2015-2016')
    later,_=harmonize(fake_raw(160,seed=9).assign(SEQN=lambda d:d.SEQN+2000000),'2017-2018')
    res=train(earlier,later,fast=True)
    assert res['selected_model'] in candidates()
    assert res['selection_rule'].startswith('LOWEST_VALIDATION_BRIER')
    assert res['split']['later_cycle_test_n']==len(later)
    assert res['do_not_interpret_as_future_frailty_or_clinical_prediction'] is True
    assert set(res['validation_permutation_importance_delta_brier'][0])=={'feature','brier_increase','std'}
    assert len(res['model_comparison_development_only'])==3
    assert all('test' not in row for row in res['model_comparison_development_only'])

def test_overlap_and_malformed_predictions_fail_closed():
    a,_=harmonize(fake_raw(200,seed=1),'2015-2016')
    b,_=harmonize(fake_raw(160,seed=5),'2017-2018')
    with pytest.raises(ContractError,match='leakage'):train(a,b,fast=True)
    with pytest.raises(ContractError):metric(np.array([0,1]*11),np.array([.5]*21+[float('nan')]))

def test_outside_repo_only_and_no_safe_output_patient_fields():
    with pytest.raises(ContractError,match='OUTSIDE'):safe_root(ROOT/'data/secret',ROOT)
    source=(ROOT/'ml/public_mobility_v48.py').read_text()
    for forbidden in ('nhanes_mortality_v10/integrity','joblib.load(','pickle.load(','read_csv("data/processed',
                      "['PFQ061C','PFQ061D']",'clinical_prediction_permitted\':True'):
        assert forbidden not in source
    assert 'clinical_prediction_permitted' in source

def test_legacy_chains_and_ci():
    ci=(ROOT/'.github/workflows/ci.yml').read_text()
    assert 'tests/test_public_mobility_v48.py' in ci
    assert 'python -m ml.public_mobility_v48 --contract' in ci
    assert 'tests/test_interview_focus_v47.py' in ci
    assert 'tests/test_study_activation_v46.py' in ci
    from scripts.patch_interview_focus_v47 import PATCHES
    for rel,pairs in PATCHES.items():
        body=(ROOT/rel).read_text()
        for old,new in pairs: assert new in body,(rel,new)


def test_optional_boosting_adapters_respect_classifier_tags():
    from sklearn.base import is_classifier
    reg=candidates()
    for name,(pipe,params) in reg.items():
        assert is_classifier(pipe),name
        assert not any('target' in key or 'PFQ' in key for key in params)


def test_aggregate_report_contains_no_real_or_fictional_person_ids(monkeypatch,tmp_path):
    from ml import public_mobility_v48 as module
    earlier=fake_raw(210,seed=3)
    later=fake_raw(150,seed=9).assign(SEQN=lambda d:d.SEQN+2000000)
    def fake_read(_root,cycle):
        return (earlier if cycle=='2015-2016' else later),{'FAKE_SYNTHETIC_TABLE.XPT':'generated_fixture_only'}
    monkeypatch.setattr(module,'read_cycle',fake_read)
    root=tmp_path/'separate_public_study'
    (root/'results').mkdir(parents=True)
    output=module.run(root,fast=True)
    assert output['clinical_prediction_permitted'] is False
    assert output['case_id']==CASE_ID
    raw=(root/'results'/'mobility_aggregate_v48.json').read_text()
    report=(root/'results'/'mobility_report_v48.md').read_text()
    assert output['experiment']['selected_model'] in module.candidates()
    assert '1000000' not in raw and '1000000' not in report
    assert '"id":' not in raw and 'SEQN' not in raw
    assert 'NOT future' in report or 'NOT future risk' in report


def test_ci_patcher_rejects_repeat_without_changing_old_contracts():
    from scripts.patch_public_mobility_v48 import transform, ANCHOR, INSERT
    baseline='name: safe\n'+ANCHOR+'        run: previous\n'
    patched=transform(baseline)
    assert INSERT+ANCHOR in patched
    assert '        run: previous\n' in patched
    with pytest.raises(ValueError):transform(patched)


def test_v48_1_unavailable_phq_is_explicitly_excluded_from_both_cycles():
    # A strict nine-item score can become fully missing in one public data cycle.
    # This must not silently disappear inside SimpleImputer or feature rankings.
    from ml.public_mobility_v48 import feature_contract
    development,_=harmonize(fake_raw(220,seed=8),'2015-2016')
    heldout,_=harmonize(fake_raw(220,seed=12).assign(SEQN=lambda d:d.SEQN+2000000),'2017-2018')
    development['phq9_score']=np.nan
    selected,meta=feature_contract(development,heldout)
    assert 'phq9_score' not in selected
    assert any(x['feature']=='phq9_score' and x['observed_counts']['development']==0
               for x in meta['excluded_predictors'])
    result=train(development,heldout,fast=True)
    assert result['feature_availability_contract']['included_predictors']==selected
    assert 'phq9_score' not in [r['feature'] for r in result['validation_permutation_importance_delta_brier']]
    assert 'PREVIOUSLY_INSPECTED' in result['later_cycle_prior_exposure']


def test_v48_1_usable_phq_is_kept_without_leaking_an_outcome():
    from ml.public_mobility_v48 import feature_contract
    development,_=harmonize(fake_raw(220,seed=3),'2015-2016')
    heldout,_=harmonize(fake_raw(220,seed=7).assign(SEQN=lambda d:d.SEQN+2000000),'2017-2018')
    selected,meta=feature_contract(development,heldout)
    assert 'phq9_score' in selected
    assert 'target' not in selected and 'PFQ061B' not in selected
    assert meta['used_outcome_labels_for_availability_decision'] is False


def test_v48_1_fail_closed_if_minimum_age_or_sex_is_missing():
    from ml.public_mobility_v48 import feature_contract
    development,_=harmonize(fake_raw(220,seed=3),'2015-2016')
    heldout,_=harmonize(fake_raw(220,seed=7).assign(SEQN=lambda d:d.SEQN+2000000),'2017-2018')
    development['sex']=np.nan
    with pytest.raises(ContractError,match='source audit'):
        feature_contract(development,heldout)


def test_v48_1_public_aggregate_includes_real_feature_coverage_and_test_reuse_label(monkeypatch,tmp_path):
    from ml import public_mobility_v48 as module
    earlier=fake_raw(230,seed=3);later=fake_raw(180,seed=9).assign(SEQN=lambda d:d.SEQN+2000000)
    for key in module.TABLES['DPQ'][1:]:
        earlier[key]=np.nan
    monkeypatch.setattr(module,'read_cycle',lambda root,cycle: (earlier if cycle=='2015-2016' else later,
        {'FAKE_FIXTURE_ONLY.XPT':'generated'}))
    root=tmp_path/'new';(root/'results').mkdir(parents=True)
    report=module.run(root,fast=True)
    assert report['cohorts']['2015-2016']['phq9_valid_complete_n']==0
    assert 'phq9_score' in [x['feature'] for x in report['predictor_exclusions']]
    assert 'phq9_score' not in report['predictors_actually_used']
    assert 'PREVIOUSLY_INSPECTED' in report['experiment']['later_cycle_prior_exposure']
    assert 'already inspected' in (root/'results'/'mobility_report_v48.md').read_text()


def test_v48_1_coverage_audit_produces_aggregates_without_fitting(monkeypatch,tmp_path,capsys):
    from ml import public_mobility_v48 as module
    earlier=fake_raw(210,seed=7)
    later=fake_raw(180,seed=13).assign(SEQN=lambda d:d.SEQN+2000000)
    for key in module.TABLES['DPQ'][1:]:earlier[key]=np.nan
    monkeypatch.setattr(module,'read_cycle',lambda root,cycle:(
        earlier if cycle=='2015-2016' else later,{'fake': 'fixture'}))
    module.audit_feature_coverage(tmp_path)
    report=json.loads(capsys.readouterr().out)
    assert report['audit_only'] is True
    assert report['phq_complete_n_by_cycle']['2015-2016']==0
    assert report['individual_rows_exported'] is False
    assert not list(tmp_path.iterdir())


def test_v48_2_sas_ibm_zero_artifact_is_exact_and_normalized():
    # This checks the decoder using only eight invented zero bytes, no people.
    from pandas.io.sas.sas_xport import _parse_float_vec
    from ml.public_mobility_v48 import (SAS_XPORT_ZERO_ARTIFACT, normalize_xport_zeros)
    decoded = float(_parse_float_vec(np.frombuffer(bytes(8),dtype='S8'))[0])
    assert decoded == SAS_XPORT_ZERO_ARTIFACT
    frame = pd.DataFrame({'DPQ090':[decoded,0.0,1.0,2.0,3.0,7.0,9.0,np.nan],
                          'test_measure':[decoded,0.0,1e-8,4.0,7.0,np.nan,80.0,2.0],
                          'category':['a']*8})
    cleaned = normalize_xport_zeros(frame)
    assert cleaned.loc[0,'DPQ090'] == 0.0
    assert cleaned.loc[0,'test_measure'] == 0.0
    assert cleaned.loc[2,'test_measure'] == 1e-8  # NOT round tiny real values
    assert cleaned.loc[5,'DPQ090'] == 7.0
    assert cleaned.loc[6,'DPQ090'] == 9.0
    assert pd.isna(cleaned.loc[7,'DPQ090'])
    assert cleaned.category.equals(frame.category)
    assert frame.loc[0,'DPQ090'] == decoded  # original source not mutated


def test_v48_2_sas_zero_in_every_phq_item_restores_valid_zero_score():
    from ml.public_mobility_v48 import SAS_XPORT_ZERO_ARTIFACT, normalize_xport_zeros
    raw=fake_raw(180,seed=7)
    # Invented older participant, valid mobility answer and zero on all nine items.
    raw.loc[25,'RIDAGEYR']=75
    raw.loc[25,'PFQ054']=2
    raw.loc[25,'PFQ061B']=1
    for key in TABLES['DPQ'][1:]:
        raw[key]=raw[key].astype(float)
        raw.loc[25,key]=SAS_XPORT_ZERO_ARTIFACT
    false_out,_=harmonize(raw,'2015-2016')
    assert pd.isna(false_out.loc[false_out['id']==1000025,'phq9_score']).all()
    out,coverage=harmonize(normalize_xport_zeros(raw),'2015-2016')
    assert out.loc[out['id']==1000025,'phq9_score'].iloc[0]==0
    assert coverage['dpq_item_valid_observed_n']['DPQ090'] >= 1


def test_v48_2_source_reader_normalizes_decoded_zeros(monkeypatch,tmp_path):
    from ml import public_mobility_v48 as module
    frame=fake_raw(100,seed=11)
    frame['DPQ090']=frame['DPQ090'].astype(float)
    frame.loc[25,'DPQ090']=module.SAS_XPORT_ZERO_ARTIFACT
    # Only invented XPORT content: monkeypatch pandas before any actual read.
    monkeypatch.setattr(module.pd,'read_sas',lambda path,format:frame.copy())
    from pandas import DataFrame
    monkeypatch.setattr(module.Path,'read_bytes',lambda self:b'HEADER RECORD'+b'0'*2000)
    root=tmp_path/'isolated';(root/'raw').mkdir(parents=True)
    for table in module.TABLES:(root/'raw'/f'{table}_I.XPT').write_bytes(b'x')
    merged,_=module.read_cycle(root,'2015-2016')
    assert merged.loc[merged.SEQN==1000025,'DPQ090'].iloc[0]==0.0


def test_v48_2_published_docs_disclose_reader_correction_and_preinspected_wave():
    src = (ROOT/'ml/public_mobility_v48.py').read_text()
    doc = (ROOT/'research/PHASE2_PUBLIC_MOBILITY_V48.md').read_text()
    assert 'normalize_xport_zeros(df)' in src
    assert 'SAS_XPORT_ZERO_ARTIFACT' in src
    assert 'NOT a fresh' in doc or 'not a fresh' in doc.lower()
    assert '5.397605346934028e-79' in doc
    assert 'historical' in doc.lower() or 'mortality' in doc.lower()

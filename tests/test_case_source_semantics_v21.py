"""Only synthetic data and pure contract tests: NO model fitting or real research rows."""
from __future__ import annotations

import copy
import csv
import json

import pandas as pd
import pytest

from ml.case_source_semantics_v21 import (
    SCHEMA, REPORT_SCHEMA, POLICIES, canonical_sha, code_category,
    source_encode, predictor_spec, paired_summary, validate_design,
    validate_report, _read_development_only, make_pipeline,
)


def source_fixture():
    dev=pd.DataFrame({
        'SEQN':[101,102,103,104,105],
        'walking_difficulty':[None,1,None,3,None],
        'stairs_difficulty':[None,2,4,None,1],
        'stooping_difficulty':[3,2,None,4,1],
        'age':[69,71,80,65,74], 'sex':['F','M','F','M','F']})
    raw=pd.DataFrame({'SEQN':[101,102,103,104,105,106],
        'PFQ054':[1,2,2,2,2,1],
        'PFQ061B':[None,1,5,3,5,None],
        'PFQ061C':[None,2,4,5,1,None],
        'PFQ061D':[3,2,5,4,1,3]})
    return dev,raw


def synthetic_contract():
    manifest={'case_id':'test_case','task':'classification','target':'outcome',
              'id_column':'SEQN','features':{'numeric':[
                  'age','walking_difficulty','stairs_difficulty','stooping_difficulty'],
                  'categorical':['sex']}}
    v16={'case_id':'test_case','metric':'brier'}
    selected={'dataset_sha256':'a'*64,'v16_protocol_sha256':canonical_sha(v16),
              'selected_model':'random_forest','selected_preprocessing':'missingness_indicators',
              'final_development_selection':{'selection':{
                  'pair':'random_forest__missingness_indicators'}},
              'selected_parameters':{'n_estimators':80,'max_depth':12,'min_samples_leaf':6},
              'holdout_scored':False}
    cfg={'schema':SCHEMA,'case_id':'test_case','processed_sha256':'a'*64,
         'v16_protocol_sha256':canonical_sha(v16),'v20_audit_relative':'artifacts/x.json',
         'raw_pfq_sha256':'b'*64,'raw_file':'AUTO_PFQ_G',
         'frozen_pair':'random_forest__missingness_indicators',
         'methods':list(POLICIES),'primary_metric':'brier',
         'holdout_policy':'development_only_no_evaluation',
         'post_hoc_development_reuse':True,'seeds':[7319,7320],
         'folds':3,'expected_development_n':100}
    return cfg,manifest,v16,selected


def test_all_documented_codes():
    for i in (1,2,3,4):
        assert code_category(i,'PFQ061B',2)==f'DIFFICULTY_{i}'
    assert code_category(None,'PFQ061B',1)=='SKIP_PFQ054'
    assert code_category(None,'PFQ061C',1)=='SKIP_PFQ054'
    assert code_category(5,'PFQ061D',1)=='DO_NOT_DO_ACTIVITY'
    assert code_category(5,'PFQ061B',2)=='DO_NOT_DO_ACTIVITY'


@pytest.mark.parametrize('value,source,routing',[
    (None,'PFQ061D',1),(None,'PFQ061B',2),(7,'PFQ061B',2),
    (9,'PFQ061C',2),(6,'PFQ061D',2),(5,'PFQ061C',1),
    (2,'PFQ061B',1),(1.5,'PFQ061D',2)])
def test_unreviewed_responses_block(value,source,routing):
    with pytest.raises(ValueError):code_category(value,source,routing)


def test_source_encoder_preserves_valid_and_distinct_reasons():
    dev,raw=source_fixture()
    encoded,summary=source_encode(dev,raw)
    assert len(encoded)==5
    assert encoded.loc[0,'walking_difficulty_pfq_category']=='SKIP_PFQ054'
    assert encoded.loc[2,'walking_difficulty_pfq_category']=='DO_NOT_DO_ACTIVITY'
    assert encoded.loc[2,'stairs_difficulty_pfq_category']=='DIFFICULTY_4'
    assert encoded.loc[2,'stooping_difficulty_pfq_category']=='DO_NOT_DO_ACTIVITY'
    assert summary['walking_difficulty']['SKIP_PFQ054']==1
    assert summary['walking_difficulty']['DO_NOT_DO_ACTIVITY']==2
    assert summary['stooping_difficulty']['SKIP_PFQ054']==0
    assert 'PFQ054' not in encoded
    assert 'PFQ061B' not in encoded


@pytest.mark.parametrize('edit',[lambda d,r:r.__setitem__('PFQ061B',[None,1,9,3,5,None]),
        lambda d,r:r.__setitem__('PFQ054',[1,1,2,2,2,1]),
        lambda d,r:d.__setitem__('walking_difficulty',[None,4,None,3,None]),
        lambda d,r:r.__setitem__('SEQN',[101,101,103,104,105,106]),
        lambda d,r:r.__setitem__('SEQN',[100,102,103,104,105,106])])
def test_source_fail_closed(edit):
    d,r=source_fixture();edit(d,r)
    with pytest.raises(ValueError):source_encode(d,r)


def test_model_policy_feature_lists_and_no_unfitted_model_export():
    _,manifest,_,selected=synthetic_contract()
    num,cat=predictor_spec(manifest,'legacy_missing_indicators')
    assert len(num)==4 and cat==['sex']
    num,cat=predictor_spec(manifest,'source_status_augmented')
    assert len(num)==4 and 'walking_difficulty_pfq_status' in cat
    num,cat=predictor_spec(manifest,'source_categories')
    assert num==['age'] and 'stairs_difficulty_pfq_category' in cat
    model=make_pipeline(manifest,'source_categories',selected['selected_parameters'])
    assert 'features' in model.named_steps and 'model' in model.named_steps
    assert not hasattr(model.named_steps['model'],'estimators_')


def test_paired_metrics_math():
    rows=[dict(zip(POLICIES,(.14,.13,.132))),dict(zip(POLICIES,(.15,.145,.146)))]
    summary=paired_summary(rows)
    assert summary['repeated_cv_mean_brier']['legacy_missing_indicators']==.145
    assert summary['brier_gain_vs_legacy']['source_status_augmented']==.0075
    assert summary['repeats']==2
    rows[0]['source_categories']=float('nan')
    with pytest.raises(ValueError):paired_summary(rows)


def test_design_valid_and_invalid_variants():
    c,m,v,s=synthetic_contract()
    assert validate_design(c,m,v,s) is c
    for tamper in [lambda x:x.update(post_hoc_development_reuse=False),
                   lambda x:x.update(holdout_policy='evaluate'),
                   lambda x:x.update(v16_protocol_sha256='0'*64),
                   lambda x:x.update(frozen_pair='logistic__reference'),
                   lambda x:x.update(seeds=[3,3]),
                   lambda x:x.update(methods=list(reversed(x['methods']))),
                   lambda x:x.update(raw_pfq_sha256=''),
                   lambda x:x.update(folds=7)]:
        cc=copy.deepcopy(c);tamper(cc)
        with pytest.raises(ValueError):validate_design(cc,m,v,s)


def test_development_only_csv_never_reads_invalid_holdout_outcomes(tmp_path):
    path=tmp_path/'case.csv'
    with path.open('w',newline='') as fd:
        writer=csv.DictWriter(fd,fieldnames=['SEQN','cycle','outcome','age','sex',
         'walking_difficulty','stairs_difficulty','stooping_difficulty'])
        writer.writeheader()
        for n,cycle,target in [(1,'dev',0),(2,'dev',1),(3,'holdout','MUST_NOT_PARSE'),
                               (4,'holdout','MUST_NOT_PARSE')]:
            writer.writerow({'SEQN':n,'cycle':cycle,'outcome':target,'age':70,
            'sex':'F','walking_difficulty':1,'stairs_difficulty':2,
            'stooping_difficulty':3})
    _,m,_,_=synthetic_contract()
    m['split']={'strategy':'cohort','column':'cycle','development':'dev','evaluation':'holdout'}
    frame,not_scored=_read_development_only(path,m)
    assert len(frame)==2 and not_scored==2
    assert frame['outcome'].tolist()==[0,1]


def test_report_gate():
    c,*_=synthetic_contract()
    report={'schema':REPORT_SCHEMA,'report_type':'LOCAL_DEVELOPMENT_PFQ_ENCODING_DIAGNOSTIC',
            'case_id':c['case_id'],'config_sha256':canonical_sha(c),
            'holdout_outcomes_accessed':False,'model_overwritten':False,
            'model_binary_exported':False,'public_export':False,
            'new_threshold_selected':False,'n_development':100,
            'repeated_development_metrics':[{},{}]}
    assert validate_report(c,report)['holdout_scored'] is False
    for name,wrong in [('public_export',True),('model_overwritten',True),
                       ('holdout_outcomes_accessed',True),('n_development',7)]:
        changed=dict(report);changed[name]=wrong
        with pytest.raises(ValueError):validate_report(c,changed)


def test_import_does_not_fit():
    import ml.case_source_semantics_v21 as mod
    assert callable(mod.run) and callable(mod.main)
    assert not hasattr(mod,'fitted_model')

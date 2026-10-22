"""Synthetic-only tests. Never load real research tables or fit models."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.case_harmonization_v24 import (
    SCHEMA, REPORT_SCHEMA, canonical_code, digest, validate_protocol,
    harmonize_fixture, make_plan, local_file,
)

EVIDENCE='research/HARMONIZATION_CONTRACT_V24.md'


def feature(source,kind='ordinal'):
    return {'source_column':source,'kind':kind,'source_unit':'raw coded value',
        'canonical_unit':'canonical coded value',
        'value_codes':{'1':1,'2':2,'3':3,'4':4} if kind=='ordinal' else {'1':0,'2':1},
        'missing_codes':{'5':'does_not_do_activity','7':'refused','9':'unknown'},
        'blank_status':'structural_skip',
        'skip_if':{'column':'ROUTER','equals':'1'},
        'mapping_evidence':EVIDENCE}


def fixture():
    mapping=feature('ITEM_A')
    dic={'case_id':'synthetic','holdout_history':'locked_new',
         'prior_exploration':False,
         'prediction_index':{'definition_status':'provisional'},
         'predictors':{'walking':{'source_variables':['ITEM_A']},
                       'smoking':{'source_variables':['ITEM_B']}}}
    cfg={'schema':SCHEMA,'case_id':'synthetic',
         'related_v23_protocol':'research/cases/synthetic.json',
         'related_private_v23_ledger':'artifacts/cases/synthetic/report.json',
         'holdout_history':'locked_new','prior_exploration':False,
         'prediction_index_status':'provisional', 'scope':'partial_blueprint',
         'real_data_execution_permitted':False,'model_fitting_permitted':False,
         'holdout_scoring_permitted':False,'public_export_permitted':False,
         'waves':{'wave_A':{'source_verified':True,'features':{'walking':mapping}}},
         'unmapped_predictors':['smoking']}
    frame=pd.DataFrame({'ITEM_A':[None,1,2,5,7,9,4],
                        'ROUTER':[1,2,2,2,2,2,2]})
    return cfg,dic,frame


def test_source_harmonization_mapping():
    cfg,dic,df=fixture()
    assert validate_protocol(cfg,dic) is cfg
    out,counts=harmonize_fixture(df,cfg['waves']['wave_A'],synthetic_fixture=True)
    assert pd.isna(out['walking'].iloc[0])
    assert out['walking'].iloc[1:3].tolist()==[1,2]
    assert out['walking__status'].tolist()==[
        'structural_skip','observed','observed','does_not_do_activity',
        'refused','unknown','observed']
    assert counts['walking']['observed']==3
    assert list(out)==['walking','walking__status']
    assert out.index.equals(df.index)


@pytest.mark.parametrize('bad', [6,8,0,'surprise',-1,1.000001,float('inf')])
def test_unreviewed_codes_fail(bad):
    cfg,dic,frame=fixture()
    frame['ITEM_A']=frame['ITEM_A'].astype(object)
    frame.loc[1,'ITEM_A']=bad
    with pytest.raises(ValueError):
        harmonize_fixture(frame,cfg['waves']['wave_A'],synthetic_fixture=True)


@pytest.mark.parametrize('bad',[None,5,2,'foo'])
def test_documented_skip_must_have_blank(bad):
    cfg,dic,frame=fixture();frame['ITEM_A']=frame['ITEM_A'].astype(object);frame.loc[0,'ITEM_A']=bad
    if bad is None: return
    with pytest.raises(ValueError):
        harmonize_fixture(frame,cfg['waves']['wave_A'],synthetic_fixture=True)


def test_blank_without_skip_fails_closed():
    cfg,dic,frame=fixture();frame.loc[1,'ITEM_A']=None
    with pytest.raises(ValueError):
        harmonize_fixture(frame,cfg['waves']['wave_A'],synthetic_fixture=True)


def test_explicit_nonstructural_missing_allowed():
    cfg,dic,frame=fixture();spec=cfg['waves']['wave_A']['features']['walking']
    spec.pop('skip_if');spec['blank_status']='not_recorded'
    out,counts=harmonize_fixture(frame.iloc[[1,2,3]].assign(ITEM_A=[1,None,7]),
                                 cfg['waves']['wave_A'],synthetic_fixture=True)
    assert counts['walking']=={'not_recorded':1,'observed':1,'refused':1}
    assert out['walking__status'].tolist()==['observed','not_recorded','refused']


def test_unit_conversion_on_synthetic_data():
    cfg,dic,frame=fixture()
    value={'source_column':'ITEM_A','kind':'numeric',
           'source_unit':'cm','canonical_unit':'m','numeric_scale':.01,
           'numeric_offset':0,'unit_conversion_verified':True,
           'valid_range':[0.5,2.5], 'value_codes':{},
           'missing_codes':{'9999':'not_measured'},
           'blank_status':'not_recorded','mapping_evidence':EVIDENCE}
    cfg['waves']['wave_A']['features']['walking']=value
    validate_protocol(cfg,dic)
    out,counts=harmonize_fixture(pd.DataFrame({'ITEM_A':[150,200,9999,None]}),
                                 cfg['waves']['wave_A'],synthetic_fixture=True)
    assert out.walking.iloc[:2].tolist()==[1.5,2.]
    assert out['walking__status'].tolist()==['observed','observed','not_measured','not_recorded']
    for bad in [350,-20,0,float('inf'),'junk']:
        with pytest.raises(ValueError):
            harmonize_fixture(pd.DataFrame({'ITEM_A':[bad]}),cfg['waves']['wave_A'],
                              synthetic_fixture=True)


def test_conversion_requires_verification():
    cfg,dic,_=fixture()
    value={'source_column':'ITEM_A','kind':'numeric','source_unit':'cm',
           'canonical_unit':'m','numeric_scale':.01,'numeric_offset':0,
           'valid_range':[0.5,2.5],'value_codes':{},'missing_codes':{},
           'blank_status':'not_recorded','mapping_evidence':EVIDENCE}
    cfg['waves']['wave_A']['features']['walking']=value
    with pytest.raises(ValueError,match='conversion'):
        validate_protocol(cfg,dic)


@pytest.mark.parametrize('tamper',[
    lambda c:c.update(holdout_history='previously_inspected'),
    lambda c:c.update(prior_exploration=True),
    lambda c:c.update(real_data_execution_permitted=True),
    lambda c:c.update(model_fitting_permitted=True),
    lambda c:c.update(holdout_scoring_permitted=True),
    lambda c:c.update(public_export_permitted=True),
    lambda c:c.update(scope='complete'),
    lambda c:c.update(prediction_index_status='operationally_verified'),
    lambda c:c.update(unmapped_predictors=[]),
    lambda c:c.update(unmapped_predictors=['walking','smoking']),
    lambda c:c['waves']['wave_A'].update(source_verified=False),
    lambda c:c['waves']['wave_A']['features']['walking'].update(source_column='outcome_5yr'),
    lambda c:c['waves']['wave_A']['features']['walking'].update(source_column='SEQN'),
    lambda c:c['waves']['wave_A']['features']['walking'].update(value_codes={'1':1,'5':5}),
    lambda c:c['waves']['wave_A']['features']['walking'].update(blank_status='structural_skip',skip_if=None),
    lambda c:c['waves']['wave_A']['features']['walking'].update(blank_status='unexplained'),
    lambda c:c['waves']['wave_A']['features']['walking'].update(kind='time_to_event'),
    lambda c:c['waves']['wave_A']['features']['walking'].update(mapping_evidence='data/private.csv'),
])
def test_bad_protocols_fail_closed(tamper):
    cfg,dic,_=fixture();tamper(cfg)
    with pytest.raises(ValueError):validate_protocol(cfg,dic)


def test_two_wave_same_output_and_different_codes():
    cfg,dic,_=fixture()
    b=copy.deepcopy(cfg['waves']['wave_A'])
    b['features']['walking']['value_codes']={'A':1,'B':2,'C':3,'D':4}
    cfg['waves']['wave_B']=b
    assert validate_protocol(cfg,dic) is cfg
    b['features']['walking']['value_codes']['D']=8
    with pytest.raises(ValueError,match='categories'):
        validate_protocol(cfg,dic)


def test_no_modeling_and_no_report_export():
    cfg,dic,df=fixture()
    plan=make_plan(cfg)
    assert plan['schema']==REPORT_SCHEMA
    assert plan['route']=='BLOCKED_FOR_NEW_ANALYSIS'
    assert plan['holdout_history']=='locked_new'
    assert plan['unmapped_predictors']==['smoking']
    assert plan['no_models_fitted'] is True
    assert plan['no_predictions_generated'] is True
    assert plan['no_holdout_targets_accessed'] is True
    assert plan['public_export'] is False
    with pytest.raises(ValueError,match='real-data'):
        harmonize_fixture(df,cfg['waves']['wave_A'])


def test_duplicate_columns_rejected():
    cfg,dic,df=fixture()
    df=pd.concat([df,df[['ITEM_A']]],axis=1)
    with pytest.raises(ValueError):
        harmonize_fixture(df,cfg['waves']['wave_A'],synthetic_fixture=True)


def test_bad_source_ref_is_rejected(tmp_path):
    (tmp_path/'research').mkdir()
    (tmp_path/'research'/'one.json').write_text('{}')
    assert local_file(tmp_path,'research/one.json','research').is_file()
    for unsafe in ['../bad.json','/tmp/secret.json','data/private.csv','research/../data/x']:
        with pytest.raises(ValueError): local_file(tmp_path,unsafe,'research')


def test_numeric_and_float_code_are_equivalent():
    assert canonical_code(1)==canonical_code(1.0)=='1'
    assert canonical_code('1')=='1'
    assert canonical_code(' 1 ')=='1'
    assert canonical_code('001')=='001'  # zero-padded categories are not silently collapsed
    assert len(digest({'a':1}))==64


def test_no_target_or_private_data_touch_from_import():
    import ml.case_harmonization_v24 as m
    assert callable(m.main)
    assert not hasattr(m,'fitted_model')
    assert not hasattr(m,'participant_data')

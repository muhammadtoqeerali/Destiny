"""Fictional unit-test wave tables, not real NHATS observations."""
import copy
import json
import pandas as pd
import pytest
from ml.nhats_longitudinal_v09 import audit_rounds,check_spec,safe_path,normalized_status


def sample():
    def wave(round_no,year):
        return {'round':round_no,'year':year,'file':f'data/nhats/r{round_no}.csv',
                'id_column':'private_key','measures':{
                  'mobility':{'column':'mob','positive_codes':[1], 'negative_codes':[2], 'missing_codes':[-9]},
                  'cognition':{'disabled':True},'daily_function':{'disabled':True}}}
    spec={'verified_against_nhats_codebooks':True,'domains':['mobility','cognition','daily_function'],
          'waves':[wave(1,2011),wave(2,2012)]}
    left=pd.DataFrame({'private_key':['alpha','beta','gamma','delta'], 'mob':[2.,1.,-9.,2.]})
    right=pd.DataFrame({'private_key':['alpha','beta','gamma','omega'], 'mob':[1.,2.,1.,2.]})
    return spec,[left,right]


def test_detects_real_transitions_but_never_returns_ids():
    spec,rounds=sample()
    out=audit_rounds(rounds,spec)
    x=out['transitions'][0]
    assert x['matched_respondents']==3 and x['paired_observed_n']==2
    assert x['incident_difficulty_n']==1 and x['recovery_n']==1
    assert 'alpha' not in json.dumps(out)
    assert 'beta' not in json.dumps(out)
    assert 'NO_PREDICTION' in out['status']


def test_unverified_template_fails():
    spec,frames=sample();spec['verified_against_nhats_codebooks']=False
    with pytest.raises(ValueError):audit_rounds(frames,spec)


def test_codebook_unknown_and_duplicates_fail():
    spec,frames=sample()
    frames[0].loc[0,'mob']=77.
    with pytest.raises(ValueError,match='Unexpected code'):audit_rounds(frames,spec)
    spec,frames=sample()
    frames[0].loc[0,'private_key']='beta'
    with pytest.raises(ValueError,match='duplicated'):audit_rounds(frames,spec)
    spec,frames=sample();spec['waves'][0]['measures']['mobility']['missing_codes']=[2]
    with pytest.raises(ValueError,match='Overlapping'):check_spec(spec)


def test_numeric_code_normalization():
    meta={'column':'x','positive_codes':[1],'negative_codes':[2],'missing_codes':[-9]}
    assert normalized_status(1.,meta)==1
    assert normalized_status(2.,meta)==0
    assert normalized_status(-9.,meta) is None


def test_safe_path_rejects_outside_or_symlink(tmp_path):
    root=tmp_path/'project';(root/'data'/'nhats').mkdir(parents=True)
    (root/'data'/'nhats'/'round.csv').write_text('x\n1\n')
    assert safe_path(root,'data/nhats/round.csv').is_file()
    with pytest.raises(ValueError):safe_path(root,'data/../../other.csv')
    (root/'data'/'nhats'/'escape.csv').symlink_to(tmp_path/'elsewhere.csv')
    with pytest.raises(ValueError):safe_path(root,'data/nhats/escape.csv')

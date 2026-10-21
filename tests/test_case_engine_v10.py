"""Small artificial fixtures are unit tests only; no published research data."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from ml.case_engine_v10 import (validate_manifest,safe_local_input,load_data,
    split_data,run_case,render_markdown,calculate_metrics)


def cohort_case(tmp_path:Path,task='classification'):
    (tmp_path/'data').mkdir(exist_ok=True)
    rng=np.random.default_rng(731)
    n=210
    cycle=np.array(['2011-2012']*150+['2013-2014']*60)
    age=rng.integers(65,90,n)
    bmi=rng.normal(29,3,n)
    sex=rng.choice(['Male','Female'],n)
    score=(age-74)*0.04+(bmi-28)*.12+(sex=='Male')*.15+rng.normal(0,.9,n)
    y=(score>np.quantile(score,0.62)).astype(int) if task=='classification' else np.maximum(0,score*3+8)
    frame=pd.DataFrame({'SEQN':range(500000,500000+n),'cycle':cycle,'age':age,
             'bmi':bmi,'sex':sex,'outcome_5yr':y,'data_origin':['NHANES_PUBLIC_2019_LMF']*n})
    frame.loc[[1,16,38],'bmi']=np.nan
    frame.to_csv(tmp_path/'data'/'test.csv',index=False)
    spec={'case_id':'test_reference_case','display_name':'Test Reference',
         'source':{'path':'data/test.csv','provenance':{'column':'data_origin','value':'NHANES_PUBLIC_2019_LMF'}},
         'id_column':'SEQN','task':task,'target':'outcome_5yr',
         'features':{'numeric':['age','bmi'],'categorical':['sex']},
         'split':{'strategy':'cohort','column':'cycle','development':'2011-2012','evaluation':'2013-2014',
             'validation_fraction':0.25},'models':['dummy','logistic' if task=='classification' else 'ridge'],
         'selection_metric':'brier' if task=='classification' else 'rmse',
         'cv_folds':3,'trials_per_model':1}
    return spec


def test_real_reference_manifest_is_complete():
    spec=json.loads(Path('research/cases/nhanes_mortality_v10.json').read_text())
    assert validate_manifest(spec) is spec
    assert spec['split']['strategy']=='cohort'
    assert 'phq9_score' in spec['features']['numeric']
    assert spec['source']['path'].startswith('data/')


def test_contract_and_cohort_split(tmp_path):
    spec=cohort_case(tmp_path)
    frame,y,_=load_data(tmp_path,spec)
    tr,va,te=split_data(frame,y,spec)
    assert len(tr)+len(va)==150 and len(te)==60
    assert set(tr).isdisjoint(te) and set(va).isdisjoint(te)
    assert len(set(frame.iloc[te].cycle))==1


def test_blocks_leakage(tmp_path):
    s=cohort_case(tmp_path);s['features']['numeric'].append('SEQN')
    with pytest.raises(ValueError,match='leakage'):validate_manifest(s)
    s=cohort_case(tmp_path);s['features']['numeric'].append('mortstat')
    with pytest.raises(ValueError,match='leakage'):validate_manifest(s)
    s=cohort_case(tmp_path);s['features']['numeric'].append('death_date')
    with pytest.raises(ValueError,match='leakage'):validate_manifest(s)


def test_blocks_target_leakage(tmp_path):
    s=cohort_case(tmp_path);s['features']['numeric'].append('outcome_5yr')
    with pytest.raises(ValueError):validate_manifest(s)


def test_requires_baseline(tmp_path):
    s=cohort_case(tmp_path);s['models']=['logistic']
    with pytest.raises(ValueError,match='Dummy baseline'):validate_manifest(s)


def test_blocks_unsafe_path_and_symlink(tmp_path):
    s=cohort_case(tmp_path)
    assert safe_local_input(tmp_path,s['source']['path']).is_file()
    with pytest.raises(ValueError):safe_local_input(tmp_path,'../secret.csv')
    (tmp_path/'data'/'escape.csv').symlink_to('/etc/hosts')
    with pytest.raises(ValueError):safe_local_input(tmp_path,'data/escape.csv')


def test_requires_stable_provenance(tmp_path):
    s=cohort_case(tmp_path)
    s['source']['provenance']['value']='OTHER'
    with pytest.raises(ValueError,match='origin'):load_data(tmp_path,s)


def test_rejects_duplicate_ids(tmp_path):
    s=cohort_case(tmp_path)
    p=tmp_path/'data'/'test.csv';df=pd.read_csv(p)
    df.loc[2,'SEQN']=df.loc[1,'SEQN'];df.to_csv(p,index=False)
    with pytest.raises(ValueError,match='IDs'):load_data(tmp_path,s)


def test_works_on_classification_fixture(tmp_path):
    s=cohort_case(tmp_path)
    r=run_case(tmp_path,s)
    assert r['selected_model']=='logistic'
    assert r['split']['counts']['evaluation']==60
    assert r['evaluation']['roc_auc']>0.6
    assert len(r['permutation_importance_validation'])==3
    assert 'SEQN' not in json.dumps(r)
    assert 'experiment results' in render_markdown(r).lower()


def test_works_on_regression_fixture(tmp_path):
    s=cohort_case(tmp_path,'regression')
    r=run_case(tmp_path,s)
    assert r['selected_model']=='ridge'
    assert r['evaluation']['rmse']>=0
    assert 'roc_auc' not in r['evaluation']


def test_rejects_extra_cohorts(tmp_path):
    s=cohort_case(tmp_path);p=tmp_path/'data'/'test.csv'
    df=pd.read_csv(p);df.loc[0,'cycle']='2017-2018';df.to_csv(p,index=False)
    frame,y,_=load_data(tmp_path,s)
    with pytest.raises(ValueError,match='Other cohort'):split_data(frame,y,s)


def test_metric_confusion_is_consistent():
    y=np.array([0,0,1,1]);proba=np.array([0.1,.9,.2,.9])
    m=calculate_metrics('classification',y,proba,proba,.5)
    assert m['confusion']=={'tn':1,'fp':1,'fn':1,'tp':1}


def test_catboost_classifier_adapter_with_modern_sklearn():
    pytest.importorskip('catboost')
    from ml.case_engine_v10 import CatBoostClassifierAdapter
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    rng=np.random.default_rng(3)
    X=rng.normal(size=(40,3))
    y=(X[:,0]>0).astype(int)
    model=Pipeline([('scale',StandardScaler()),('cat',CatBoostClassifierAdapter(iterations=25))]).fit(X,y)
    assert model.predict_proba(X[:5]).shape==(5,2)
    assert model.predict(X[:5]).shape==(5,)


def test_catboost_regressor_adapter_with_modern_sklearn():
    pytest.importorskip('catboost')
    from ml.case_engine_v10 import CatBoostRegressorAdapter
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    rng=np.random.default_rng(3)
    X=rng.normal(size=(40,3))
    y=2*X[:,0]-X[:,1]
    model=Pipeline([('scale',StandardScaler()),('cat',CatBoostRegressorAdapter(iterations=25))]).fit(X,y)
    assert model.predict(X[:5]).shape==(5,)


def test_optional_excel_adapter_accepts_worksheet(tmp_path):
    pytest.importorskip('openpyxl')
    from ml.case_engine_v10 import read_local_table
    s=cohort_case(tmp_path)
    data=pd.read_csv(tmp_path/'data'/'test.csv')
    path=tmp_path/'data'/'case.xlsx'
    data.to_excel(path,index=False,sheet_name='Measures')
    s['source']['path']='data/case.xlsx';s['source']['sheet']='Measures'
    frame,y,hashval=load_data(tmp_path,s)
    assert len(frame)==210 and len(hashval)==64


def test_random_split_with_regression(tmp_path):
    s=cohort_case(tmp_path,'regression')
    s['split']={'strategy':'random','validation_fraction':0.25,'evaluation_fraction':0.25}
    frame,y,_=load_data(tmp_path,s)
    tr,va,te=split_data(frame,y,s)
    assert len(set(tr)&set(va))==0
    assert len(te)>=50


def test_cv_respects_configured_objective(tmp_path):
    from ml.case_engine_v10 import cv_score
    spec=cohort_case(tmp_path)
    frame,y,_=load_data(tmp_path,spec)
    x=frame[['age','bmi','sex']]
    b=cv_score(x,y,['age','bmi'],['sex'],'logistic','classification',{'C':1.0},3,'brier')
    rank_loss=cv_score(x,y,['age','bmi'],['sex'],'logistic','classification',{'C':1.0},3,'roc_auc')
    assert 0 <= b <= 1 and 0 <= rank_loss <= 1 and abs(b-rank_loss)>0.001
    reg=cohort_case(tmp_path,'regression')
    f,yt,_=load_data(tmp_path,reg)
    rmse=cv_score(f[['age','bmi','sex']],yt,['age','bmi'],['sex'],'ridge','regression',{'alpha':1},3,'rmse')
    mae=cv_score(f[['age','bmi','sex']],yt,['age','bmi'],['sex'],'ridge','regression',{'alpha':1},3,'mae')
    assert 0 < mae <= rmse

def test_cli_writes_fitted_model_locally(tmp_path,monkeypatch):
    import sys, joblib
    from ml.case_engine_v10 import main
    spec=cohort_case(tmp_path)
    (tmp_path/'research').mkdir()
    (tmp_path/'research'/'case.json').write_text(json.dumps(spec))
    monkeypatch.setattr(sys,'argv',['run','--project',str(tmp_path),'--config','research/case.json'])
    main()
    location=tmp_path/'artifacts/cases'/spec['case_id']
    model=joblib.load(location/'best_model.joblib') # trusted artifact created by this test
    assert hasattr(model,'predict_proba')
    assert json.loads((location/'metrics.json').read_text())['selected_model']=='logistic'

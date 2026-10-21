"""Only synthetic unit-test fixtures; no synthetic dataset used for research."""
import copy
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import brier_score_loss
from ml.case_forensics_v11 import feature_profile,preprocessing_audit,calibration,performance_groups,cross_cycle_shift,raw_local_preview,correlations
from ml.case_enhancement_v11 import crossfit_calibration,choose_calibration,logit
from ml.case_engine_v10 import fit_pipeline
from scripts.export_case_audit_v11 import clean

def fixture(n=420):
    rng=np.random.default_rng(44)
    age=rng.integers(65,88,n);bmi=np.round(rng.normal(27,4,n),1)
    bmi[:14]=np.nan
    sex=np.array(['Female','Male'])[rng.integers(0,2,n)].astype(object)
    sex[1]=None
    p=1/(1+np.exp(-(-3+.055*(age-65)+.035*(np.nan_to_num(bmi,nan=27)-27))))
    y=rng.binomial(1,p)
    return pd.DataFrame({'age':age,'bmi':bmi,'sex':sex}),pd.Series(y)

def test_profile_quantiles_and_suppression():
    frame,y=fixture();p=feature_profile(frame,'bmi','numeric')
    assert p['missing']==14 and p['observed']==406
    assert p['summary']['median']>20 and 'distribution' in p
    assert all(c['n']>=20 for c in p['distribution'])

def test_numeric_categorical_processing_genuine_fitted_stats():
    frame,y=fixture()
    model=fit_pipeline(['age','bmi'],['sex'],'logistic','classification',{'C':0.5},frame.iloc[:300],y.iloc[:300])
    d=preprocessing_audit(model,frame,np.arange(300),np.arange(300,420),['age','bmi'],['sex'])
    assert d['input_feature_count']==3 and d['output_feature_count']>=4
    bmi=next(x for x in d['methods'] if x['feature']=='bmi')
    assert bmi['training_missing']==14 and bmi['after_missing']==0
    assert abs(bmi['impute_value']-frame.iloc[:300].bmi.median())<1e-3
    preview=raw_local_preview(frame,np.arange(300),model,['age','bmi'],['sex'])
    assert len(preview)==5 and not {'id','SEQN'}.intersection(preview[0])

def test_correlations_and_shift():
    frame,y=fixture()
    correlations_out=correlations(frame,['age','bmi'])
    assert len(correlations_out)==1
    assert -1<=correlations_out[0]['spearman_rho']<=1
    shifts=cross_cycle_shift(frame,np.arange(200),np.arange(200,420),['age','bmi'])
    assert len(shifts)==2 and shifts[0]['standardized_mean_difference']>=0

def test_reliability_bin_threshold():
    frame,y=fixture(630);p=np.linspace(.02,.70,630)
    out=calibration(y,p)
    assert len(out)>5 and all(x['n']>=50 for x in out)
    assert sum(x['n'] for x in out)==630

def test_subgroup_minimum_cases():
    rng=np.random.default_rng(9);n=900
    frame=pd.DataFrame({'age':rng.choice([66,72,77,80],n),'sex':rng.choice(['Female','Male'],n)})
    y=rng.binomial(1,0.35,n);p=np.clip(rng.normal(.35,.13,n),0,1)
    groups=performance_groups(frame,y,p,.4,np.arange(n))
    assert groups and all(x['n']>=100 and x['events']>=20 and x['n']-x['events']>=20 for x in groups)

def test_crossfit_platt_does_not_consume_evaluation():
    rng=np.random.default_rng(17);n=330;y=rng.binomial(1,.35,n)
    raw=np.clip(.1+.3*y+rng.normal(0,.18,n),.01,.99)
    oof=crossfit_calibration(y,raw)
    result=choose_calibration(y,raw,oof)
    assert np.isfinite(oof).all() and len(oof)==n
    assert result['accepted'] in (True,False)
    assert result['raw_validation_brier']==round(brier_score_loss(y,raw),6)
    assert logit(raw).shape==(n,1)

def test_enhancement_acceptance_gate_can_reject():
    rng=np.random.default_rng(22);n=320;y=rng.binomial(1,.3,n)
    raw=np.clip(.18+.6*y+rng.normal(0,.03,n),.0001,.999)
    result=choose_calibration(y,raw,raw)
    assert not result['accepted']

def audit_stub():
    return {'schema':'FRAILTYSCOPE_CASE_AUDIT_V11','case_id':'nhanes_mortality_v10',
      'source_sha256':'abc','counts':{'all':2422,'train':873,'validation':292,'evaluation':1257},
      'feature_profiles':[{'feature':'age','label':'Age','description':'Years', 'type':'numeric',
        'observed':2422,'missing':0,'missing_pct':0,'unique':16,
        'summary':{'median':72},'distribution':[{'bin':'65–69','n':743}]}],
      'cohort_shift':[],'correlations':[],
      'preprocessing':{'input_feature_count':1,'output_feature_count':1,
         'methods':[{'feature':'age','label':'Age','method':'median + scale','fit_partition':'Training only',
           'training_missing':0,'validation_missing':0,'after_missing':0,'impute_value':72}],
         'quantile_examples':[]},
      'selection':{'metric':'brier','model':'logistic','candidates':[{'name':'logistic','cv_score':.16,
           'validation':{'brier':.15},'parameters':{},'fit_search_seconds':2.3}],
         'permutation_importance_validation':[]},
      'evaluation':{'metrics':{'roc_auc':.8},'baseline':{'roc_auc':.5},
         'calibration':[{'bin':1,'n':120,'predicted':.3,'observed':.35}],
         'subgroups':[{'group':'Female','n':200,'events':55,'event_rate':.275,
           'roc_auc':.79,'recall':.8,'false_positive_rate':.32,'brier':.14}]},
      'local_examples':[{'record':'Local row 1','raw':{'age':'75'},'transformed_vector':[.12]}],
      'methodology':{'selection':'Brier','data_split':'separate','is_external_validation':False,
           'preprocessing':'training','limitations':['Research']}}

def enhancement_stub():
    return {'schema':'FRAILTYSCOPE_ENHANCEMENT_V11','case_id':'nhanes_mortality_v10',
      'dataset_sha256':'abc','method':'Platt','model':'logistic',
      'rule':{'accepted':False,'oof_brier_gain':-.02},'thresholds':{'original':.3,'selected':.3},
      'later_cycle':{'original':{'roc_auc':.8},'selected':{'roc_auc':.8}}}

def test_public_export_drops_actual_rows_and_sha():
    out=clean(audit_stub(),enhancement_stub(),{'counts':{'total':2422},'provenance':'REAL_NHANES_AGGREGATE_ONLY'},
              {'dataset_sha256':'abc'})
    text=str(out)
    assert 'Local row 1' not in text and 'transformed_vector' not in text and 'source_sha256' not in text
    assert len(out['features'])==1 and out['evaluation']['subgroups'][0]['n']==200

def test_public_export_rejects_small_bins():
    a=audit_stub();a['feature_profiles'][0]['distribution'][0]['n']=2
    with pytest.raises(ValueError,match='Small distribution'):clean(a,enhancement_stub(),{'counts':{'total':2422},'provenance':'REAL_NHANES_AGGREGATE_ONLY'}, {'dataset_sha256':'abc'})

def test_public_export_rejects_wrong_fingerprint():
    e=enhancement_stub();e['dataset_sha256']='different'
    with pytest.raises(ValueError,match='Fingerprint'):clean(audit_stub(),e,{'counts':{'total':2422},'provenance':'REAL_NHANES_AGGREGATE_ONLY'},{'dataset_sha256':'abc'})

def test_public_export_rejects_small_subgroup():
    a=audit_stub();a['evaluation']['subgroups'][0]['events']=1
    with pytest.raises(ValueError,match='Unsafe subgroup'):clean(a,enhancement_stub(),{'counts':{'total':2422},'provenance':'REAL_NHANES_AGGREGATE_ONLY'}, {'dataset_sha256':'abc'})

def test_end_to_end_actual_local_model_contract(tmp_path):
    import json,joblib
    from pathlib import Path
    from ml.case_engine_v10 import load_data,split_data,digest,calculate_metrics
    from ml.case_forensics_v11 import generate as forensic_generate
    from ml.case_enhancement_v11 import generate as enhance_generate
    x,y=fixture(520)
    # Artificial test fixtures only; never used as research data or published.
    path=tmp_path/'data'/'unit.csv';path.parent.mkdir(parents=True)
    df=x.copy();df['local_id']=np.arange(len(df));df['outcome']=y
    df['wave']=['earlier']*330+['later']*190
    df.to_csv(path,index=False)
    spec={'case_id':'unit_case_v11','source':{'path':'data/unit.csv'},'id_column':'local_id',
       'target':'outcome','task':'classification',
       'features':{'numeric':['age','bmi'],'categorical':['sex']},
       'split':{'strategy':'cohort','column':'wave','development':'earlier','evaluation':'later','validation_fraction':.25},
       'models':['dummy','logistic'],'selection_metric':'brier','cv_folds':3,'trials_per_model':2}
    df2,y2,sha=load_data(tmp_path,spec);tr,va,te=split_data(df2,y2,spec)
    model=fit_pipeline(['age','bmi'],['sex'],'logistic','classification',{'C':1.},df2.iloc[tr][['age','bmi','sex']],y2.iloc[tr])
    val=model.predict_proba(df2.iloc[va][['age','bmi','sex']])[:,1]
    test=model.predict_proba(df2.iloc[te][['age','bmi','sex']])[:,1]
    m={'schema':'FRAILTYSCOPE_CASE_V10','case_id':'unit_case_v11','dataset_sha256':sha,
      'task':'classification','selection_metric':'brier','selected_model':'logistic','selected_threshold':0.3,
      'candidate_models':[{'model':'logistic','parameters':{'C':1.},'cv_score':.15,
                          'validation':calculate_metrics('classification',y2.iloc[va],val,val),
                          'fit_search_seconds':1.5}],
      'permutation_importance_validation':[{'feature':'age','mean_metric_drop':.03}],
      'evaluation':calculate_metrics('classification',y2.iloc[te],test,test,0.3),
      'dummy_baseline_evaluation':calculate_metrics('classification',y2.iloc[te],np.full(len(te),float(y2.iloc[tr].mean())),np.full(len(te),float(y2.iloc[tr].mean())))}
    out=tmp_path/'artifacts'/'cases'/'unit_case_v11';out.mkdir(parents=True)
    (out/'metrics.json').write_text(json.dumps(m));joblib.dump(model,out/'best_model.joblib')
    audit=forensic_generate(tmp_path,spec)
    enh=enhance_generate(tmp_path,spec)
    assert audit['source_sha256']==sha
    assert len(audit['feature_profiles'])==3
    assert len(audit['local_examples'])==5
    assert len(audit['evaluation']['calibration'])==0  # 190 observations < privacy threshold
    assert enh['later_cycle']['selected']['n']==190
    assert enh['rule']['accepted'] in (True,False)

def test_local_inspector_only_deidentified_examples():
    from scripts.local_transformation_inspector_v11 import page
    a=audit_stub();a['local_examples'][0]['raw']['age']='<b>75</b>'
    markup=page({'schema':'FRAILTYSCOPE_CASE_AUDIT_V11','report_type':'LOCAL_DEIDENTIFIED_AUDIT',
       'preprocessing':a['preprocessing'],'local_examples':a['local_examples']})
    assert '&lt;b&gt;75&lt;/b&gt;' in markup and '<b>75</b>' not in markup
    assert 'LOCAL RESEARCH WORKSPACE' in markup

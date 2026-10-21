from pathlib import Path
import numpy as np
import pandas as pd
from ml.realdata_nhanes import read_mortality, construct_five_year_label,as_features,recode_yes_no,recode_function
from ml.longitudinal_contract import check_panel,label_at_horizon,OutcomeSpec
from ml.realdata_train import scores,tune_threshold,pipeline
from sklearn.linear_model import LogisticRegression


def test_cdc_mortality_fwf_parser(tmp_path:Path):
    # Synthetic FIXTURE ONLY for testing exact CDC fixed-width layout.
    rows=[]
    for i in range(15):
        s=f'{70000+i:6d}'+' '*8+'1'+ ('1' if i%2 else '0') + ' '*29 + f'{10+i*7:3d}'+' '*8
        assert s[14]=='1' and s[15] in '01'
        rows.append(s)
    path=tmp_path/'fixture.dat'
    path.write_text('\n'.join(rows)+'\n')
    df=read_mortality(path)
    assert len(df)==15
    assert df.iloc[0].SEQN==70000
    assert df.iloc[3].PERMTH_EXM==31


def test_mortality_five_year_classification_and_censoring():
    m=pd.DataFrame({'ELIGSTAT':[1,1,1,1,1,3,1],
                    'MORTSTAT':[1,1,0,0,1,1,0],
                    'PERMTH_EXM':[20,70,80,22,60,10,np.nan]})
    x=construct_five_year_label(m).outcome_5yr
    assert x.iloc[0]==1
    assert x.iloc[1]==0
    assert x.iloc[2]==0
    assert np.isnan(x.iloc[3])
    assert x.iloc[4]==1
    assert np.isnan(x.iloc[5])
    assert np.isnan(x.iloc[6])


def test_nhanes_recoding_and_questionnaire_skip():
    yes=pd.Series([1,2,7,9,np.nan])
    assert recode_yes_no(yes).iloc[:2].tolist()==[1,0]
    assert recode_yes_no(yes).iloc[2:].isna().all()
    fn=recode_function(pd.Series([1,2,3,4,5,7,9]))
    assert fn.iloc[:4].tolist()==[1,2,3,4]
    assert fn.iloc[4:].isna().all()
    row=pd.DataFrame({'RIDAGEYR':[85],'RIAGENDR':[2],'DPQ010':[1]})
    f=as_features(row)
    assert f.iloc[0]['age']==85 and f.iloc[0]['sex']=='Female'
    assert pd.isna(f.iloc[0]['phq9_score'])


def test_longitudinal_unequal_followup():
    d=pd.DataFrame({'id':[1,2,3,4],'baseline':['2020-01-01']*4,
      'event':['2020-06-01','2022-01-01',None,None],
      'end':['2021-03-01','2021-03-01','2020-08-01','2022-01-01']})
    spec=OutcomeSpec('event','baseline','event','end')
    y=label_at_horizon(d,spec,365)
    assert y.iloc[0]==1 and y.iloc[1]==0 and pd.isna(y.iloc[2]) and y.iloc[3]==0
    waves=pd.DataFrame({'person_id':[1,1,2], 'assessment_date':['2020-01-01','2021-01-01','2020-01-01'],'data_origin':['APPROVED']*3})
    assert check_panel(waves)['n_people']==2


def test_metric_baseline_and_threshold_are_separate():
    y=np.array([0,0,1,1,0,1,0,1])
    p=np.array([.1,.2,.6,.7,.3,.4,.15,.65])
    s=scores(y,p,.5)
    assert s['confusion']['tp']==3
    assert 0 < tune_threshold(y,p) < 1


def test_pipeline_fit_and_predict():
    rng=np.random.default_rng(4)
    rows=60
    from ml.realdata_nhanes import BASE_FEATURES
    d=pd.DataFrame({k:rng.normal(size=rows) for k in BASE_FEATURES if k!='sex'})
    d['sex']=rng.choice(['Female','Male'],size=rows)
    d.iloc[0,0]=np.nan
    y=np.array([0,1]*30)
    p=pipeline(LogisticRegression(max_iter=200))
    p.fit(d,y)
    assert p.predict_proba(d.iloc[:2]).shape==(2,2)

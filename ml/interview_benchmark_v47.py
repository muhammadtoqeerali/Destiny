"""NTNU interview-ready, GENERATED-only tabular cohort benchmark.

Synthetic toy outcomes model software behavior; never an estimate of HUNT or real frailty.
Only evaluation summaries and eight explicitly fictional profiles may be exported.
No files from data/, artifacts/, research-private paths, or participant-level inputs read.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 472026
OUTPUT='web/app/data/interview-benchmark-v47.json'
NAMES=['Dummy prior','Logistic regression','Random forest','Histogram boosting']
NUMERIC=['age','bmi','grip_strength_kg','gait_speed_mps','chronic_conditions','adl_limitations','falls_last_year','low_mood_score']
CATEGORICAL=['sex','activity_level']
FEATURES=NUMERIC+CATEGORICAL


def generated(n:int=1800,seed:int=SEED)->pd.DataFrame:
    if not 600<=n<=3000:raise ValueError('Generated fixture size outside controlled demo')
    rng=np.random.default_rng(seed)
    age=rng.integers(70,96,n)
    sex=rng.choice(['Female','Male'],size=n,p=[.55,.45])
    conditions={
      'Hypertension':rng.binomial(1,np.clip(.38+.012*(age-70),0,.82),n),
      'Diabetes':rng.binomial(1,np.clip(.16+.004*(age-70),0,.42),n),
      'Heart disease':rng.binomial(1,np.clip(.10+.009*(age-70),0,.46),n),
      'Lung disease':rng.binomial(1,.13,n),
      'Arthritis':rng.binomial(1,np.clip(.35+.006*(age-70),0,.69),n),
    }
    chronic=sum(conditions.values())
    mobility_signal=.045*(age-70)+.42*chronic+rng.normal(0,1,n)
    gait=np.clip(1.32-.12*mobility_signal+rng.normal(0,.14,n),.15,1.8)
    grip=np.clip(np.where(sex=='Male',31,20)-.28*(age-70)-2*chronic+rng.normal(0,5,n),4,60)
    bmi=np.clip(rng.normal(26.8,4.5,n)+.14*chronic,16,44)
    activity=rng.choice(['Low','Moderate','High'],n,p=[.38,.44,.18])
    mood=np.clip(rng.poisson(3.6+.5*chronic,n),0,27)
    adl=np.clip(rng.poisson(.3+.32*(mobility_signal>1.2),n),0,5)
    falls=rng.binomial(2,np.clip(.10+.11*(gait<.8)+.008*(age-70),0,.65))
    # Future outcome is an invented process, not a HUNT or NHATS observation.
    logit=(-3.35+.050*(age-70)+.48*adl+.32*chronic+.38*falls+
           .13*mood/3+.95*(gait<.72)-.034*(grip-16)+.36*(activity=='Low'))
    prob=1/(1+np.exp(-np.clip(logit,-20,20)))
    future=rng.binomial(1,prob)
    df=pd.DataFrame({'fictional_id':[f'FICTIONAL-{i:05d}' for i in range(n)],
        'age':age,'sex':sex,'bmi':np.round(bmi,1),'grip_strength_kg':np.round(grip,1),
        'gait_speed_mps':np.round(gait,2),'chronic_conditions':chronic,
        'adl_limitations':adl,'falls_last_year':falls,'low_mood_score':mood,
        'activity_level':activity,'future_adl_decline_demo':future})
    for condition,flags in conditions.items():df['has_'+condition.lower().replace(' ','_')]=flags
    # Missing-not-at-random-ish toy patterns; never fill from a test fold.
    for key,p in [('bmi',.065),('grip_strength_kg',.11),('gait_speed_mps',.07),('low_mood_score',.09)]:
        missing=rng.random(n)<p + .07*(age>88)
        df.loc[missing,key]=np.nan
    df.loc[rng.random(n)<.035,'activity_level']=None
    return df


def split(df):
    groups=df['fictional_id'].to_numpy()
    y=df['future_adl_decline_demo'].to_numpy()
    outer=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=SEED)
    tv,te=next(outer.split(df,y,groups))
    inner=GroupShuffleSplit(n_splits=1,test_size=.25,random_state=SEED+1)
    tr0,va0=next(inner.split(df.iloc[tv],y[tv],groups[tv]))
    tr,va=tv[tr0],tv[va0]
    ids=[set(groups[i]) for i in (tr,va,te)]
    assert not (ids[0]&ids[1] or ids[0]&ids[2] or ids[1]&ids[2])
    for idx in (tr,va,te):
        if len(np.unique(y[idx]))<2:raise ValueError('Insufficient class diversity for split')
    return tr,va,te


def pipeline(estimator):
    pre=ColumnTransformer([
        ('numeric',Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True)),
                             ('scale',StandardScaler())]),NUMERIC),
        ('categorical',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),
                  ('onehot',OneHotEncoder(handle_unknown='ignore'))]),CATEGORICAL),
    ])
    return Pipeline([('transform',pre),('model',estimator)])


def models():
    return [
      DummyClassifier(strategy='prior'),
      LogisticRegression(max_iter=1200,C=.7,random_state=SEED),
      RandomForestClassifier(n_estimators=140,max_depth=7,min_samples_leaf=8,
                             random_state=SEED,n_jobs=1),
      HistGradientBoostingClassifier(max_iter=110,max_leaf_nodes=13,
                             learning_rate=.055,l2_regularization=1,random_state=SEED),
    ]


def metrics(y,p):
    if not np.all(np.isfinite(p)) or np.any((p<0)|(p>1)):
        raise ValueError('Invalid probability output')
    return {'roc_auc':round(float(roc_auc_score(y,p)),4),
            'average_precision':round(float(average_precision_score(y,p)),4),
            'brier':round(float(brier_score_loss(y,p)),4)}


def bins(y,p):
    cuts=np.linspace(0,1,6)
    result=[]
    for i in range(5):
        mask=(p>=cuts[i]) & (p<(cuts[i+1]) if i<4 else p<=cuts[i+1])
        if mask.any():result.append({'band':f'{int(100*cuts[i])}–{int(100*cuts[i+1])}%',
            'count':int(mask.sum()),'mean_probability':round(float(p[mask].mean()),4),
            'observed_fraction':round(float(y[mask].mean()),4)})
    return result


def report():
    df=generated();tr,va,te=split(df)
    X=df[FEATURES];y=df['future_adl_decline_demo'].to_numpy()
    rows=[];fitted={}
    for name,estimator in zip(NAMES,models()):
        learner=pipeline(estimator)
        learner.fit(X.iloc[tr],y[tr])
        vp=learner.predict_proba(X.iloc[va])[:,1]
        rows.append({'name':name,'validation':metrics(y[va],vp)})
        fitted[name]=learner
    # Select using VALIDATION only. The untouched synthetic test is measured once.
    best=min(rows,key=lambda x:(x['validation']['brier'],NAMES.index(x['name'])))['name']
    best_fit=fitted[best]
    p=best_fit.predict_proba(X.iloc[te])[:,1]
    test=metrics(y[te],p)
    # Show only generated, invented example rows: no real participant information.
    indices=te[:8];examples=[]
    conditions_for_export=['Hypertension','Diabetes','Heart disease','Lung disease','Arthritis']
    demo_p=best_fit.predict_proba(X.iloc[indices])[:,1]
    explainer=None
    if best=='Logistic regression':
        processor=best_fit.named_steps['transform']
        model=best_fit.named_steps['model']
        values=processor.transform(X.iloc[indices])
        terms=values*model.coef_[0]
        names=processor.get_feature_names_out()
        explainer=(model,terms,names)
    for pos,(idx,pred) in enumerate(zip(indices,demo_p)):
        rec=df.iloc[int(idx)]
        contributions=[]
        if explainer is not None:
            model,terms,names=explainer
            reconstructed=float(model.intercept_[0]+terms[pos].sum())
            if abs(reconstructed-np.log(float(pred)/(1-float(pred))))>1e-8:
                raise ValueError('Fictional model contributions do not reconstruct prediction')
            order=np.argsort(-np.abs(terms[pos]))[:4]
            contributions=[{'feature':str(names[j]).replace('numeric__','').replace('categorical__','').replace('missingindicator_','missing: '),
                             'log_odds_contribution':round(float(terms[pos,j]),4)} for j in order]
        examples.append({'id':str(rec['fictional_id']), 'age':int(rec['age']),
           'illustrative_factors':contributions,
          'sex':str(rec['sex']),'chronic_conditions':int(rec['chronic_conditions']),
          'adl_limitations':int(rec['adl_limitations']),
          'current_conditions':[c for c in conditions_for_export if rec['has_'+c.lower().replace(' ','_')]==1],
          'gait_speed_mps':None if pd.isna(rec['gait_speed_mps']) else float(rec['gait_speed_mps']),
          'grip_strength_kg':None if pd.isna(rec['grip_strength_kg']) else float(rec['grip_strength_kg']),
          'observed_demo_outcome':int(rec['future_adl_decline_demo']),
          'fictional_model_probability':round(float(pred),4)})
    val_best=next(r['validation'] for r in rows if r['name']==best)
    return {'schema':'FRAILTYSCOPE_INTERVIEW_BENCHMARK_V47',
      'source':'GENERATED_FICTIONAL_AGEING_COHORT_NOT_HUNT_NHATS_OR_NHANES',
      'target':'Artificial next-period activities-of-daily-living decline label',
      'time_horizon':'Invented two-year follow-up, not observed',
      'training_claim':'Demonstrates machine-learning software only; no real-data generalization',
      'person_level_real_data_used':False,'clinical_prediction':False,
      'generated_with':{'scikit_learn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__},
      'configuration':{'seed':SEED,'generation_n':len(df),'features':FEATURES,
           'train_n':len(tr),'validation_n':len(va),'test_n':len(te),
           'split':'fictional_id-disjoint 60/20/20; validation model selection; synthetic test once',
           'missingness':'training-only median/mode imputation with numeric missing indicators',
           'selection':'minimum validation Brier, deterministic listed-order tiebreak'},
      'models':rows,'selected_model':best,'selected_validation':val_best,
      'synthetic_test':test,'calibration':bins(y[te],p),'fictional_examples':examples,
      'interpretability':'If selected model is logistic, exact transformed-feature log-odds terms describe the fictional model prediction; not SHAP, causality, or medical guidance',
      'limits':['Invented labels and measurements; metrics are not HUNT results',
        'No cross-dataset ranking because tasks/endpoints differ',
        'No new NHANES real-data analysis or clinical inference',
        'No individual real records exported to web hosting']}


def serialized():return json.dumps(report(),ensure_ascii=False,indent=2)+'\n'

def check_fixture(stored:dict, current:dict)->None:
    """Strict same-toolchain replay; safe bounded drift check across supported ML runtimes."""
    required=('schema','source','target','clinical_prediction','person_level_real_data_used',
              'configuration','selected_model')
    for key in required:
        if stored.get(key)!=current.get(key):
            raise ValueError('Unexpected synthetic provenance, split or selected model: '+key)
    if len(stored.get('models',[]))!=len(current['models']) or \
        [m.get('name') for m in stored['models']]!=NAMES:
        raise ValueError('Synthetic model portfolio changed')
    if stored.get('generated_with')==current['generated_with']:
        if stored!=current:raise ValueError('Same-toolchain synthetic benchmark does not exactly replay')
        return
    # sklearn/numpy revisions can change low-order tree/solver results. Never
    # confuse that with scientific transportability. Keep outcome provenance,
    # model identity, scores and public artificial-example boundaries fixed.
    for a,b in zip(stored['models'],current['models']):
        for metric in ('roc_auc','average_precision','brier'):
            if abs(a['validation'][metric]-b['validation'][metric])>.03:
                raise ValueError('Synthetic model metric drift too large')
    for metric in ('roc_auc','average_precision','brier'):
        if abs(stored['synthetic_test'][metric]-current['synthetic_test'][metric])>.03:
            raise ValueError('Synthetic heldout metric drift too large')
    if [x['id'] for x in stored.get('fictional_examples',[])]!=[x['id'] for x in current['fictional_examples']]:
        raise ValueError('Invented profile lineage changed')
    for a,b in zip(stored['fictional_examples'],current['fictional_examples']):
        if abs(a['fictional_model_probability']-b['fictional_model_probability'])>.03:
            raise ValueError('Fictional example prediction drift too large')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    opts=parser.add_mutually_exclusive_group(required=True)
    opts.add_argument('--check',action='store_true')
    opts.add_argument('--write-fixture',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    output=root/OUTPUT;current=report();s=json.dumps(current,ensure_ascii=False,indent=2)+'\n'
    if args.check:
        if not output.is_file():raise SystemExit('ERROR: fictional benchmark missing')
        try:
            stored=json.loads(output.read_text(encoding='utf8'))
            check_fixture(stored,current)
        except (ValueError,KeyError,TypeError) as exc:
            raise SystemExit('ERROR: fictional benchmark not reproducible/safe: '+str(exc)) from None
        print('PASS: Interview synthetic model comparison verified; local toolchain:',current['generated_with'])
    else:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(s,encoding='utf8')
        print('WROTE generated-only interview fixture:',output)

if __name__=='__main__':main()

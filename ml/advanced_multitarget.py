"""Reproducible MULTI-OUTCOME model benchmark, synthetic demo or restricted local run.

IMPORTANT: synthetic performance is NOT evidence about real HUNT participants.
No patient-level authorized data are ever written to web/public or committed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score,average_precision_score,brier_score_loss,
                             confusion_matrix,f1_score,precision_score,recall_score,roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.base import BaseEstimator, ClassifierMixin

from ml.schema import FEATURES
from ml.multioutcome import OUTCOMES,DESCRIPTIONS,make_synthetic_cohort,simulated_history
from ml.train import make_pipeline,verify_synthetic
from ml.approved_hunt_adapter import make_labels


class CatBoostSklearnAdapter(ClassifierMixin, BaseEstimator):
    """CatBoost wrapper with sklearn >=1.6 estimator tags and fitted state."""
    def __init__(self, iterations=130, depth=4, learning_rate=.05, l2_leaf_reg=5, random_seed=42, thread_count=4):
        self.iterations=iterations; self.depth=depth; self.learning_rate=learning_rate
        self.l2_leaf_reg=l2_leaf_reg; self.random_seed=random_seed; self.thread_count=thread_count

    def fit(self, X, y):
        from catboost import CatBoostClassifier
        self.model_=CatBoostClassifier(iterations=self.iterations,depth=self.depth,
            learning_rate=self.learning_rate,l2_leaf_reg=self.l2_leaf_reg,
            random_seed=self.random_seed,thread_count=self.thread_count,allow_writing_files=False,
            verbose=False,loss_function='Logloss')
        self.model_.fit(X,y)
        self.classes_=np.asarray(self.model_.classes_)
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(X)

    def predict(self, X):
        return self.model_.predict(X)


def model_candidates(include_advanced:bool=True)->dict[str,Any]:
    models={
        'Regularized logistic regression': lambda: LogisticRegression(C=.3,max_iter=1200),
        'Histogram gradient boosting': lambda: HistGradientBoostingClassifier(max_iter=90,max_leaf_nodes=15,learning_rate=.065,l2_regularization=3,random_state=42),
    }
    if include_advanced:
        try:
            from xgboost import XGBClassifier
            models['XGBoost'] = lambda: XGBClassifier(n_estimators=105,max_depth=3,learning_rate=.05,
                subsample=.85,colsample_bytree=.85,reg_lambda=5,eval_metric='logloss',
                tree_method='hist',random_state=42,n_jobs=4)
        except ImportError:
            print('Optional dependency xgboost unavailable; install requirements-advanced.txt')
        try:
            from catboost import CatBoostClassifier
            models['CatBoost'] = lambda: CatBoostSklearnAdapter()
        except ImportError:
            print('Optional dependency catboost unavailable; install requirements-advanced.txt')
    return models


def score(y:pd.Series,p:np.ndarray)->dict:
    y=np.asarray(y).astype(int);p=np.asarray(p,dtype=float);classified=(p>=.5).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,classified,labels=[0,1]).ravel()
    return dict(roc_auc=round(float(roc_auc_score(y,p)),4),
       average_precision=round(float(average_precision_score(y,p)),4),
       brier=round(float(brier_score_loss(y,p)),4),
       accuracy=round(float(accuracy_score(y,classified)),4),
       precision=round(float(precision_score(y,classified,zero_division=0)),4),
       recall=round(float(recall_score(y,classified,zero_division=0)),4),
       specificity=round(float(tn/max(1,tn+fp)),4),
       f1=round(float(f1_score(y,classified,zero_division=0)),4),
       matrix={'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)})


def split_synthetic(df:pd.DataFrame,seed:int):
    indexes=np.arange(len(df))
    dev,test=train_test_split(indexes,test_size=.2,random_state=seed,stratify=df['fall_within_12m'])
    train,val=train_test_split(dev,test_size=.25,random_state=seed,stratify=df.iloc[dev]['fall_within_12m'])
    return train,val,test


def split_approved(df:pd.DataFrame):
    """Prefer temporal split; disallow an unsupported time claim with one baseline date."""
    times=pd.to_datetime(df['baseline_date'],errors='coerce')
    if times.isna().any() or times.nunique()<3:
        raise ValueError('Temporal split requires ≥3 distinct baseline dates. Define another approved validation design, never silently substitute random.')
    n=len(df)
    if n<200: raise ValueError('At least 200 eligible participants required for this prototype; check cohort design')
    unique=sorted(times.unique())
    split1=unique[int(len(unique)*.6)]
    split2=unique[int(len(unique)*.8)]
    train=np.flatnonzero(times < split1);validation=np.flatnonzero((times>=split1)&(times<split2));test=np.flatnonzero(times>=split2)
    if min(len(train),len(validation),len(test))<30:
        raise ValueError('Insufficient date-separated observations in at least one temporal partition')
    return train,validation,test


def bin_calibration(y:pd.Series,p:np.ndarray)->list[dict]:
    y=np.asarray(y)
    bins=np.linspace(0,1,7)
    return [{'expected':round(float(p[(p>=a)&(p<b if b<1 else p<=b)].mean()),3),
             'observed':round(float(y[(p>=a)&(p<b if b<1 else p<=b)].mean()),3),
             'n':int(((p>=a)&(p<b if b<1 else p<=b)).sum())}
            for a,b in zip(bins[:-1],bins[1:]) if ((p>=a)&(p<b if b<1 else p<=b)).sum()>0]


def run(df:pd.DataFrame,seed:int=42,advanced:bool=True,mode:str='synthetic',
        export:Path|None=None,artifacts:Path|None=None)->dict:
    if mode=='synthetic':
        verify_synthetic(df)
        train_ids,val_ids,test_ids=split_synthetic(df,seed)
    else:
        if export is not None:raise ValueError('SECURITY: approved-data mode may not export any public dashboard JSON')
        train_ids,val_ids,test_ids=split_approved(df)
    models=model_candidates(advanced)
    report={'mode':mode,'modeling':'five separate binary 12-month illustrative outcomes' if mode=='synthetic' else 'approved temporal prototype (not validated for clinical use)',
            'n':len(df),'algorithms':list(models),'split':{'train':len(train_ids),'validation':len(val_ids),'test':len(test_ids)},'outcomes':[]}
    prediction_map={}
    selected_models={}
    ref={key:(float(df.iloc[train_ids][key].median()) if key != 'sex' else str(df.iloc[train_ids][key].mode().iloc[0])) for key in FEATURES}
    test=df.iloc[test_ids]
    for target,label in OUTCOMES.items():
        valid=np.asarray(df[target].notna())
        ta=train_ids[valid[train_ids]]
        va=val_ids[valid[val_ids]]
        te=test_ids[valid[test_ids]]
        if min(len(ta),len(va),len(te))<30 or any(df.iloc[ix][target].nunique()!=2 for ix in (ta,va,te)):
            report['outcomes'].append({'id':target,'label':label,'status':'not_estimable','reason':'Too few eligible labels or one outcome class'});continue
        tr,vl,ts=(df.iloc[ix] for ix in (ta,va,te))
        candidates=[];fitted={}
        for name,make in models.items():
            pipe=make_pipeline(make(),FEATURES)
            pipe.fit(tr[FEATURES],tr[target].astype(int))
            val_prob=pipe.predict_proba(vl[FEATURES])[:,1]
            sc=score(vl[target],val_prob)
            candidates.append({'name':name,'validation':sc})
            fitted[name]=pipe
            print(f'{label:25s} | {name:32s} | val AUC={sc["roc_auc"]:.3f} Brier={sc["brier"]:.3f}',flush=True)
        selected=min(candidates,key=lambda c:(c['validation']['brier'],-c['validation']['roc_auc']))
        pipe=fitted[selected['name']]
        test_probs=pipe.predict_proba(ts[FEATURES])[:,1]
        ts_sc=score(ts[target],test_probs)
        benchmark={'id':target,'label':label,'status':'evaluated','nTrain':len(tr),'nValidation':len(vl),'nTest':len(ts),
                    'eventsTest':int(ts[target].sum()),'selectedModel':selected['name'],
                    'validationModels':candidates,'test':ts_sc,'calibration':bin_calibration(ts[target],test_probs)}
        report['outcomes'].append(benchmark)
        print(f'  Selected: {selected["name"]}. Held-out AUC={ts_sc["roc_auc"]:.3f}, Brier={ts_sc["brier"]:.3f}',flush=True)
        if mode=='synthetic':
            selected_models[target]=pipe
            prediction_map[target]=dict(zip(ts.patient_id,test_probs))
            if artifacts:
                artifacts.mkdir(parents=True,exist_ok=True)
                joblib.dump({'pipeline':pipe,'features':FEATURES,'synthetic_only':True,'target':target},artifacts/f'{target}.joblib')
        # no authorized HUNT exports, predictions, IDs, or model artifacts persisted.
    if export is not None:
        if mode!='synthetic':raise ValueError('Public export requires synthetic mode')
        records=[]
        # Match the 90 synthetic cases in the existing Doctor Portal.
        displayed_cases=test.sample(n=min(90,len(test)),random_state=seed)
        for _,row in displayed_cases.iterrows():
            pid=row.patient_id
            from ml.train import explain_example_with_columns
            forecasts=[{'id':key,'label':label,'score':round(float(prediction_map[key][pid])*100,1),
                'horizonMonths':12,'method':next(v['selectedModel'] for v in report['outcomes'] if v['id']==key),
                'responses':explain_example_with_columns(selected_models[key],row,ref,FEATURES)[:3]}
                for key,label in OUTCOMES.items() if key in prediction_map and pid in prediction_map[key]]
            records.append({'id':pid,'outcomes':forecasts,'priorVisits':simulated_history(row,seed=seed)})
        # JSON contains ONLY synthetic patient IDs and synthetic predictions.
        payload={'provenance':'SYNTHETIC_ONLY','publicData':False,'disclaimer':'All individual outcomes, scores and histories are invented. No HUNT participant data. Not clinical decision support.',
            'publishedHuntContext':{'originalAreaN':9956,'trondheimN':1743,'source':'https://academic.oup.com/ije/article/55/2/dyag011/8490101','type':'Published aggregate cohort description, NOT modeling data'},
            'summary':{'syntheticParticipants':len(df),'split':report['split'],'algorithms':list(models)},
            'outcomes':report['outcomes'],'cases':records}
        export.parent.mkdir(parents=True,exist_ok=True)
        export.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
        print('Synthetic-only web payload saved:',export)
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['synthetic','approved-local'],default='synthetic')
    p.add_argument('--n',type=int,default=6000)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--fast-models',action='store_true',help='Only logistic regression and histogram gradient boosting')
    p.add_argument('--baseline',help='Approved pseudonymized baseline CSV in secure enclave')
    p.add_argument('--followup',help='Approved follow-up CSV in secure enclave')
    p.add_argument('--acknowledge-approved-environment',action='store_true')
    p.add_argument('--output',default='web/public/data/multioutcome-demo.json')
    p.add_argument('--artifact-dir',default=None)
    a=p.parse_args()
    if a.mode=='approved-local':
        if not a.acknowledge_approved_environment or not a.baseline or not a.followup:
            p.error('Approved mode requires baseline/followup paths and explicit environment acknowledgement.')
        # We do NOT write a public result or save private model weights in this path.
        df=make_labels(pd.read_csv(a.baseline),pd.read_csv(a.followup))
        report=run(df,a.seed,not a.fast_models,mode='approved-local')
        print('LOCAL RESEARCH EXPERIMENT FINISHED. No data, predictions, model or report exported.')
    else:
        df=make_synthetic_cohort(n=a.n,seed=a.seed)
        output=Path(a.output)
        if 'web/public/data' not in output.as_posix():
            raise ValueError('Public synthetic output must be in web/public/data/')
        run(df,a.seed,not a.fast_models,mode='synthetic',export=output,
            artifacts=Path(a.artifact_dir) if a.artifact_dir else None)

if __name__=='__main__':
    # Serialize adapter classes using their stable importable module name.
    import importlib
    CatBoostSklearnAdapter = importlib.import_module('ml.advanced_multitarget').CatBoostSklearnAdapter
    main()

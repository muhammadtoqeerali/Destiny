"""Run independent, real-public-data NHANES mortality benchmark locally.

Training data and artifacts MUST remain off GitHub and Vercel. The report contains
aggregate statistics only. Classification is not a clinically deployable model.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, accuracy_score, precision_score, recall_score, f1_score, fbeta_score, confusion_matrix
from sklearn.model_selection import train_test_split
from ml.realdata_nhanes import BASE_FEATURES

TARGET='outcome_5yr'

def pipeline(estimator):
    numerics=[c for c in BASE_FEATURES if c!='sex']
    pre=ColumnTransformer([
      ('num',Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True)),('scale',StandardScaler())]),numerics),
      ('cat',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),['sex'])
    ],sparse_threshold=0)
    return Pipeline([('preprocess',pre),('model',estimator)])


class CatBoostAdapter(ClassifierMixin, BaseEstimator):
    """Compatible CatBoost wrapper for scikit-learn 1.8 pipeline fitted checks."""
    def __init__(self, seed:int=42):
        self.seed=seed

    def fit(self,X,y):
        from catboost import CatBoostClassifier
        self.estimator_=CatBoostClassifier(iterations=250,depth=4,learning_rate=.035,
            l2_leaf_reg=6,loss_function='Logloss',verbose=False,thread_count=4,
            random_seed=self.seed)
        self.estimator_.fit(X,y)
        self.classes_=self.estimator_.classes_
        return self

    def predict_proba(self,X):
        return self.estimator_.predict_proba(X)

    def predict(self,X):
        return self.estimator_.predict(X).reshape(-1)


def factories(seed):
    from xgboost import XGBClassifier
    return {
      'Regularized logistic regression':lambda:pipeline(LogisticRegression(max_iter=2500,C=0.5,class_weight=None,random_state=seed)),
      'Histogram gradient boosting':lambda:pipeline(HistGradientBoostingClassifier(max_iter=150,learning_rate=.045,max_leaf_nodes=12,l2_regularization=5,random_state=seed)),
      'XGBoost':lambda:pipeline(XGBClassifier(n_estimators=220,max_depth=3,learning_rate=.035,subsample=.9,colsample_bytree=.9,reg_lambda=8,tree_method='hist',n_jobs=4,random_state=seed,eval_metric='logloss')),
      'CatBoost':lambda:pipeline(CatBoostAdapter(seed=seed))
    }


def scores(y,p,cutoff=.5,weights=None):
    y=np.asarray(y,dtype=int)
    p=np.asarray(p,dtype=float)
    if len(np.unique(y))<2:raise ValueError('Both event classes must be present')
    yhat=(p>=cutoff).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,yhat,labels=[0,1]).ravel()
    return {
      'roc_auc':round(float(roc_auc_score(y,p,sample_weight=weights)),4),
      'average_precision':round(float(average_precision_score(y,p,sample_weight=weights)),4),
      'brier':round(float(brier_score_loss(y,p,sample_weight=weights)),4),
      'accuracy':round(float(accuracy_score(y,yhat,sample_weight=weights)),4),
      'precision':round(float(precision_score(y,yhat,zero_division=0,sample_weight=weights)),4),
      'recall':round(float(recall_score(y,yhat,zero_division=0,sample_weight=weights)),4),
      'f1':round(float(f1_score(y,yhat,zero_division=0,sample_weight=weights)),4),
      'confusion':{'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)},
    }


def tune_threshold(y,p):
    """Illustrative choice on validation ONLY; max F2 (recall-weighted)."""
    candidates=np.linspace(.02,.70,137)
    ys=np.asarray(y,dtype=int)
    best=min(candidates,key=lambda t:(-fbeta_score(ys,p>=t,beta=2,zero_division=0),abs(t-.5)))
    return round(float(best),4)


def boot_auc_interval(y,p,seed=42,n=200):
    rng=np.random.default_rng(seed); ys=np.asarray(y,dtype=int); ps=np.asarray(p,float)
    auc=[]
    for _ in range(n):
        idx=rng.integers(0,len(ys),len(ys))
        if np.unique(ys[idx]).size==2:auc.append(roc_auc_score(ys[idx],ps[idx]))
    return [round(float(np.quantile(auc,t)),4) for t in [.025,.975]] if len(auc)>10 else None


def run(input:Path,out:Path,seed:int=42):
    df=pd.read_csv(input)
    if not df.data_origin.eq('NHANES_PUBLIC_2019_LMF').all():
        raise ValueError('Expected NHANES real public-use provenance only')
    if not set(BASE_FEATURES+[TARGET,'cycle','SEQN','survey_weight']).issubset(df.columns):
        raise ValueError('Missing required features or outcome')
    if df.duplicated(['cycle','SEQN']).any():raise ValueError('Repeated participant-cycle key')
    trainval=df[df.cycle.eq('2011-2012')].copy()
    test=df[df.cycle.eq('2013-2014')].copy()
    if len(trainval)<150 or len(test)<150:raise ValueError('Not enough records for cycle-level evaluation')
    tr,va=train_test_split(trainval,test_size=.25,random_state=seed,stratify=trainval[TARGET])
    if set(tr.SEQN).intersection(set(va.SEQN)) or set(test.SEQN).intersection(set(trainval.SEQN)):
        raise ValueError('Leakage across splits')
    bench=[]; winners={}
    for name,factory in factories(seed).items():
        model=factory()
        model.fit(tr[BASE_FEATURES],tr[TARGET])
        p=model.predict_proba(va[BASE_FEATURES])[:,1]
        metric=scores(va[TARGET],p)
        bench.append({'model':name,'validation':metric})
        winners[name]=(model,p)
        print(f'{name:<33} | Validation ROC-AUC {metric["roc_auc"]:.3f} | AP {metric["average_precision"]:.3f} | Brier {metric["brier"]:.3f}',flush=True)
    best=min(bench,key=lambda z:(z['validation']['brier'],-z['validation']['roc_auc']))
    label=best['model']; model,va_scores=winners[label]
    # Selection and threshold based only on 2011-12 development data.
    cutoff=tune_threshold(va[TARGET],va_scores)
    p_test=model.predict_proba(test[BASE_FEATURES])[:,1]
    normal=scores(test[TARGET],p_test,cutoff=.5)
    tuned=scores(test[TARGET],p_test,cutoff=cutoff)
    weights=np.asarray(test.survey_weight,float)
    weights=np.where(np.isfinite(weights)&(weights>0),weights,0)
    weighted=scores(test[TARGET],p_test,cutoff=cutoff,weights=weights) if weights.sum()>0 else None
    report={
      'report_type':'AGGREGATE_RESEARCH_METRICS_ONLY','data_origin':'NHANES_PUBLIC_2019_LMF',
      'source':'CDC NHANES 2011–2014 + public-use linked 2019 mortality',
      'label':'Mortality at approximately 60 months following baseline MEC exam; public-use times may be perturbed',
      'training_cycle':'2011-2012','test_cycle':'2013-2014','split':'2011–12 75% training /25% validation; 2013–14 external-cycle test',
      'counts':{'train':len(tr),'validation':len(va),'test':len(test),'test_events':int(test[TARGET].sum())},
      'selected_model':label,'validation_comparisons':bench,
      'selection':'Minimum validation Brier, ROC-AUC tie breaker',
      'validation_selected_threshold_F2':cutoff,
      'test_unweighted_threshold_050':normal,
      'test_unweighted_validation_threshold':tuned,
      'test_weighted_validation_threshold':weighted,
      'test_auc_95ci_fixed_model_bootstrap':boot_auc_interval(test[TARGET],p_test,seed),
      'baseline_predict_none_accuracy':round(float(1-test[TARGET].mean()),4),
      'warnings':[
        'Real public-use US survey data; this is NOT HUNT or NHATS.',
        'Public linked mortality follow-up times are perturbed for selected respondents; five-year horizon is approximate.',
        'This classifier does not model censoring or competing events and is not a complete survival analysis.',
        'Random validation within earliest cycle; later-cycle test is a temporal cohort comparison, not an independent clinical-site validation.',
        'Public-use NHANES age is top-coded at 80 years; do not infer finer ages.',
        'Some PFQ variables are missing by questionnaire routing and eligibility.',
        'Weighted discrimination is exploratory; survey design-based confidence intervals and calibration remain necessary.',
        'No calibration refit; no Optuna optimization; no causal or clinical interpretation.',
        'Never place actual participant rows, model binaries or individual predictions on GitHub/Vercel.'
      ],
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('\n========== HELD-OUT REAL-DATA RESULTS (NOT HUNT) ==========',flush=True)
    print(json.dumps({k:report[k] for k in ['counts','selected_model','validation_selected_threshold_F2','test_unweighted_threshold_050','test_unweighted_validation_threshold','baseline_predict_none_accuracy','test_auc_95ci_fixed_model_bootstrap']},indent=2),flush=True)
    print('Aggregate-only report saved:',out,flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default='data/processed/nhanes_5yr_local.csv')
    p.add_argument('--report',default='artifacts/realdata_nhanes/report.json')
    p.add_argument('--seed',type=int,default=42)
    args=p.parse_args()
    run(Path(args.input),Path(args.report),args.seed)
if __name__=='__main__':main()
